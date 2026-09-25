from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class GatewayRequest(BaseModel):
    """Client request schema entering the JevFlow Gateway."""
    prompt: str = Field(
        ...,
        description="The user prompt or query to be evaluated and answered.",
        min_length=1,
        examples=["Explain Dijkstra's algorithm in Python with code examples."]
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional client/user identifier for rate limiting or session tracking.",
        examples=["user_123"]
    )
    latency_budget_ms: Optional[int] = Field(
        default=None,
        description="Optional strict latency budget constraint in milliseconds.",
        ge=50,
        examples=[1000]
    )
    cost_budget: Optional[float] = Field(
        default=None,
        description="Optional maximum cost budget constraint for this request in USD.",
        ge=0.0,
        examples=[0.01]
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional arbitrary metadata passed through for tracing or routing context."
    )
