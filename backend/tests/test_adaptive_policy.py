import pytest
from backend.app.policy.engine import PolicyEngine
from backend.app.policy.state import SystemState
from backend.app.schemas.decision import (
    DecisionResult,
    IntentType,
    ComplexityLevel,
    RouteRecommendation,
)
from backend.app.schemas.response import RouteType


def make_decision(
    intent: IntentType = IntentType.REASONING,
    complexity: float = 1.7,
    confidence: float = 0.92,
    safety_prob: float = 0.98,
    rec_route: RouteRecommendation = RouteRecommendation.FRONTIER_MODEL,
) -> DecisionResult:
    return DecisionResult(
        intent=intent,
        complexity_score=complexity,
        complexity_level=ComplexityLevel.COMPLEX if complexity >= 1.4 else ComplexityLevel.MODERATE,
        safety_probability=safety_prob,
        is_safe=(safety_prob >= 0.80),
        recommended_route=rec_route,
        confidence=confidence,
        decision_latency_ms=12.0,
    )


def test_adaptive_policy_sheds_load_under_high_concurrency():
    engine = PolicyEngine()
    decision = make_decision()
    
    # Simulate 85% load (85 active requests out of 100 max)
    state = SystemState(active_requests=85, max_concurrency=100)
    assert state.load_ratio == 0.85

    plan = engine.evaluate(decision=decision, system_state=state)
    assert plan.selected_route == RouteType.SMALL_MODEL
    assert "load-shedding" in plan.policy_reason
    assert "load_shedding_gate" in plan.applied_gates


def test_adaptive_policy_handles_frontier_provider_outage():
    engine = PolicyEngine()
    decision = make_decision()  # Complex reasoning requiring Frontier

    # Frontier is currently down / unavailable
    state = SystemState(
        provider_status={
            RouteType.FRONTIER_MODEL.value: "unavailable",
            RouteType.SMALL_MODEL.value: "healthy",
            RouteType.DETERMINISTIC.value: "healthy",
        }
    )

    plan = engine.evaluate(decision=decision, system_state=state)
    assert plan.selected_route == RouteType.SMALL_MODEL
    assert plan.fallback_triggered is True
    assert plan.fallback_reason == "frontier_unavailable"
    assert "frontier unavailable" in plan.policy_reason.lower()


def test_adaptive_policy_token_aware_cost_budget():
    engine = PolicyEngine()
    decision = make_decision()

    # Client specifies a $0.0001 budget
    # Frontier model cost for 500 input tokens is ~0.0024, far exceeding budget
    plan = engine.evaluate(
        decision=decision,
        cost_budget=0.0001,
        estimated_input_tokens=500,
    )
    assert plan.selected_route == RouteType.SMALL_MODEL
    assert "cost budget" in plan.policy_reason.lower()
    assert "cost_budget_gate" in plan.applied_gates


def test_adaptive_policy_dynamic_latency_budget_clamping():
    engine = PolicyEngine()
    decision = make_decision()

    # Observed frontier latency is 200ms + decision latency 12ms = 212ms
    state = SystemState(
        provider_latencies_ms={
            RouteType.FRONTIER_MODEL.value: 200.0,
            RouteType.SMALL_MODEL.value: 30.0,
        }
    )

    # Client sets a 150ms budget (< 212ms)
    plan = engine.evaluate(
        decision=decision,
        latency_budget_ms=150,
        system_state=state,
    )
    assert plan.selected_route == RouteType.SMALL_MODEL
    assert "latency budget" in plan.policy_reason.lower()
    assert "latency_budget_gate" in plan.applied_gates


def test_adaptive_policy_low_confidence_escalation_when_frontier_healthy():
    engine = PolicyEngine()
    low_conf_decision = make_decision(confidence=0.45)  # Below 0.60
    state = SystemState()

    plan = engine.evaluate(decision=low_conf_decision, system_state=state)
    assert plan.selected_route == RouteType.FRONTIER_MODEL
    assert "below threshold" in plan.policy_reason
