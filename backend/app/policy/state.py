from typing import Dict, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.response import RouteType


class SystemState(BaseModel):
    """
    Runtime telemetry and system conditions used for adaptive routing decisions.
    
    Rather than static request-to-model mapping, the gateway evaluates:
    Request + System State -> Decision -> Optimal Route
    """
    active_requests: int = Field(default=0, ge=0, description="Current concurrent requests in-flight")
    max_concurrency: int = Field(default=100, gt=0, description="Max configured gateway concurrency")
    provider_status: Dict[str, str] = Field(
        default_factory=lambda: {
            RouteType.DETERMINISTIC.value: "healthy",
            RouteType.SMALL_MODEL.value: "healthy",
            RouteType.FRONTIER_MODEL.value: "healthy",
            RouteType.HUMAN_REVIEW.value: "healthy",
        },
        description="Health status per provider: 'healthy', 'degraded', 'unavailable'"
    )
    provider_latencies_ms: Dict[str, float] = Field(
        default_factory=lambda: {
            RouteType.DETERMINISTIC.value: 1.0,
            RouteType.SMALL_MODEL.value: 35.0,
            RouteType.FRONTIER_MODEL.value: 140.0,
        },
        description="Observed average / P50 latency per route"
    )
    cache_available: bool = Field(default=False, description="Whether Redis/cache layer is available")

    @property
    def load_ratio(self) -> float:
        """Calculate system load ratio (0.0 to 1.0+)."""
        return min(1.0, self.active_requests / float(self.max_concurrency))

    def is_provider_available(self, route: RouteType) -> bool:
        """Check if provider for this route is healthy or degraded (not unavailable)."""
        status = self.provider_status.get(route.value, "healthy")
        return status != "unavailable"
