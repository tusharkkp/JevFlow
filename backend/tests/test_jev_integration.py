import json
import pytest
import httpx
from backend.app.jev.client import (
    TypeSafeJevClient,
    TypeSafeAuthError,
    TypeSafeValidationError,
    TypeSafeTimeoutError,
    TypeSafeAPIError,
)
from backend.app.decision.jev_engine import TypeSafeJevEngine
from backend.app.schemas.decision import IntentType, ComplexityLevel, RouteRecommendation


SAMPLE_SYSTEM_ONE_RESPONSE = {
    "model": "jev-latest",
    "answers": {
        "intent": {
            "type": "choice",
            "choice": "coding",
            "confidence": 0.94,
            "probabilities": {
                "coding": 0.94,
                "reasoning": 0.04,
                "factual_question": 0.02
            }
        },
        "complexity": {
            "type": "score",
            "score": 1.65,
            "confidence": 0.89,
            "legend": {
                "0": "Simple",
                "1": "Moderate",
                "2": "Complex"
            },
            "probabilities": {
                "0": 0.05,
                "1": 0.25,
                "2": 0.70
            }
        },
        "safety": {
            "type": "noul",
            "noul": 0.97
        },
        "execution_route": {
            "type": "choice",
            "choice": "frontier_model",
            "confidence": 0.91,
            "probabilities": {
                "frontier_model": 0.91,
                "small_model": 0.09
            }
        }
    },
    "usage": {
        "input_tokens": 145,
        "output_tokens": 16
    }
}


@pytest.mark.asyncio
async def test_jev_client_success():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test_key_123"
        return httpx.Response(200, json=SAMPLE_SYSTEM_ONE_RESPONSE)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as custom_http_client:
        client = TypeSafeJevClient(api_key="test_key_123", http_client=custom_http_client)
        result = await client.evaluate_system_one(
            state="Write a lock-free ring buffer in C++",
            questions={"intent": {"type": "choice"}}
        )
        assert result["model"] == "jev-latest"
        assert result["answers"]["intent"]["choice"] == "coding"


@pytest.mark.asyncio
async def test_jev_client_auth_error_on_401():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Unauthorized"})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as custom_http_client:
        client = TypeSafeJevClient(api_key="invalid_key", http_client=custom_http_client)
        with pytest.raises(TypeSafeAuthError):
            await client.evaluate_system_one(state="test", questions={})


@pytest.mark.asyncio
async def test_jev_client_validation_error_on_422():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": [{"loc": ["body", "state"], "msg": "Field required"}]})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as custom_http_client:
        client = TypeSafeJevClient(api_key="test_key", http_client=custom_http_client)
        with pytest.raises(TypeSafeValidationError):
            await client.evaluate_system_one(state=None, questions={})


@pytest.mark.asyncio
async def test_jev_engine_parses_sample_response_correctly():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_SYSTEM_ONE_RESPONSE)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as custom_http_client:
        client = TypeSafeJevClient(api_key="valid_key", http_client=custom_http_client)
        engine = TypeSafeJevEngine(client=client)

        decision = await engine.evaluate("Write a lock-free queue in Rust")

        assert decision.intent == IntentType.CODING
        assert decision.complexity_score == 1.65
        assert decision.complexity_level == ComplexityLevel.COMPLEX
        assert decision.safety_probability == 0.97
        assert decision.is_safe is True
        assert decision.recommended_route == RouteRecommendation.FRONTIER_MODEL
        assert decision.confidence == 0.91
        assert decision.model_used == "jev-latest"
        assert decision.decision_latency_ms > 0.0


@pytest.mark.asyncio
async def test_jev_engine_graceful_fallback_when_api_key_missing():
    # Engine instantiated with no API key
    client = TypeSafeJevClient(api_key=None)
    engine = TypeSafeJevEngine(client=client)

    decision = await engine.evaluate("Hello, test!")
    assert decision is not None
    assert decision.raw_details.get("fallback_reason") == "missing_typesafe_api_key"


@pytest.mark.asyncio
async def test_jev_engine_graceful_fallback_on_network_timeout():
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Connection timed out after 1500ms")

    transport = httpx.MockTransport(timeout_handler)
    async with httpx.AsyncClient(transport=transport) as custom_http_client:
        client = TypeSafeJevClient(api_key="valid_key", http_client=custom_http_client)
        engine = TypeSafeJevEngine(client=client)

        decision = await engine.evaluate("Explain quantum entanglement")
        assert decision is not None
        assert "fallback_reason" in decision.raw_details
        assert "timed out" in decision.raw_details["fallback_reason"].lower()
