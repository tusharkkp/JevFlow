import time
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional

from backend.app.schemas.request import GatewayRequest
from backend.app.schemas.response import GatewayResponse, TelemetryTrace, RouteType
from backend.app.decision.base import DecisionEngine
from backend.app.decision.jev_engine import TypeSafeJevEngine
from backend.app.policy.engine import PolicyEngine
from backend.app.policy.state import SystemState
from backend.app.providers.registry import ProviderRegistry


class GatewayService:
    """
    Central Orchestrator for JevFlow.
    
    Coordinates the adaptive pipeline:
    Client Request + Runtime State -> System One Decision -> Adaptive Policy -> Provider -> Telemetry
    """

    def __init__(
        self,
        decision_engine: Optional[DecisionEngine] = None,
        policy_engine: Optional[PolicyEngine] = None,
        provider_registry: Optional[ProviderRegistry] = None,
    ):
        self.decision_engine = decision_engine or TypeSafeJevEngine()
        self.policy_engine = policy_engine or PolicyEngine()
        self.registry = provider_registry or ProviderRegistry()
        self._active_requests: int = 0
        self._lock = asyncio.Lock()

    async def _capture_system_state(self) -> SystemState:
        """Snapshot current runtime concurrency, provider health, and latencies."""
        # Simple snapshot
        provider_health_map = {
            RouteType.DETERMINISTIC.value: "healthy",
            RouteType.SMALL_MODEL.value: "healthy",
            RouteType.FRONTIER_MODEL.value: "healthy",
            RouteType.HUMAN_REVIEW.value: "healthy",
        }
        return SystemState(
            active_requests=self._active_requests,
            provider_status=provider_health_map,
        )

    async def process_request(self, request: GatewayRequest) -> GatewayResponse:
        start_overall = time.perf_counter()
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc)
        estimated_input_tokens = max(1, len(request.prompt) // 4)

        async with self._lock:
            self._active_requests += 1

        try:
            # 1. System One Decision
            decision = await self.decision_engine.evaluate(request.prompt)

            # 2. Capture dynamic runtime conditions
            system_state = await self._capture_system_state()

            # 3. Adaptive Policy Evaluation
            plan = self.policy_engine.evaluate(
                decision=decision,
                latency_budget_ms=request.latency_budget_ms,
                cost_budget=request.cost_budget,
                estimated_input_tokens=estimated_input_tokens,
                system_state=system_state,
            )

            # 4. Model Provider Execution (with automatic failover)
            provider_resp, exec_fallback, exec_reason = await self.registry.execute_route(
                route=plan.selected_route,
                prompt=request.prompt,
            )

        finally:
            async with self._lock:
                self._active_requests = max(0, self._active_requests - 1)

        # 5. Latency & Cost Telemetry Accounting
        end_overall = time.perf_counter()
        total_latency_ms = (end_overall - start_overall) * 1000.0

        gateway_overhead_ms = max(
            0.1,
            total_latency_ms - decision.decision_latency_ms - provider_resp.latency_ms,
        )

        baseline_cost_usd = self.registry.frontier_model.estimate_cost(
            input_tokens=provider_resp.input_tokens,
            output_tokens=provider_resp.output_tokens,
        )
        cost_saved_usd = max(0.0, baseline_cost_usd - provider_resp.cost_usd)

        fallback_triggered = plan.fallback_triggered or exec_fallback
        fallback_reason = exec_reason or plan.fallback_reason

        telemetry = TelemetryTrace(
            request_id=request_id,
            timestamp=created_at,
            intent=decision.intent.value,
            complexity_score=decision.complexity_score,
            jev_confidence=decision.confidence,
            selected_route=plan.selected_route,
            policy_reason=plan.policy_reason,
            actual_model=provider_resp.model_name,
            cache_hit=False,
            fallback_triggered=fallback_triggered,
            fallback_reason=fallback_reason,
            jev_latency_ms=round(decision.decision_latency_ms, 2),
            model_latency_ms=round(provider_resp.latency_ms, 2),
            gateway_overhead_ms=round(gateway_overhead_ms, 2),
            total_latency_ms=round(total_latency_ms, 2),
            input_tokens=provider_resp.input_tokens,
            output_tokens=provider_resp.output_tokens,
            estimated_cost_usd=provider_resp.cost_usd,
            baseline_cost_usd=baseline_cost_usd,
            cost_saved_usd=round(cost_saved_usd, 7),
        )

        return GatewayResponse(
            request_id=request_id,
            content=provider_resp.content,
            route=plan.selected_route,
            model=provider_resp.model_name,
            telemetry=telemetry,
        )
