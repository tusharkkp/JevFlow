import pytest
import httpx
from backend.app.providers.openai_provider import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_openai_compatible_provider_success():
    """Verify OpenAICompatibleProvider parses standard chat completions response."""
    async def mock_handler(request: httpx.Request):
        assert request.url.path == "/v1/chat/completions"
        assert "Bearer test-api-key" in request.headers["Authorization"]
        return httpx.Response(
            status_code=200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Real API generated response."},
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 8,
                    "total_tokens": 20
                }
            }
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        provider = OpenAICompatibleProvider(
            api_key="test-api-key",
            model_name="gpt-4o-mini",
            base_url="https://api.openai.com/v1",
            client=mock_client,
        )

        resp = await provider.generate("Hello real model")
        assert resp.model_name == "gpt-4o-mini"
        assert resp.content == "Real API generated response."
        assert resp.input_tokens == 12
        assert resp.output_tokens == 8
        assert resp.cost_usd > 0
        assert resp.raw_metadata["is_real_api"] is not None or "base_url" in resp.raw_metadata


@pytest.mark.asyncio
async def test_openai_compatible_provider_error_handling():
    """Verify OpenAICompatibleProvider raises RuntimeError on API errors."""
    async def mock_handler(request: httpx.Request):
        return httpx.Response(status_code=401, json={"error": {"message": "Invalid API key"}})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        provider = OpenAICompatibleProvider(
            api_key="invalid-key",
            model_name="gpt-4o-mini",
            client=mock_client,
        )

        with pytest.raises(RuntimeError) as exc_info:
            await provider.generate("Test prompt")
        assert "401" in str(exc_info.value)
