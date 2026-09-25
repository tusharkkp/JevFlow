import pytest
from fastapi.testclient import TestClient

from backend.app.schemas.response import RouteType
from backend.app.providers.deterministic_provider import DeterministicProvider
from backend.app.providers.small_model_provider import SmallModelProvider
from backend.app.providers.frontier_model_provider import FrontierModelProvider
from backend.app.providers.human_review_provider import HumanReviewProvider
from backend.app.providers.registry import ProviderRegistry
from backend.app.providers.base import ModelProvider, ProviderResponse, ProviderHealth


@pytest.mark.asyncio
async def test_deterministic_provider():
    provider = DeterministicProvider()
    resp = await provider.generate("hello")
    assert "Hello!" in resp.content
    assert resp.cost_usd == 0.0
    assert resp.model_name == "deterministic-rule-v1"
    assert provider.estimate_cost(100, 100) == 0.0
    health = await provider.health()
    assert health.status == "healthy"


@pytest.mark.asyncio
async def test_small_model_provider_cost_and_generation():
    provider = SmallModelProvider(simulated_latency_ms=0.0)
    resp = await provider.generate("What is 2 + 2?")
    assert "small-fast-v1" in resp.model_name
    assert resp.cost_usd > 0.0
    # 1,000,000 input tokens = $0.25, 1,000,000 output tokens = $1.25 -> total $1.50
    assert provider.estimate_cost(1_000_000, 1_000_000) == 1.50
    health = await provider.health()
    assert health.status == "healthy"


@pytest.mark.asyncio
async def test_frontier_model_provider_cost_and_generation():
    provider = FrontierModelProvider(simulated_latency_ms=0.0)
    resp = await provider.generate("Design a distributed consensus protocol")
    assert "frontier-reasoning-v1" in resp.model_name
    assert resp.cost_usd > 0.0
    # 1M in ($3.00) + 1M out ($15.00) -> $18.00
    assert provider.estimate_cost(1_000_000, 1_000_000) == 18.00


@pytest.mark.asyncio
async def test_human_review_provider():
    provider = HumanReviewProvider()
    resp = await provider.generate("malicious prompt")
    assert "Security & Policy Gate" in resp.content
    assert resp.cost_usd == 0.0
    assert resp.model_name == "security-review-queue"


@pytest.mark.asyncio
async def test_provider_registry_routing():
    registry = ProviderRegistry()
    resp, fallback, reason, retries, cb_tripped, err_cat = await registry.execute_route(RouteType.SMALL_MODEL, "test prompt")
    assert resp.model_name == "small-fast-v1"
    assert not fallback
    assert reason is None


class FailingProvider(ModelProvider):
    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        raise ConnectionResetError("Remote model provider disconnected")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0

    async def health(self) -> ProviderHealth:
        return ProviderHealth(status="unavailable", error="disconnected")

    @property
    def metadata(self):
        return {"model_name": "failing-provider"}


@pytest.mark.asyncio
async def test_provider_registry_failover_on_error():
    failing_frontier = FailingProvider()
    registry = ProviderRegistry(frontier_model_provider=failing_frontier)

    # When FRONTIER_MODEL fails, it should failover to small_model
    resp, fallback, reason, retries, cb_tripped, err_cat = await registry.execute_route(RouteType.FRONTIER_MODEL, "Solve complex logic")
    assert fallback is True
    assert "provider_failure" in reason
    assert resp.model_name == "small-fast-v1"


def test_list_providers_endpoint(client: TestClient):
    response = client.get("/v1/providers")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert "small_model" in data["providers"]
    assert "frontier_model" in data["providers"]
    assert "deterministic" in data["providers"]
