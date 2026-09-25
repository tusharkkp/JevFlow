import time
from typing import Dict, Any
from backend.app.providers.base import ModelProvider, ProviderResponse, ProviderHealth


class HumanReviewProvider(ModelProvider):
    """
    Safety gate provider for prompts flagged by System One safety checks.
    
    Generates a human-in-the-loop review ticket instead of executing
    potentially malicious or high-risk prompts against automated models.
    """

    MODEL_NAME = "security-review-queue"

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        start_time = time.perf_counter()

        content = (
            "[Security & Policy Gate] Request flagged by safety classifier. "
            "Execution has been paused and assigned to the review queue for human operator sign-off."
        )

        input_tokens = max(1, len(prompt) // 4)
        output_tokens = max(1, len(content) // 4)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return ProviderResponse(
            content=content,
            model_name=self.MODEL_NAME,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(elapsed_ms, 2),
            cost_usd=0.0,
            raw_metadata={"tier": "human_review", "action_taken": "quarantined"}
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0

    async def health(self) -> ProviderHealth:
        return ProviderHealth(status="healthy", latency_ms=0.5)

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "model_name": self.MODEL_NAME,
            "tier": "human_review",
            "cost_per_million_input": 0.0,
            "cost_per_million_output": 0.0,
            "typical_latency_ms": 1.0,
        }
