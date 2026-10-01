import time
import logging
from typing import Optional, Dict, Any
import httpx

from backend.app.core.config import settings, Settings
from backend.app.decision.base import DecisionEngine
from backend.app.decision.mock_engine import MockDecisionEngine
from backend.app.reliability.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from backend.app.schemas.decision import (
    DecisionResult,
    IntentType,
    ComplexityLevel,
    RouteRecommendation,
)

logger = logging.getLogger("jevflow.openrouter_jev_engine")


class OpenRouterJevEngine(DecisionEngine):
    """
    Live System One Decision Engine powered by OpenRouter's TypeSafe JEV Decisions API.
    
    Endpoint: POST https://openrouter.ai/api/alpha/decisions
    Model: typesafe/jev-1.13 (or ~typesafe/jev-latest)
    
    Submits structured System One decision questions:
    - intent (ChoiceQuestion) -> factual_question, coding, reasoning, summarization, creative, other
    - complexity (ScoreQuestion) -> 0.0 to 2.0 (Simple, Moderate, Complex)
    - safety (NoulQuestion) -> P(safe) from 0.0 to 1.0
    - execution_route (ChoiceQuestion) -> deterministic, small_model, frontier_model, human_review
    
    If OpenRouter times out or errors, gracefully degrades to local calibrated heuristics.
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
        api_key: Optional[str] = None,
        decisions_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: float = 8.0,
        config: Optional[Settings] = None,
        fallback_engine: Optional[DecisionEngine] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.config = config or settings
        self.api_key = api_key or self.config.OPENROUTER_API_KEY or self.config.OPENAI_API_KEY
        self.decisions_url = (
            decisions_url
            or getattr(self.config, "OPENROUTER_DECISIONS_URL", "https://openrouter.ai/api/alpha/decisions")
            or "https://openrouter.ai/api/alpha/decisions"
        ).rstrip("/")
        self.model = model or getattr(self.config, "JEV_DECISION_MODEL", "typesafe/jev-1.13") or "typesafe/jev-1.13"
        self.timeout_seconds = timeout_seconds
        self.fallback_engine = fallback_engine or MockDecisionEngine()
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name="openrouter_jev",
            failure_threshold=3,
            recovery_timeout_sec=10.0,
        )
        self._injected_client = client

    async def evaluate(self, prompt: str) -> DecisionResult:
        start_time = time.perf_counter()

        if not self.api_key:
            logger.info("OpenRouter API key not configured; falling back to local decision engine.")
            result = await self.fallback_engine.evaluate(prompt)
            result.raw_details["fallback_reason"] = "missing_openrouter_api_key"
            result.raw_details["error_category"] = "none"
            return result

        try:
            data = await self.circuit_breaker.call(self._call_openrouter, prompt)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return self._parse_response(data, elapsed_ms)

        except CircuitBreakerOpenException as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning("OpenRouter JEV Circuit Breaker OPEN; falling back to local heuristics: %s", exc)
            fallback = await self.fallback_engine.evaluate(prompt)
            fallback.raw_details["fallback_reason"] = "openrouter_circuit_breaker_open"
            fallback.raw_details["circuit_breaker_tripped"] = True
            fallback.raw_details["error_category"] = "circuit_breaker_open"
            fallback.raw_details["jev_attempt_latency_ms"] = round(elapsed_ms, 2)
            return fallback

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning("OpenRouter JEV evaluation failed (%s); falling back to local heuristics.", exc)
            fallback = await self.fallback_engine.evaluate(prompt)
            fallback.raw_details["fallback_reason"] = f"openrouter_exception: {str(exc)}"
            fallback.raw_details["error_category"] = "timeout" if isinstance(exc, httpx.TimeoutException) else "jev_error"
            fallback.raw_details["circuit_breaker_tripped"] = (self.circuit_breaker.state.value == "open")
            fallback.raw_details["jev_attempt_latency_ms"] = round(elapsed_ms, 2)
            return fallback

    async def _call_openrouter(self, prompt: str) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/tusharkkp/JevFlow",
            "X-Title": "JevFlow Gateway",
        }

        payload = {
            "model": self.model,
            "state": prompt,
            "questions": self.SYSTEM_ONE_QUESTIONS,
        }

        if self._injected_client is not None:
            resp = await self._injected_client.post(
                self.decisions_url, headers=headers, json=payload, timeout=self.timeout_seconds
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(self.decisions_url, headers=headers, json=payload)

        if resp.status_code != 200:
            raise RuntimeError(f"OpenRouter Decisions API returned status {resp.status_code}: {resp.text}")

        return resp.json()

    def _parse_response(self, data: Dict[str, Any], elapsed_ms: float) -> DecisionResult:
        answers = data.get("answers", {})
        model_name = data.get("model", self.model)
        usage = data.get("usage", {})

        # 1. Parse Intent (Choice)
        intent_data = answers.get("intent", {})
        raw_intent = str(intent_data.get("choice", "other")).lower().strip()
        try:
            intent = IntentType(raw_intent)
        except ValueError:
            intent = IntentType.OTHER
        intent_confidence = float(intent_data.get("confidence", 0.8))

        # 2. Parse Complexity (Score 0.0 to 2.0)
        complexity_data = answers.get("complexity", {})
        try:
            complexity_score = min(2.0, max(0.0, float(complexity_data.get("score", 1.0))))
        except (ValueError, TypeError):
            complexity_score = 1.0

        if complexity_score < 0.6:
            complexity_level = ComplexityLevel.SIMPLE
        elif complexity_score < 1.4:
            complexity_level = ComplexityLevel.MODERATE
        else:
            complexity_level = ComplexityLevel.COMPLEX

        # 3. Parse Safety (Noul 0.0 to 1.0)
        safety_data = answers.get("safety", {})
        try:
            safety_prob = min(1.0, max(0.0, float(safety_data.get("noul", 0.95))))
        except (ValueError, TypeError):
            safety_prob = 0.95
        is_safe = safety_prob >= 0.80

        # 4. Parse Recommended Route (Choice)
        route_data = answers.get("execution_route", {})
        raw_route = str(route_data.get("choice", "small_model")).lower().strip()
        try:
            recommended_route = RouteRecommendation(raw_route)
        except ValueError:
            recommended_route = RouteRecommendation.SMALL_MODEL
        route_confidence = float(route_data.get("confidence", 0.8))

        # 5. Combined Confidence
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
                "usage": usage,
                "cost_usd": float(usage.get("cost", 0.0)),
                "intent_probabilities": intent_data.get("probabilities", {}),
                "complexity_probabilities": complexity_data.get("probabilities", {}),
                "route_probabilities": route_data.get("probabilities", {}),
                "source": "openrouter_jev_decisions",
                "model": model_name,
                "id": data.get("id"),
            },
        )
