import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.schemas.request import GatewayRequest
from backend.app.schemas.response import GatewayResponse, TelemetryTrace, RouteType
from backend.app.decision.base import DecisionEngine
from backend.app.decision.mock_engine import MockDecisionEngine
from backend.app.policy.engine import PolicyEngine
from backend.app.providers.base import ModelProvider
from backend.app.providers.mock_provider import MockModelProvider


class GatewayService:
    """
    Central Orchestrator for JevFlow.
    
    Coordinates the pipeline:
    Client Request -> System One Decision -> Deterministic Policy -> Execution Provider -> Observability Telemetry
    """

    def __init__(
        self,
        decision_engine: Optional[DecisionEngine] = None,
        policy_engine: Optional[PolicyEngine] = None,
        provider: Optional[ModelProvider] = None,
    ):
        self.decision_engine = decision_engine or MockDecisionEngine()
        self.policy_engine = policy_engine or PolicyEngine()
        self.provider = provider or MockModelProvider()

    async def process_request(self, request: GatewayRequest) -> GatewayResponse:
        start_overall = time.perf_counter()
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc)

        # 1. System One Decision
        decision = await self.decision_engine.evaluate(request.prompt)

        # 2. Deterministic Policy Evaluation
        plan = self.policy_engine.evaluate(
            decision=decision,
            latency_budget_ms=request.latency_budget_ms,
            cost_budget=request.cost_budget,
        )

        # 3. Model Provider Execution
        provider_resp = await self.provider.generate(
            prompt=request.prompt,
            route=plan.selected_route,
        )

        # 4. Latency & Cost Telemetry Accounting
        end_overall = time.perf_counter()
        total_latency_ms = (end_overall - start_overall) * 1000.0

        # Calculate pure gateway overhead: total time minus decision & provider model time
        gateway_overhead_ms = max(
            0.1,
            total_latency_ms - decision.decision_latency_ms - provider_resp.latency_ms,
        )

        # Baseline cost calculation: What would this exact request have cost if routed to Frontier?
        baseline_cost_usd = self.provider.estimate_cost(
            input_tokens=provider_resp.input_tokens,
            output_tokens=provider_resp.output_tokens,
            route=RouteType.FRONTIER_MODEL,
        )
        cost_saved_usd = max(0.0, baseline_cost_usd - provider_resp.cost_usd)

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
            fallback_triggered=plan.fallback_triggered,
            fallback_reason=plan.fallback_reason,
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
