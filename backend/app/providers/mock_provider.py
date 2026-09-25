import time
from typing import Dict, Any
from backend.app.providers.base import ModelProvider, ProviderResponse
from backend.app.schemas.response import RouteType


class MockModelProvider(ModelProvider):
    """
    Mock Model Provider supporting deterministic, small, and frontier routes.
    
    Provides simulated generation, token counts, and transparent cost tracking
    without consuming third-party API credits.
    """

    # Pricing per 1,000,000 tokens (USD)
    PRICING = {
        RouteType.DETERMINISTIC: {"input": 0.0, "output": 0.0, "model": "rule-engine-v1"},
        RouteType.SMALL_MODEL: {"input": 0.25, "output": 1.25, "model": "mock-small-fast-v1"},
        RouteType.FRONTIER_MODEL: {"input": 3.00, "output": 15.00, "model": "mock-frontier-large-v1"},
        RouteType.HUMAN_REVIEW: {"input": 0.0, "output": 0.0, "model": "human-review-queue"},
        RouteType.FALLBACK: {"input": 0.10, "output": 0.50, "model": "mock-fallback-v1"},
        RouteType.CACHE: {"input": 0.0, "output": 0.0, "model": "in-memory-cache"},
    }

    def __init__(self, simulated_delays_ms: Dict[RouteType, float] = None):
        self.simulated_delays_ms = simulated_delays_ms or {
            RouteType.DETERMINISTIC: 1.0,
            RouteType.SMALL_MODEL: 35.0,
            RouteType.FRONTIER_MODEL: 140.0,
            RouteType.HUMAN_REVIEW: 2.0,
            RouteType.FALLBACK: 15.0,
            RouteType.CACHE: 0.5,
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int, route: RouteType = RouteType.FRONTIER_MODEL) -> float:
        rates = self.PRICING.get(route, self.PRICING[RouteType.FRONTIER_MODEL])
        input_cost = (input_tokens / 1_000_000.0) * rates["input"]
        output_cost = (output_tokens / 1_000_000.0) * rates["output"]
        return round(input_cost + output_cost, 7)

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "provider": "MockModelProvider",
            "supported_routes": [r.value for r in self.PRICING.keys()],
            "pricing_per_1m_tokens": self.PRICING,
        }

    async def generate_for_route(self, prompt: str, route: RouteType) -> ProviderResponse:
        start_time = time.perf_counter()

        # Token count approximation (~4 chars per token)
        input_tokens = max(1, len(prompt) // 4)

        if route == RouteType.DETERMINISTIC:
            content = f"[Deterministic Rule Engine] Processed: '{prompt}'. Response generated instantly."
            output_tokens = 15
        elif route == RouteType.HUMAN_REVIEW:
            content = "[Security & Policy Review] Request queued for safety inspection. Execution paused."
            output_tokens = 12
        elif route == RouteType.FALLBACK:
            content = f"[Fallback Provider] Gracefully served response for: '{prompt[:40]}...'"
            output_tokens = 25
        elif route == RouteType.SMALL_MODEL:
            content = (
                f"[Small Model: mock-small-fast-v1] Succinct answer to: '{prompt}'. "
                "Execution finished with high efficiency and minimal latency."
            )
            output_tokens = 30
        else:  # FRONTIER_MODEL
            content = (
                f"[Frontier Model: mock-frontier-large-v1] In-depth, nuanced reasoning synthesis "
                f"for prompt: '{prompt}'. Explored underlying principles, edge cases, and architectural trade-offs."
            )
            output_tokens = 65

        # Compute cost for this specific route
        cost_usd = self.estimate_cost(input_tokens, output_tokens, route=route)

        # Baseline cost (what it would have cost on the Frontier model)
        simulated_delay = self.simulated_delays_ms.get(route, 10.0)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0 + simulated_delay

        return ProviderResponse(
            content=content,
            model_name=self.PRICING.get(route, {}).get("model", "unknown-model"),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(elapsed_ms, 2),
            cost_usd=cost_usd,
        )

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        route = kwargs.get("route", RouteType.FRONTIER_MODEL)
        return await self.generate_for_route(prompt, route)
