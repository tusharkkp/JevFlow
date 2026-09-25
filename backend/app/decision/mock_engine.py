import time
from backend.app.decision.base import DecisionEngine
from backend.app.schemas.decision import (
    DecisionResult,
    IntentType,
    ComplexityLevel,
    RouteRecommendation,
)


class MockDecisionEngine(DecisionEngine):
    """
    Mock System One Decision Engine for Phase 1 testing.
    
    Uses transparent, deterministic rules to produce realistic
    probabilistic distributions without requiring an external API key.
    """

    def __init__(self, simulated_latency_ms: float = 12.0):
        self.simulated_latency_ms = simulated_latency_ms

    async def evaluate(self, prompt: str) -> DecisionResult:
        start_time = time.perf_counter()
        lowered = prompt.lower().strip()

        # 1. Safety check simulation
        suspicious_keywords = ["ignore previous instructions", "jailbreak", "sudo", "bypass security"]
        is_suspicious = any(kw in lowered for kw in suspicious_keywords)
        safety_prob = 0.15 if is_suspicious else 0.98
        is_safe = safety_prob >= 0.80

        # 2. Intent classification simulation
        if is_suspicious:
            intent = IntentType.OTHER
            recommended_route = RouteRecommendation.HUMAN_REVIEW
            complexity_score = 1.9
            complexity_level = ComplexityLevel.COMPLEX
            confidence = 0.95
        elif any(kw in lowered for kw in ["def ", "class ", "function", "code", "bug", "sql", "python", "javascript"]):
            intent = IntentType.CODING
            # Determine complexity from query length / detail
            if len(lowered.split()) > 20 or "architect" in lowered or "refactor" in lowered:
                complexity_score = 1.7
                complexity_level = ComplexityLevel.COMPLEX
                recommended_route = RouteRecommendation.FRONTIER_MODEL
                confidence = 0.91
            else:
                complexity_score = 0.8
                complexity_level = ComplexityLevel.MODERATE
                recommended_route = RouteRecommendation.SMALL_MODEL
                confidence = 0.88
        elif any(kw in lowered for kw in ["why", "compare", "proof", "reason", "philosophy", "trade-off", "tradeoff"]):
            intent = IntentType.REASONING
            complexity_score = 1.6
            complexity_level = ComplexityLevel.COMPLEX
            recommended_route = RouteRecommendation.FRONTIER_MODEL
            confidence = 0.89
        elif any(kw in lowered for kw in ["summarize", "tl;dr", "tldr", "condense", "brief"]):
            intent = IntentType.SUMMARIZATION
            complexity_score = 0.7
            complexity_level = ComplexityLevel.MODERATE
            recommended_route = RouteRecommendation.SMALL_MODEL
            confidence = 0.87
        elif any(kw in lowered for kw in ["hello", "hi", "hey", "ping", "test"]):
            intent = IntentType.FACTUAL_QUESTION
            complexity_score = 0.1
            complexity_level = ComplexityLevel.SIMPLE
            recommended_route = RouteRecommendation.DETERMINISTIC
            confidence = 0.99
        else:
            # Default / general factual question
            intent = IntentType.FACTUAL_QUESTION
            complexity_score = 0.4
            complexity_level = ComplexityLevel.SIMPLE
            recommended_route = RouteRecommendation.SMALL_MODEL
            confidence = 0.84

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0 + self.simulated_latency_ms

        return DecisionResult(
            intent=intent,
            complexity_score=complexity_score,
            complexity_level=complexity_level,
            safety_probability=safety_prob,
            is_safe=is_safe,
            recommended_route=recommended_route,
            confidence=confidence,
            decision_latency_ms=round(elapsed_ms, 2),
            model_used="mock-system-one-v1",
            raw_details={
                "probabilities": {
                    recommended_route.value: confidence,
                    "other": round(1.0 - confidence, 4),
                }
            }
        )
