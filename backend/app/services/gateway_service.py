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
from backend.app.cache.base import BaseCache
from backend.app.cache.memory_cache import MemoryCache
from backend.app.cache.key_generator import generate_cache_key
from backend.app.telemetry.repository import TelemetryRepository


class GatewayService:
    """
    Central Orchestrator for JevFlow.
    
    Coordinates the pipeline:
    Client Request -> Cache Check -> System One Decision -> Adaptive Policy -> Provider -> Cache Store -> Telemetry Persistence
    """

    def __init__(
        self,
        decision_engine: Optional[DecisionEngine] = None,
        policy_engine: Optional[PolicyEngine] = None,
        provider_registry: Optional[ProviderRegistry] = None,
        cache: Optional[BaseCache] = None,
        telemetry_repo: Optional[TelemetryRepository] = None,
    ):
        self.decision_engine = decision_engine or TypeSafeJevEngine()
        self.policy_engine = policy_engine or PolicyEngine()
        self.registry = provider_registry or ProviderRegistry()
        self.cache = cache or MemoryCache()
        self.telemetry_repo = telemetry_repo or TelemetryRepository()
        self._active_requests: int = 0
        self._lock = asyncio.Lock()

    async def _capture_system_state(self) -> SystemState:
        """Snapshot current runtime concurrency, provider health, and latencies."""
        provider_health_map = {
            RouteType.DETERMINISTIC.value: "healthy",
            RouteType.SMALL_MODEL.value: "healthy",
            RouteType.FRONTIER_MODEL.value: "healthy",
            RouteType.HUMAN_REVIEW.value: "healthy",
        }
        for route, cb in self.registry.circuit_breakers.items():
            if cb.state.value == "open":
                provider_health_map[route.value] = "unavailable"

        return SystemState(
            active_requests=self._active_requests,
            provider_status=provider_health_map,
            cache_available=(self.cache is not None),
        )

    async def process_request(self, request: GatewayRequest) -> GatewayResponse:
        start_overall = time.perf_counter()
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc)
        estimated_input_tokens = max(1, len(request.prompt) // 4)

        # ----------------------------------------------------------------------
        # 1. Cache Layer Lookup (Prior to Jev Decision)
        # ----------------------------------------------------------------------
        cache_key = generate_cache_key(request.prompt)
        if self.cache:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                total_latency_ms = (time.perf_counter() - start_overall) * 1000.0
                baseline_cost = cached_data.get("baseline_cost_usd", 0.001)

                telemetry = TelemetryTrace(
                    request_id=request_id,
                    timestamp=created_at,
                    intent=cached_data.get("intent", "cached"),
                    complexity_score=cached_data.get("complexity_score", 0.0),
                    jev_confidence=1.0,
                    selected_route=RouteType.CACHE,
                    policy_reason="Exact semantic cache hit; bypassed System One and model execution.",
                    actual_model=cached_data.get("model", "cache"),
                    cache_hit=True,
                    fallback_triggered=False,
                    fallback_reason=None,
                    retries_attempted=0,
                    circuit_breaker_tripped=False,
                    error_category=None,
                    jev_latency_ms=0.0,
                    model_latency_ms=0.0,
                    gateway_overhead_ms=round(total_latency_ms, 2),
                    total_latency_ms=round(total_latency_ms, 2),
                    input_tokens=estimated_input_tokens,
                    output_tokens=cached_data.get("output_tokens", 20),
                    estimated_cost_usd=0.0,
                    baseline_cost_usd=baseline_cost,
                    cost_saved_usd=round(baseline_cost, 7),
                )
                return GatewayResponse(
                    request_id=request_id,
                    content=cached_data["content"],
                    route=RouteType.CACHE,
                    model=cached_data.get("model", "cache"),
                    telemetry=telemetry,
                )

        # ----------------------------------------------------------------------
        # 2. Main Gateway Pipeline (Cache Miss)
        # ----------------------------------------------------------------------
        async with self._lock:
            self._active_requests += 1

        try:
            # 2a. System One Decision
            decision = await self.decision_engine.evaluate(request.prompt)

            # 2b. Dynamic System State
            system_state = await self._capture_system_state()

            # 2c. Adaptive Policy Evaluation
            plan = self.policy_engine.evaluate(
                decision=decision,
                latency_budget_ms=request.latency_budget_ms,
                cost_budget=request.cost_budget,
                estimated_input_tokens=estimated_input_tokens,
                system_state=system_state,
            )

            # 2d. Model Provider Execution (with Circuit Breakers, Retries, Failover)
            (
                provider_resp,
                exec_fallback,
                exec_reason,
                retries_attempted,
                circuit_tripped,
                error_cat,
            ) = await self.registry.execute_route(
                route=plan.selected_route,
                prompt=request.prompt,
            )

        finally:
            async with self._lock:
                self._active_requests = max(0, self._active_requests - 1)

        # ----------------------------------------------------------------------
        # 3. Telemetry Accounting & Latency
        # ----------------------------------------------------------------------
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

        # ----------------------------------------------------------------------
        # 4. Conditional Cache Write-Back
        # ----------------------------------------------------------------------
        if self.cache and plan.allow_cache and not exec_fallback:
            await self.cache.set(
                cache_key,
                {
                    "content": provider_resp.content,
                    "model": provider_resp.model_name,
                    "intent": decision.intent.value,
                    "complexity_score": decision.complexity_score,
                    "output_tokens": provider_resp.output_tokens,
                    "baseline_cost_usd": baseline_cost_usd,
                },
                ttl_seconds=3600,
            )

        # Consolidate fallback signals
        fallback_triggered = plan.fallback_triggered or exec_fallback or decision.raw_details.get("circuit_breaker_tripped", False)
        fallback_reason = exec_reason or plan.fallback_reason or decision.raw_details.get("fallback_reason")
        circuit_breaker_tripped = circuit_tripped or decision.raw_details.get("circuit_breaker_tripped", False)
        error_category = error_cat or decision.raw_details.get("error_category")
        if not error_category and fallback_triggered:
            error_category = "policy_rejection" if "reject" in (fallback_reason or "") else "fallback"

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
            retries_attempted=retries_attempted,
            circuit_breaker_tripped=circuit_breaker_tripped,
            error_category=error_category,
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

        # ----------------------------------------------------------------------
        # 5. Telemetry Persistence
        # ----------------------------------------------------------------------
        if self.telemetry_repo:
            await self.telemetry_repo.save_trace(telemetry)

        return GatewayResponse(
            request_id=request_id,
            content=provider_resp.content,
            route=plan.selected_route,
            model=provider_resp.model_name,
            telemetry=telemetry,
        )
