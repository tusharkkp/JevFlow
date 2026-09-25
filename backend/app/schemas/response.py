from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class RouteType(str, Enum):
    DETERMINISTIC = "deterministic"
    CACHE = "cache"
    SMALL_MODEL = "small_model"
    FRONTIER_MODEL = "frontier_model"
    HUMAN_REVIEW = "human_review"
    FALLBACK = "fallback"


class TelemetryTrace(BaseModel):
    """Fine-grained telemetry and cost-accounting trace for every gateway request."""
    request_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    intent: str
    complexity_score: float
    jev_confidence: float
    selected_route: RouteType
    policy_reason: str
    actual_model: str
    cache_hit: bool = False
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None
    jev_latency_ms: float
    model_latency_ms: float
    gateway_overhead_ms: float
    total_latency_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    baseline_cost_usd: float
    cost_saved_usd: float


class GatewayResponse(BaseModel):
    """Unified client response containing generation payload and observability metadata."""
    request_id: str
    content: str
    route: RouteType
    model: str
    telemetry: TelemetryTrace
