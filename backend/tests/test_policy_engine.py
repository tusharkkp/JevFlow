import pytest
from backend.app.policy.engine import PolicyEngine
from backend.app.schemas.decision import (
    DecisionResult,
    IntentType,
    ComplexityLevel,
    RouteRecommendation,
)
from backend.app.schemas.response import RouteType


def test_policy_engine_safety_gate_triggers_review():
    engine = PolicyEngine()
    unsafe_decision = DecisionResult(
        intent=IntentType.OTHER,
        complexity_score=1.5,
        complexity_level=ComplexityLevel.COMPLEX,
        safety_probability=0.20,
        is_safe=False,
        recommended_route=RouteRecommendation.HUMAN_REVIEW,
        confidence=0.90,
        decision_latency_ms=10.0,
    )
    plan = engine.evaluate(unsafe_decision)
    assert plan.selected_route == RouteType.HUMAN_REVIEW
    assert "Safety risk" in plan.policy_reason
    assert not plan.allow_cache


def test_policy_engine_low_confidence_escalates_to_frontier():
    engine = PolicyEngine()
    low_confidence_decision = DecisionResult(
        intent=IntentType.FACTUAL_QUESTION,
        complexity_score=0.2,
        complexity_level=ComplexityLevel.SIMPLE,
        safety_probability=0.99,
        is_safe=True,
        recommended_route=RouteRecommendation.SMALL_MODEL,
        confidence=0.45,  # below 0.60
        decision_latency_ms=10.0,
    )
    plan = engine.evaluate(low_confidence_decision)
    assert plan.selected_route == RouteType.FRONTIER_MODEL
    assert "below threshold" in plan.policy_reason


def test_policy_engine_latency_budget_overrides_to_small_model():
    engine = PolicyEngine()
    complex_decision = DecisionResult(
        intent=IntentType.REASONING,
        complexity_score=1.8,
        complexity_level=ComplexityLevel.COMPLEX,
        safety_probability=0.99,
        is_safe=True,
        recommended_route=RouteRecommendation.FRONTIER_MODEL,
        confidence=0.95,
        decision_latency_ms=10.0,
    )
    # Strict latency budget of 300ms
    plan = engine.evaluate(complex_decision, latency_budget_ms=300)
    assert plan.selected_route == RouteType.SMALL_MODEL
    assert "latency budget" in plan.policy_reason


def test_policy_engine_trivial_high_confidence_deterministic_route():
    engine = PolicyEngine()
    trivial_decision = DecisionResult(
        intent=IntentType.FACTUAL_QUESTION,
        complexity_score=0.1,
        complexity_level=ComplexityLevel.SIMPLE,
        safety_probability=0.99,
        is_safe=True,
        recommended_route=RouteRecommendation.DETERMINISTIC,
        confidence=0.99,
        decision_latency_ms=8.0,
    )
    plan = engine.evaluate(trivial_decision)
    assert plan.selected_route == RouteType.DETERMINISTIC
    assert "Trivial complexity" in plan.policy_reason
