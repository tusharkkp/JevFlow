import pytest
import httpx
from unittest.mock import AsyncMock, patch

from backend.app.providers.openrouter_jev_provider import OpenRouterJevProvider
from backend.app.providers.registry import ProviderRegistry
from backend.app.core.config import Settings


@pytest.mark.asyncio
async def test_openrouter_jev_provider_success():
    mock_response_data = {
        "id": "gen-12345",
        "model": "openai/gpt-6-luna-20260922",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "A mutex is a locking mechanism, whereas a semaphore is a signaling mechanism."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 40,
            "total_tokens": 55,
            "cost": 0.000085
        },
        "openrouter_metadata": {
            "pipeline": [
                {
                    "name": "jev-router",
                    "data": {
                        "resolved_models": ["openai/gpt-6-luna-20260922"],
                        "selected_tier_prior": "basic",
                        "candidates": [
                            {"model": "openai/gpt-6-luna-20260922", "effort": "low", "tier": "basic"}
                        ]
                    }
                }
            ]
        }
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        assert request.headers.get("X-OpenRouter-Metadata") == "enabled"
        assert "Bearer mock-openrouter-key" in request.headers.get("Authorization", "")
        return httpx.Response(200, json=mock_response_data)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenRouterJevProvider(
            api_key="mock-openrouter-key",
            model_name="typesafe/jev-router",
            client=client,
        )

        resp = await provider.generate("Explain the difference between a mutex and a semaphore.")
        assert resp.content == "A mutex is a locking mechanism, whereas a semaphore is a signaling mechanism."
        assert resp.model_name == "openai/gpt-6-luna-20260922"
        assert resp.input_tokens == 15
        assert resp.output_tokens == 40
        assert resp.cost_usd == 0.000085
        assert resp.raw_metadata["router"] == "typesafe/jev-router"
        assert resp.raw_metadata["resolved_models"] == ["openai/gpt-6-luna-20260922"]
        assert resp.raw_metadata["selected_tier"] == "basic"


@pytest.mark.asyncio
async def test_openrouter_jev_provider_with_plugin_restriction():
    captured_payload = {}

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        import json
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "anthropic/claude-3.5-sonnet",
                "choices": [{"message": {"content": "Restricted response"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "cost": 0.0001},
                "openrouter_metadata": {"pipeline": []}
            }
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenRouterJevProvider(
            api_key="mock-key",
            model_name="typesafe/jev-router",
            allowed_models=["anthropic/*", "google/*"],
            excluded_models=["anthropic/claude-opus*"],
            client=client,
        )

        resp = await provider.generate("Test prompt")
        assert resp.content == "Restricted response"
        assert "plugins" in captured_payload
        plugin = captured_payload["plugins"][0]
        assert plugin["id"] == "jev-router"
        assert plugin["models"] == ["anthropic/*", "google/*"]
        assert plugin["excluded_models"] == ["anthropic/claude-opus*"]


@pytest.mark.asyncio
async def test_openrouter_jev_provider_error_handling():
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenRouterJevProvider(
            api_key="mock-key",
            model_name="typesafe/jev-router",
            client=client,
        )

        with pytest.raises(RuntimeError) as exc_info:
            await provider.generate("Test error")
        assert "OpenRouter Jev Router API returned status 500" in str(exc_info.value)


def test_provider_registry_instantiates_openrouter_jev_provider():
    custom_settings = Settings(
        OPENROUTER_API_KEY="sk-mock-key",
        FRONTIER_MODEL_NAME="typesafe/jev-router",
        SMALL_MODEL_NAME="meta-llama/llama-3.1-8b-instruct",
    )
    with patch("backend.app.providers.registry.settings", custom_settings):
        registry = ProviderRegistry()
        assert isinstance(registry.frontier_model, OpenRouterJevProvider)
        assert registry.frontier_model.model_name == "typesafe/jev-router"
