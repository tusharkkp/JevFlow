from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel, Field


class ProviderResponse(BaseModel):
    """Response payload returned by any underlying execution model provider."""
    content: str
    model_name: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float = Field(default=0.0)


class ModelProvider(ABC):
    """Abstract interface decoupling the gateway from specific model vendors."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Execute prompt generation against the model."""
        pass

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost in USD based on input and output token counts."""
        pass

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Provider metadata (model name, tier, pricing per million tokens)."""
        pass
