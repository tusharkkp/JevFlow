import time
import logging
from typing import Dict, Any, Optional, List
import httpx

from backend.app.providers.base import ModelProvider, ProviderResponse, ProviderHealth
from backend.app.core.config import settings

logger = logging.getLogger("jevflow.provider.openrouter_jev")


class OpenRouterJevProvider(ModelProvider):
    """
    OpenRouter Model Provider using TypeSafe's Jev Router (`typesafe/jev-router`).
    
    As documented by OpenRouter:
      - Model: 'typesafe/jev-router'
      - Automatically picks the model and reasoning effort from OpenRouter's curated model pool.
      - Supports optional candidate model restriction via the 'jev-router' plugin:
          plugins: [{"id": "jev-router", "models": [...], "excluded_models": [...]}]
      - Sends header 'X-OpenRouter-Metadata: enabled' to receive router pipeline metadata
        (resolved_models, candidate tiers, and routing rationale).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "typesafe/jev-router",
        base_url: Optional[str] = None,
        allowed_models: Optional[List[str]] = None,
        excluded_models: Optional[List[str]] = None,
        timeout_seconds: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key or settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        self.model_name = model_name or "typesafe/jev-router"
        self.base_url = (base_url or settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1").rstrip("/")
        self.allowed_models = allowed_models
        self.excluded_models = excluded_models
        self.timeout_seconds = timeout_seconds
        self._injected_client = client

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        start_time = time.perf_counter()
        endpoint = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Metadata": "enabled",
            "HTTP-Referer": "https://github.com/tusharkkp/JevFlow",
            "X-Title": "JevFlow Gateway",
        }

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }

        # Restrict candidate models if plugin config is provided
        if self.allowed_models or self.excluded_models:
            plugin_def: Dict[str, Any] = {"id": "jev-router"}
            if self.allowed_models:
                plugin_def["models"] = self.allowed_models
            if self.excluded_models:
                plugin_def["excluded_models"] = self.excluded_models
            payload["plugins"] = [plugin_def]

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
                logger.error("OpenRouter Jev Router returned status %d: %s", resp.status_code, error_body)
                raise RuntimeError(f"OpenRouter Jev Router API returned status {resp.status_code}: {error_body}")

            data = resp.json()
            choice = data["choices"][0]
            message = choice.get("message", {})
            content = message.get("content") or message.get("reasoning") or ""
            usage = data.get("usage", {})
            served_model = data.get("model", self.model_name)

            # Extract Jev router metadata from openrouter_metadata pipeline
            openrouter_metadata = data.get("openrouter_metadata", {})
            pipeline = openrouter_metadata.get("pipeline", [])
            jev_stage = next((stage.get("data", {}) for stage in pipeline if stage.get("name") == "jev-router"), {})

            resolved_models = jev_stage.get("resolved_models", [served_model])
            candidates = jev_stage.get("candidates", [])
            selected_tier = jev_stage.get("selected_tier_prior") or jev_stage.get("floor")

            input_tokens = usage.get("prompt_tokens") or max(1, len(prompt) // 4)
            output_tokens = usage.get("completion_tokens") or max(1, len(content) // 4)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # OpenRouter provides explicit cost in usage.cost or total_cost
            cost_usd = float(usage.get("cost", 0.0))
            if cost_usd == 0.0:
                # Fallback estimation based on typical blended rates
                cost_usd = round((input_tokens * 1.0 + output_tokens * 3.0) / 1_000_000.0, 7)

            return ProviderResponse(
                content=content,
                model_name=served_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=round(elapsed_ms, 2),
                cost_usd=cost_usd,
                raw_metadata={
                    "router": "typesafe/jev-router",
                    "served_model": served_model,
                    "resolved_models": resolved_models,
                    "selected_tier": selected_tier,
                    "candidates": candidates,
                    "openrouter_metadata": openrouter_metadata,
                    "system_fingerprint": data.get("system_fingerprint"),
                    "is_real_api": True,
                },
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("OpenRouter Jev Router execution failed: %s", exc)
            raise

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate blended cost in USD based on typical OpenRouter candidate model rates."""
        # Average rate ~$0.50 / M input, $1.50 / M output
        input_cost = (input_tokens / 1_000_000.0) * 0.50
        output_cost = (output_tokens / 1_000_000.0) * 1.50
        return round(input_cost + output_cost, 7)

    async def health(self) -> ProviderHealth:
        return ProviderHealth(status="healthy", latency_ms=0.0)

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "base_url": self.base_url,
            "router": "typesafe/jev-router",
            "allowed_models": self.allowed_models,
            "excluded_models": self.excluded_models,
            "is_real_api": True,
        }
