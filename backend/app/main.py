from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.schemas.request import GatewayRequest
from backend.app.schemas.response import GatewayResponse
from backend.app.services.gateway_service import GatewayService

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Adaptive AI Gateway powered by System One Probabilistic Decisions and Deterministic Policy.",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Enable CORS for future frontend dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency Injection for GatewayService
def get_gateway_service() -> GatewayService:
    return GatewayService()


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }


@app.post(
    "/v1/chat",
    response_model=GatewayResponse,
    status_code=status.HTTP_200_OK,
    tags=["Gateway"],
    summary="Process prompt through Adaptive AI Gateway",
    description=(
        "Evaluates the prompt via System One decision layer, applies deterministic policy, "
        "routes to the optimal execution provider, and emits complete telemetry."
    )
)
async def process_chat_request(
    request: GatewayRequest,
    service: GatewayService = Depends(get_gateway_service),
) -> GatewayResponse:
    return await service.process_request(request)
