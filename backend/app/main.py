from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, Request, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.schemas.request import GatewayRequest
from backend.app.schemas.response import GatewayResponse
from backend.app.services.gateway_service import GatewayService
from backend.app.decision.jev_engine import TypeSafeJevEngine
from backend.app.providers.registry import ProviderRegistry
from backend.app.cache.memory_cache import MemoryCache
from backend.app.rate_limiter.token_bucket import TokenBucketRateLimiter
from backend.app.db.session import init_db
from backend.app.telemetry.repository import TelemetryRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.7.0",
    description="Adaptive AI Gateway powered by System One Probabilistic Decisions, Deterministic Policy, and Telemetry.",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared singletons
provider_registry = ProviderRegistry()
gateway_cache = MemoryCache(max_entries=5000)
rate_limiter = TokenBucketRateLimiter(requests_per_minute=60, burst_capacity=10)
telemetry_repo = TelemetryRepository()


def get_gateway_service() -> GatewayService:
    decision_engine = TypeSafeJevEngine()
    return GatewayService(
        decision_engine=decision_engine,
        provider_registry=provider_registry,
        cache=gateway_cache,
        telemetry_repo=telemetry_repo,
    )


async def enforce_rate_limit(client_id: str):
    allowed, retry_after, remaining = await rate_limiter.check_rate_limit(client_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please retry after {retry_after} seconds.",
            headers={"Retry-After": str(max(1, int(retry_after)))},
        )


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": "0.7.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
async def health():
    provider_health = await provider_registry.check_all_health()
    cache_health = await gateway_cache.health()
    rate_limiter_stats = await rate_limiter.get_stats()
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "providers": {k: v.model_dump() for k, v in provider_health.items()},
        "cache": cache_health,
        "rate_limiter": rate_limiter_stats,
    }


@app.get("/v1/providers", tags=["Providers"])
async def list_providers():
    return provider_registry.get_all_metadata()


@app.get("/v1/cache/stats", tags=["Cache"])
async def cache_stats():
    return await gateway_cache.health()


@app.post("/v1/cache/clear", tags=["Cache"])
async def cache_clear():
    await gateway_cache.clear()
    return {"status": "cleared"}


@app.get("/v1/rate-limit/stats", tags=["Rate Limiting"])
async def rate_limit_stats():
    return await rate_limiter.get_stats()


# ----------------------------------------------------------------------
# Telemetry & Observability Endpoints
# ----------------------------------------------------------------------
@app.get("/v1/telemetry/summary", tags=["Telemetry"])
async def get_telemetry_summary():
    """Retrieve aggregate telemetry metrics (P50/P95/P99 latency, cost savings, route distributions)."""
    return await telemetry_repo.get_summary_metrics()


@app.get("/v1/telemetry/requests", tags=["Telemetry"])
async def list_telemetry_requests(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    route: Optional[str] = Query(None, description="Filter by route: deterministic, small_model, frontier_model, cache, etc."),
):
    """List recent persistent request traces with pagination."""
    return await telemetry_repo.list_traces(limit=limit, offset=offset, route=route)


@app.get("/v1/telemetry/requests/{request_id}", tags=["Telemetry"])
async def get_telemetry_request_detail(request_id: str):
    """Retrieve detailed waterfall latency breakdown and economics for a specific request."""
    trace = await telemetry_repo.get_trace(request_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Request trace '{request_id}' not found.")
    return trace


@app.post(
    "/v1/chat",
    response_model=GatewayResponse,
    status_code=status.HTTP_200_OK,
    tags=["Gateway"],
    summary="Process prompt through Adaptive AI Gateway",
    description=(
        "Checks cache, evaluates prompt via System One decision layer, applies deterministic policy, "
        "routes to the optimal execution provider, and emits complete telemetry."
    )
)
async def process_chat_request(
    request: GatewayRequest,
    http_req: Request,
    service: GatewayService = Depends(get_gateway_service),
) -> GatewayResponse:
    client_id = request.user_id or (http_req.client.host if http_req.client else "unknown_client")
    await enforce_rate_limit(client_id)
    return await service.process_request(request)
