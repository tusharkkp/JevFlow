import time
import asyncio
from typing import Dict, Any, Optional
from backend.app.providers.base import ModelProvider, ProviderResponse, ProviderHealth


class SmallModelProvider(ModelProvider):
    """
    Fast and cost-efficient execution provider.
    
    Represents lightweight models (such as Claude 3.5 Haiku, GPT-4o-mini, or Llama 3.2 3B).
    Provides rapid responses for moderate complexity tasks at minimal token cost.
    """

    MODEL_NAME = "small-fast-v1"
    INPUT_COST_PER_MILLION = 0.25
    OUTPUT_COST_PER_MILLION = 1.25

    def __init__(self, simulated_latency_ms: float = 35.0):
        self.simulated_latency_ms = simulated_latency_ms

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        start_time = time.perf_counter()

        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        # Realistic generation synthesis for small models
        content = (
            f"[Small Fast Model] Direct response to: '{prompt}'. "
            "Executed with low latency and optimal token efficiency."
        )

        input_tokens = max(1, len(prompt) // 4)
        output_tokens = max(1, len(content) // 4)
        cost_usd = self.estimate_cost(input_tokens, output_tokens)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return ProviderResponse(
            content=content,
            model_name=self.MODEL_NAME,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(elapsed_ms, 2),
            cost_usd=cost_usd,
            raw_metadata={"tier": "small_model", "vendor_equivalent": "claude-3-5-haiku / gpt-4o-mini"}
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1_000_000.0) * self.INPUT_COST_PER_MILLION
        output_cost = (output_tokens / 1_000_000.0) * self.OUTPUT_COST_PER_MILLION
        return round(input_cost + output_cost, 7)

    async def health(self) -> ProviderHealth:
        return ProviderHealth(status="healthy", latency_ms=self.simulated_latency_ms)

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "model_name": self.MODEL_NAME,
            "tier": "small_model",
            "cost_per_million_input": self.INPUT_COST_PER_MILLION,
            "cost_per_million_output": self.OUTPUT_COST_PER_MILLION,
            "typical_latency_ms": self.simulated_latency_ms,
        }
