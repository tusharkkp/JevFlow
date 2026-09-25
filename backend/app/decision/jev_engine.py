import time
import logging
from typing import Optional, Dict, Any

from backend.app.core.config import settings, Settings
from backend.app.decision.base import DecisionEngine
from backend.app.decision.mock_engine import MockDecisionEngine
from backend.app.jev.client import (
    TypeSafeJevClient,
    TypeSafeError,
    TypeSafeTimeoutError,
    TypeSafeAuthError,
)
from backend.app.reliability.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenException,
)
from backend.app.schemas.decision import (
    DecisionResult,
    IntentType,
    ComplexityLevel,
    RouteRecommendation,
)

logger = logging.getLogger("jevflow.jev_engine")


class TypeSafeJevEngine(DecisionEngine):
    """
    Live System One Decision Engine powered by TypeSafe Jev API.
    
    Submits structured questions to POST /v1/systemone:
    - intent (ChoiceQuestion)
    - complexity (ScoreQuestion)
    - safety (NoulQuestion)
    - execution_route (ChoiceQuestion)
    
    If Jev times out or is unreachable, degrades gracefully to fallback.
    """

    SYSTEM_ONE_QUESTIONS = {
        "intent": {
            "type": "choice",
            "instructions": "What is the primary intent of this user request?",
            "criteria": {
                "factual_question": "Direct question asking for facts, definitions, or concise answers.",
                "coding": "Request to write, debug, explain, or refactor code.",
                "reasoning": "Multi-step logic, math, planning, architectural analysis, or problem-solving.",
                "summarization": "Condensing or summarizing existing text.",
                "creative": "Open-ended storytelling, creative writing, or brainstorming.",
                "other": "Requests that do not clearly fit the other categories.",
            },
        },
        "complexity": {
            "type": "score",
            "instructions": "How computationally or cognitively complex is this prompt?",
            "criteria": [
                "Simple: Direct lookup, greeting, concise query, trivial answer.",
                "Moderate: Multi-sentence answer, standard explanation or straightforward coding.",
                "Complex: Deep reasoning, architecture design, edge-case analysis, or large synthesis.",
            ],
        },
        "safety": {
            "type": "noul",
            "instructions": "Is this request safe to execute automatically?",
            "criteria": {
                "true": "The request contains no harmful commands, injection attacks, or sensitive operations.",
                "false": "The request contains prompt injections, malicious payloads, or dangerous commands.",
            },
        },
        "execution_route": {
            "type": "choice",
            "instructions": "Which execution route is best suited for this request?",
            "criteria": {
                "deterministic": "Trivial or greetings that can be answered statically.",
                "small_model": "Straightforward tasks, standard coding, or simple summaries.",
                "frontier_model": "Complex reasoning, architecture, deep debugging, or high-nuance synthesis.",
                "human_review": "Dangerous, ambiguous, or security-sensitive requests.",
            },
        },
    }

    def __init__(
        self,
        client: Optional[TypeSafeJevClient] = None,
        config: Optional[Settings] = None,
        fallback_engine: Optional[DecisionEngine] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.config = config or settings
        self.client = client or TypeSafeJevClient(
            api_key=self.config.TYPESAFE_API_KEY,
            base_url=self.config.TYPESAFE_BASE_URL,
            timeout_ms=self.config.JEV_TIMEOUT_MS,
        )
        self.fallback_engine = fallback_engine or MockDecisionEngine()
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name="jev_system_one",
            failure_threshold=3,
            recovery_timeout_sec=10.0,
        )

    async def evaluate(self, prompt: str) -> DecisionResult:
        start_time = time.perf_counter()

        # 1. If API key is not set, gracefully degrade immediately
        if not self.client.api_key:
            logger.info("TypeSafe API Key not set; using local fallback decision engine.")
            result = await self.fallback_engine.evaluate(prompt)
            result.raw_details["fallback_reason"] = "missing_typesafe_api_key"
            result.raw_details["error_category"] = "none"
            return result

        # 2. Execute via Circuit Breaker
        try:
            raw_response = await self.circuit_breaker.call(
                self.client.evaluate_system_one,
                state=prompt,
                questions=self.SYSTEM_ONE_QUESTIONS,
                model=self.config.JEV_DEFAULT_MODEL,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return self._parse_jev_response(raw_response, elapsed_ms)

        except CircuitBreakerOpenException as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning("Jev Circuit Breaker OPEN; failing fast to local fallback engine.")
            fallback_result = await self.fallback_engine.evaluate(prompt)
            fallback_result.raw_details["fallback_reason"] = "jev_circuit_breaker_open"
            fallback_result.raw_details["circuit_breaker_tripped"] = True
            fallback_result.raw_details["error_category"] = "circuit_breaker_open"
            fallback_result.raw_details["jev_attempt_latency_ms"] = round(elapsed_ms, 2)
            return fallback_result

        except (TypeSafeTimeoutError, TypeSafeError, Exception) as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            error_cat = "timeout" if isinstance(exc, TypeSafeTimeoutError) else "jev_error"
            logger.warning("Jev System One error (%s: %s); falling back to local heuristic.", error_cat, exc)
            fallback_result = await self.fallback_engine.evaluate(prompt)
            fallback_result.raw_details["fallback_reason"] = f"jev_exception: {str(exc)}"
            fallback_result.raw_details["error_category"] = error_cat
            fallback_result.raw_details["circuit_breaker_tripped"] = (self.circuit_breaker.state.value == "open")
            fallback_result.raw_details["jev_attempt_latency_ms"] = round(elapsed_ms, 2)
            return fallback_result

    def _parse_jev_response(self, raw: Dict[str, Any], elapsed_ms: float) -> DecisionResult:
        answers = raw.get("answers", {})
        model_name = raw.get("model", self.config.JEV_DEFAULT_MODEL)

        # 1. Parse Intent Answer
        intent_data = answers.get("intent", {})
        raw_intent = intent_data.get("choice", "other")
        try:
            intent = IntentType(raw_intent)
        except ValueError:
            intent = IntentType.OTHER
        intent_confidence = float(intent_data.get("confidence", 0.8))

        # 2. Parse Complexity Answer
        complexity_data = answers.get("complexity", {})
        complexity_score = float(complexity_data.get("score", 1.0))
        complexity_confidence = float(complexity_data.get("confidence", 0.8))
        if complexity_score < 0.6:
            complexity_level = ComplexityLevel.SIMPLE
        elif complexity_score < 1.4:
            complexity_level = ComplexityLevel.MODERATE
        else:
            complexity_level = ComplexityLevel.COMPLEX

        # 3. Parse Safety Answer
        safety_data = answers.get("safety", {})
        safety_prob = float(safety_data.get("noul", 0.95))
        is_safe = safety_prob >= 0.80

        # 4. Parse Execution Route Answer
        route_data = answers.get("execution_route", {})
        raw_route = route_data.get("choice", "small_model")
        try:
            recommended_route = RouteRecommendation(raw_route)
        except ValueError:
            recommended_route = RouteRecommendation.SMALL_MODEL
        route_confidence = float(route_data.get("confidence", 0.8))

        # Combined confidence metric (harmonic mean or minimum between intent and route confidence)
        overall_confidence = round(min(intent_confidence, route_confidence), 4)

        return DecisionResult(
            intent=intent,
            complexity_score=round(complexity_score, 3),
            complexity_level=complexity_level,
            safety_probability=round(safety_prob, 4),
            is_safe=is_safe,
            recommended_route=recommended_route,
            confidence=overall_confidence,
            decision_latency_ms=round(elapsed_ms, 2),
            model_used=model_name,
            raw_details={
                "usage": raw.get("usage", {}),
                "intent_probabilities": intent_data.get("probabilities", {}),
                "complexity_probabilities": complexity_data.get("probabilities", {}),
                "route_probabilities": route_data.get("probabilities", {}),
            },
        )
