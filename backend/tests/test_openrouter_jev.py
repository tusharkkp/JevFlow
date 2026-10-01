import pytest
import httpx
from backend.app.decision.openrouter_jev_engine import OpenRouterJevEngine
from backend.app.schemas.decision import IntentType, RouteRecommendation, ComplexityLevel


@pytest.mark.asyncio
async def test_openrouter_jev_engine_success():
    """Verify OpenRouterJevEngine parses valid alpha decisions response into DecisionResult."""
    async def mock_handler(request: httpx.Request):
        assert request.url.path.endswith("/api/alpha/decisions")
        assert "Bearer test-openrouter-key" in request.headers["Authorization"]
        return httpx.Response(
            status_code=200,
            json={
                "id": "gen-dec-123",
                "model": "typesafe/jev-1.13-20260917",
                "answers": {
                    "intent": {
                        "type": "choice",
                        "choice": "coding",
                        "confidence": 0.93,
                        "probabilities": {"coding": 0.93, "reasoning": 0.07},
                    },
                    "complexity": {
                        "type": "score",
                        "score": 1.65,
                        "confidence": 0.88,
                        "legend": {"0": "Simple", "1": "Moderate", "2": "Complex"},
                        "probabilities": {"0": 0.0, "1": 0.35, "2": 0.65},
                    },
                    "safety": {
                        "type": "noul",
                        "noul": 0.99,
                    },
                    "execution_route": {
                        "type": "choice",
                        "choice": "frontier_model",
                        "confidence": 0.91,
                        "probabilities": {"frontier_model": 0.91, "small_model": 0.09},
                    },
                },
                "usage": {
                    "input_tokens": 150,
                    "output_tokens": 40,
                    "cost": 0.00003,
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        engine = OpenRouterJevEngine(
            api_key="test-openrouter-key",
            decisions_url="https://openrouter.ai/api/alpha/decisions",
            model="typesafe/jev-1.13",
            client=mock_client,
        )

        res = await engine.evaluate("Design a lock-free queue in C++")
        assert res.intent == IntentType.CODING
        assert res.complexity_score == 1.65
        assert res.complexity_level == ComplexityLevel.COMPLEX
        assert res.safety_probability == 0.99
        assert res.is_safe is True
        assert res.recommended_route == RouteRecommendation.FRONTIER_MODEL
        assert res.confidence == 0.91
        assert res.model_used == "typesafe/jev-1.13-20260917"
        assert res.decision_latency_ms >= 0.0
        assert res.raw_details["cost_usd"] == 0.00003


@pytest.mark.asyncio
async def test_openrouter_jev_engine_missing_key_fallback():
    """Verify fallback engine is used when API key is None."""
    engine = OpenRouterJevEngine(api_key=None)
    res = await engine.evaluate("Hello world")
    assert res is not None
    assert res.raw_details.get("fallback_reason") == "missing_openrouter_api_key"


@pytest.mark.asyncio
async def test_openrouter_jev_engine_api_error_fallback():
    """Verify OpenRouterJevEngine degrades to fallback on HTTP errors."""
    async def mock_handler(request: httpx.Request):
        return httpx.Response(status_code=500, json={"error": {"message": "Service unavailable"}})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        engine = OpenRouterJevEngine(
            api_key="test-openrouter-key",
            client=mock_client,
        )

        res = await engine.evaluate("Hello")
        assert res is not None
        assert "openrouter_exception" in res.raw_details.get("fallback_reason", "")
