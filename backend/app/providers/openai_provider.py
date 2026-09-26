import time
import logging
from typing import Dict, Any, Optional
import httpx

from backend.app.providers.base import ModelProvider, ProviderResponse, ProviderHealth

logger = logging.getLogger("jevflow.provider.openai")


class OpenAICompatibleProvider(ModelProvider):
    """
    Universal HTTP provider for OpenAI and OpenAI-compatible inference APIs.
    
    Supports:
      - OpenAI (gpt-4o-mini, gpt-4o)
      - Groq (llama-3.1-8b-instant, llama-3.3-70b-versatile)
      - OpenRouter (any open-source or proprietary model)
      - DeepSeek, Mistral, Together AI, Ollama (localhost:11434/v1)
    """

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str = "https://api.openai.com/v1",
        input_cost_per_million: float = 0.15,
        output_cost_per_million: float = 0.60,
        timeout_seconds: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.input_cost_per_million = input_cost_per_million
        self.output_cost_per_million = output_cost_per_million
        self.timeout_seconds = timeout_seconds
        self._injected_client = client

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        start_time = time.perf_counter()
        endpoint = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/jevflow/gateway",
            "X-Title": "JevFlow Adaptive Gateway",
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }

        try:
            if self._injected_client is not None:
                resp = await self._injected_client.post(
                    endpoint, json=payload, headers=headers, timeout=self.timeout_seconds
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.post(endpoint, json=payload, headers=headers)

            if resp.status_code != 200:
                error_body = resp.text
                logger.error("OpenAI-compatible API error (%d): %s", resp.status_code, error_body)
                raise RuntimeError(f"Provider API returned status {resp.status_code}: {error_body}")

            data = resp.json()
            choice = data["choices"][0]
            content = choice["message"]["content"]
            usage = data.get("usage", {})

            input_tokens = usage.get("prompt_tokens", max(1, len(prompt) // 4))
            output_tokens = usage.get("completion_tokens", max(1, len(content) // 4))
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            cost_usd = self.estimate_cost(input_tokens, output_tokens)

            return ProviderResponse(
                content=content,
                model_name=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=round(elapsed_ms, 2),
                cost_usd=cost_usd,
                raw_metadata={
                    "base_url": self.base_url,
                    "model": self.model_name,
                    "system_fingerprint": data.get("system_fingerprint"),
                    "is_real_api": True,
                },
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("Provider execution failed for model %s: %s", self.model_name, exc)
            raise

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1_000_000.0) * self.input_cost_per_million
        output_cost = (output_tokens / 1_000_000.0) * self.output_cost_per_million
        return round(input_cost + output_cost, 7)

    async def health(self) -> ProviderHealth:
        return ProviderHealth(status="healthy", latency_ms=0.0)

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "base_url": self.base_url,
            "input_cost_per_million": self.input_cost_per_million,
            "output_cost_per_million": self.output_cost_per_million,
            "is_real_api": True,
        }
