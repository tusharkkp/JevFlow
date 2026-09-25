import time
from typing import Dict, Any
from backend.app.providers.base import ModelProvider, ProviderResponse, ProviderHealth


class DeterministicProvider(ModelProvider):
    """
    Zero-cost deterministic execution provider.
    
    Handles simple, static queries (greetings, definitions, trivial lookups)
    with sub-millisecond latency and $0.00 external API spend.
    """

    MODEL_NAME = "deterministic-rule-v1"

    # Static instant knowledge base
    RESPONSES = {
        "hello": "Hello! How can I assist you today?",
        "hi": "Hi there! What can I help you with?",
        "hey": "Hey! What would you like to explore today?",
        "ping": "pong",
        "help": "JevFlow Gateway: Adaptive routing powered by System One decisions.",
    }

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        start_time = time.perf_counter()
        lowered = prompt.lower().strip().rstrip("!?.,")

        content = self.RESPONSES.get(
            lowered,
            f"[Deterministic Engine] Answered request '{prompt}' using rule-based pattern matching."
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
            raw_metadata={"tier": "deterministic", "rule_matched": lowered in self.RESPONSES}
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0

    async def health(self) -> ProviderHealth:
        return ProviderHealth(status="healthy", latency_ms=0.1)

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "model_name": self.MODEL_NAME,
            "tier": "deterministic",
            "cost_per_million_input": 0.0,
            "cost_per_million_output": 0.0,
            "typical_latency_ms": 1.0,
        }
