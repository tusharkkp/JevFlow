from typing import Optional
from pydantic import BaseModel
from backend.app.core.config import settings, Settings
from backend.app.schemas.decision import DecisionResult, RouteRecommendation
from backend.app.schemas.response import RouteType


class ExecutionPlan(BaseModel):
    """Deterministic routing decision produced by the Policy Engine."""
    selected_route: RouteType
    policy_reason: str
    allow_cache: bool = True
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None


class PolicyEngine:
    """
    Deterministic Policy Engine.
    
    Translates probabilistic signals from the System One decision layer
    and runtime constraints (budgets, safety thresholds) into an immutable ExecutionPlan.
    """

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or settings

    def evaluate(
        self,
        decision: DecisionResult,
        latency_budget_ms: Optional[int] = None,
        cost_budget: Optional[float] = None,
    ) -> ExecutionPlan:
        # 1. Gate: Deterministic Safety Enforcement
        if not decision.is_safe or decision.safety_probability < 0.80:
            if self.config.ENABLE_HUMAN_REVIEW:
                return ExecutionPlan(
                    selected_route=RouteType.HUMAN_REVIEW,
                    policy_reason="Safety risk identified (prob < 0.80); routed to human review.",
                    allow_cache=False,
                )
            else:
                return ExecutionPlan(
                    selected_route=RouteType.FALLBACK,
                    policy_reason="Safety check failed and human review disabled; rejected.",
                    allow_cache=False,
                    fallback_triggered=True,
                    fallback_reason="safety_rejection",
                )

        # 2. Gate: Runtime Latency Budget Constraint
        if latency_budget_ms is not None and latency_budget_ms < 500:
            return ExecutionPlan(
                selected_route=RouteType.SMALL_MODEL,
                policy_reason=f"Strict client latency budget ({latency_budget_ms}ms < 500ms); forced low-latency route.",
                allow_cache=True,
            )

        # 3. Gate: Cost Budget Constraint
        if cost_budget is not None and cost_budget < 0.005:
            return ExecutionPlan(
                selected_route=RouteType.SMALL_MODEL,
                policy_reason=f"Strict client cost budget (${cost_budget:.4f}); frontier model disallowed.",
                allow_cache=True,
            )

        # 4. Gate: Low-Confidence Escalation
        if decision.confidence < self.config.MEDIUM_CONFIDENCE_THRESHOLD:
            return ExecutionPlan(
                selected_route=RouteType.FRONTIER_MODEL,
                policy_reason=(
                    f"Decision confidence ({decision.confidence:.2f}) below threshold "
                    f"({self.config.MEDIUM_CONFIDENCE_THRESHOLD}); escalated to frontier model."
                ),
                allow_cache=True,
            )

        # 5. Gate: Complexity & Intent Evaluation
        if decision.complexity_score <= 0.3 and decision.confidence >= self.config.HIGH_CONFIDENCE_THRESHOLD:
            if decision.recommended_route == RouteRecommendation.DETERMINISTIC:
                return ExecutionPlan(
                    selected_route=RouteType.DETERMINISTIC,
                    policy_reason="Trivial complexity with high confidence; routed to zero-cost deterministic engine.",
                    allow_cache=True,
                )
            return ExecutionPlan(
                selected_route=RouteType.SMALL_MODEL,
                policy_reason="Low complexity with high confidence; routed to small/cheap model.",
                allow_cache=True,
            )

        if decision.complexity_score >= 1.5 or decision.intent.value == "reasoning":
            return ExecutionPlan(
                selected_route=RouteType.FRONTIER_MODEL,
                policy_reason="High complexity or multi-step reasoning requirement; routed to frontier model.",
                allow_cache=True,
            )

        # 6. Default: Honor System One Recommendation mapped to RouteType
        route_mapping = {
            RouteRecommendation.DETERMINISTIC: RouteType.DETERMINISTIC,
            RouteRecommendation.CACHE: RouteType.CACHE,
            RouteRecommendation.SMALL_MODEL: RouteType.SMALL_MODEL,
            RouteRecommendation.FRONTIER_MODEL: RouteType.FRONTIER_MODEL,
            RouteRecommendation.HUMAN_REVIEW: RouteType.HUMAN_REVIEW,
        }
        mapped_route = route_mapping.get(decision.recommended_route, RouteType.SMALL_MODEL)

        return ExecutionPlan(
            selected_route=mapped_route,
            policy_reason=f"Standard policy matched recommendation: {decision.recommended_route.value}.",
            allow_cache=True,
        )
