from typing import Optional, List
from pydantic import BaseModel, Field
from backend.app.core.config import settings, Settings
from backend.app.schemas.decision import DecisionResult, RouteRecommendation
from backend.app.schemas.response import RouteType
from backend.app.policy.state import SystemState


class ExecutionPlan(BaseModel):
    """Deterministic routing decision produced by the Adaptive Policy Engine."""
    selected_route: RouteType
    policy_reason: str
    applied_gates: List[str] = Field(default_factory=list)
    allow_cache: bool = True
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None


class PolicyEngine:
    """
    Deterministic Adaptive Policy Engine.
    
    Translates:
    (Probabilistic System One Signals + Request Constraints + Runtime System Conditions)
    ---> Binding ExecutionPlan
    """

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or settings

    def evaluate(
        self,
        decision: DecisionResult,
        latency_budget_ms: Optional[int] = None,
        cost_budget: Optional[float] = None,
        estimated_input_tokens: int = 15,
        system_state: Optional[SystemState] = None,
    ) -> ExecutionPlan:
        applied_gates: List[str] = []
        state = system_state or SystemState()

        # ----------------------------------------------------------------------
        # 1. Gate: Deterministic Safety Enforcement
        # ----------------------------------------------------------------------
        applied_gates.append("safety_gate")
        if not decision.is_safe or decision.safety_probability < 0.80:
            if self.config.ENABLE_HUMAN_REVIEW:
                return ExecutionPlan(
                    selected_route=RouteType.HUMAN_REVIEW,
                    policy_reason="Safety risk identified (prob < 0.80); routed to human review.",
                    applied_gates=applied_gates,
                    allow_cache=False,
                )
            else:
                return ExecutionPlan(
                    selected_route=RouteType.FALLBACK,
                    policy_reason="Safety check failed and human review disabled; rejected.",
                    applied_gates=applied_gates,
                    allow_cache=False,
                    fallback_triggered=True,
                    fallback_reason="safety_rejection",
                )

        # ----------------------------------------------------------------------
        # 2. Gate: Provider Health & Outage Failover
        # ----------------------------------------------------------------------
        applied_gates.append("provider_health_gate")
        frontier_healthy = state.is_provider_available(RouteType.FRONTIER_MODEL)
        small_healthy = state.is_provider_available(RouteType.SMALL_MODEL)

        # ----------------------------------------------------------------------
        # 3. Gate: High System Load Shedding
        # ----------------------------------------------------------------------
        applied_gates.append("load_shedding_gate")
        if state.load_ratio >= self.config.HIGH_LOAD_THRESHOLD:
            # Under high concurrency, shed heavy frontier calls to small model
            if small_healthy:
                return ExecutionPlan(
                    selected_route=RouteType.SMALL_MODEL,
                    policy_reason=(
                        f"High system load ({state.load_ratio:.0%} >= {self.config.HIGH_LOAD_THRESHOLD:.0%}); "
                        "adaptive load-shedding routed to small model."
                    ),
                    applied_gates=applied_gates,
                    allow_cache=True,
                )

        # ----------------------------------------------------------------------
        # 4. Gate: Dynamic Latency Budget Constraint
        # ----------------------------------------------------------------------
        applied_gates.append("latency_budget_gate")
        if latency_budget_ms is not None:
            observed_frontier_lat = state.provider_latencies_ms.get(RouteType.FRONTIER_MODEL.value, 140.0)
            # Factor in P95 network variance (2.2x) + decision latency
            frontier_p95_estimate = (observed_frontier_lat * 2.2) + decision.decision_latency_ms

            if latency_budget_ms < frontier_p95_estimate or latency_budget_ms < 500:
                target = RouteType.SMALL_MODEL if small_healthy else RouteType.DETERMINISTIC
                return ExecutionPlan(
                    selected_route=target,
                    policy_reason=(
                        f"Strict latency budget ({latency_budget_ms}ms < safe frontier threshold {frontier_p95_estimate:.0f}ms); "
                        "forced low-latency route."
                    ),
                    applied_gates=applied_gates,
                    allow_cache=True,
                )

        # ----------------------------------------------------------------------
        # 5. Gate: Token-Aware Cost Budget Constraint
        # ----------------------------------------------------------------------
        applied_gates.append("cost_budget_gate")
        if cost_budget is not None:
            # Frontier pricing: $3/1M in, $15/1M out. Assume ~60 output tokens.
            est_frontier_cost = (estimated_input_tokens / 1e6 * 3.0) + (60 / 1e6 * 15.0)
            if est_frontier_cost > cost_budget:
                return ExecutionPlan(
                    selected_route=RouteType.SMALL_MODEL if small_healthy else RouteType.DETERMINISTIC,
                    policy_reason=(
                        f"Cost budget (${cost_budget:.5f} < estimated frontier cost ${est_frontier_cost:.5f}); "
                        "adaptive policy clamped to small model."
                    ),
                    applied_gates=applied_gates,
                    allow_cache=True,
                )

        # ----------------------------------------------------------------------
        # 6. Gate: Low-Confidence Escalation
        # ----------------------------------------------------------------------
        applied_gates.append("confidence_escalation_gate")
        if decision.confidence < self.config.MEDIUM_CONFIDENCE_THRESHOLD:
            if frontier_healthy:
                return ExecutionPlan(
                    selected_route=RouteType.FRONTIER_MODEL,
                    policy_reason=(
                        f"Decision confidence ({decision.confidence:.2f}) below threshold "
                        f"({self.config.MEDIUM_CONFIDENCE_THRESHOLD}); escalated to frontier model."
                    ),
                    applied_gates=applied_gates,
                    allow_cache=True,
                )
            else:
                return ExecutionPlan(
                    selected_route=RouteType.SMALL_MODEL,
                    policy_reason="Low confidence, but frontier model unavailable; defaulted to small model.",
                    applied_gates=applied_gates,
                    allow_cache=True,
                    fallback_triggered=True,
                    fallback_reason="frontier_unavailable",
                )

        # ----------------------------------------------------------------------
        # 7. Gate: Complexity & Intent Evaluation
        # ----------------------------------------------------------------------
        applied_gates.append("complexity_intent_gate")
        if decision.complexity_score <= 0.3 and decision.confidence >= self.config.HIGH_CONFIDENCE_THRESHOLD:
            if decision.recommended_route == RouteRecommendation.DETERMINISTIC:
                return ExecutionPlan(
                    selected_route=RouteType.DETERMINISTIC,
                    policy_reason="Trivial complexity with high confidence; routed to zero-cost deterministic engine.",
                    applied_gates=applied_gates,
                    allow_cache=True,
                )
            return ExecutionPlan(
                selected_route=RouteType.SMALL_MODEL,
                policy_reason="Low complexity with high confidence; routed to small/cheap model.",
                applied_gates=applied_gates,
                allow_cache=True,
            )

        if decision.complexity_score >= 1.4 or decision.intent.value == "reasoning":
            if frontier_healthy:
                return ExecutionPlan(
                    selected_route=RouteType.FRONTIER_MODEL,
                    policy_reason="High complexity or multi-step reasoning requirement; routed to frontier model.",
                    applied_gates=applied_gates,
                    allow_cache=True,
                )
            else:
                return ExecutionPlan(
                    selected_route=RouteType.SMALL_MODEL,
                    policy_reason="Complex reasoning needed, but frontier unavailable; degraded to small model.",
                    applied_gates=applied_gates,
                    allow_cache=True,
                    fallback_triggered=True,
                    fallback_reason="frontier_unavailable",
                )

        # ----------------------------------------------------------------------
        # 8. Default: Map Jev Recommendation
        # ----------------------------------------------------------------------
        applied_gates.append("default_recommendation_mapping")
        route_mapping = {
            RouteRecommendation.DETERMINISTIC: RouteType.DETERMINISTIC,
            RouteRecommendation.CACHE: RouteType.CACHE,
            RouteRecommendation.SMALL_MODEL: RouteType.SMALL_MODEL,
            RouteRecommendation.FRONTIER_MODEL: RouteType.FRONTIER_MODEL,
            RouteRecommendation.HUMAN_REVIEW: RouteType.HUMAN_REVIEW,
        }
        mapped_route = route_mapping.get(decision.recommended_route, RouteType.SMALL_MODEL)

        # Fallback if mapped route is currently unavailable
        if mapped_route == RouteType.FRONTIER_MODEL and not frontier_healthy:
            return ExecutionPlan(
                selected_route=RouteType.SMALL_MODEL,
                policy_reason="Frontier model recommended, but currently unavailable; routed to small model.",
                applied_gates=applied_gates,
                allow_cache=True,
                fallback_triggered=True,
                fallback_reason="frontier_unavailable",
            )

        return ExecutionPlan(
            selected_route=mapped_route,
            policy_reason=f"Standard policy matched recommendation: {decision.recommended_route.value}.",
            applied_gates=applied_gates,
            allow_cache=True,
        )
