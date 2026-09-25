from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ProviderResponse(BaseModel):
    """Response payload returned by any underlying execution model provider."""
    content: str
    model_name: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float = Field(default=0.0)
    cached: bool = Field(default=False)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class ProviderHealth(BaseModel):
    """Health and availability status of a model provider."""
    status: str = Field(..., description="'healthy', 'degraded', or 'unavailable'")
    latency_ms: Optional[float] = None
    last_checked: Optional[str] = None
    error: Optional[str] = None


class ModelProvider(ABC):
    """
    Abstract interface decoupling the gateway from specific model vendors.
    
    Any backend LLM or execution engine (OpenAI, Anthropic, local Llama,
    rule engine, or mock) must implement this interface.
    """

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Execute prompt generation against the model."""
        pass

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost in USD based on input and output token counts."""
        pass

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """Check operational health and availability of the provider."""
        pass

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Provider metadata (model name, tier, pricing per million tokens)."""
        pass
