import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.schemas.response import RouteType
from backend.app.schemas.request import GatewayRequest
from backend.app.experiments.dataset import BENCHMARK_DATASET, BenchmarkItem, RequestCategory
from backend.app.experiments.strategies import (
    BaselineStrategy,
    RuleBasedStrategy,
    JevFlowStrategy,
)
from backend.app.experiments.runner import BenchmarkRunner, format_markdown_table
from backend.app.services.gateway_service import GatewayService
from backend.app.decision.mock_engine import MockDecisionEngine
from backend.app.providers.registry import ProviderRegistry
from backend.app.cache.memory_cache import MemoryCache


def test_benchmark_dataset_integrity():
    """Verify benchmark dataset contains diverse archetypes with valid configurations."""
    assert len(BENCHMARK_DATASET) >= 12
    categories = {item.category for item in BENCHMARK_DATASET}
    assert RequestCategory.FACTUAL_QUESTION.value in categories
    assert RequestCategory.CODING.value in categories
    assert RequestCategory.REASONING.value in categories
    assert RequestCategory.SUMMARIZATION.value in categories
    assert RequestCategory.OTHER.value in categories

    for item in BENCHMARK_DATASET:
        assert item.id.startswith(("fact_", "code_", "reason_", "summ_", "ambig_", "sec_", "cache_"))
        assert len(item.prompt.strip()) > 0
        assert item.expected_route in RouteType


@pytest.mark.asyncio
async def test_baseline_strategy():
    """Verify Baseline strategy sends 100% of requests to Frontier Model."""
    strategy = BaselineStrategy()
    req = GatewayRequest(prompt="What is 2+2?")
    res = await strategy.process(req)
    assert res.route == RouteType.FRONTIER_MODEL
    assert res.model == "frontier-reasoning-v1"
    assert res.telemetry.estimated_cost_usd > 0
    assert res.telemetry.cost_saved_usd == 0.0


@pytest.mark.asyncio
async def test_rule_based_strategy():
    """Verify Rule-Based strategy applies regex/length heuristics."""
    strategy = RuleBasedStrategy()

    # Trivial / short
    res_trivial = await strategy.process(GatewayRequest(prompt="ping"))
    assert res_trivial.route == RouteType.DETERMINISTIC

    # Reasoning keyword ('why', 'compare') -> Frontier
    res_frontier = await strategy.process(GatewayRequest(prompt="Why did the Roman empire collapse?"))
    assert res_frontier.route == RouteType.FRONTIER_MODEL

    # General / code without reasoning keyword -> Small Model
    res_small = await strategy.process(GatewayRequest(prompt="Summarize this brief paragraph"))
    assert res_small.route == RouteType.SMALL_MODEL


@pytest.mark.asyncio
async def test_jevflow_strategy_adaptive_routing():
    """Verify JevFlow strategy passes through full decision + policy pipeline."""
    gateway = GatewayService(
        decision_engine=MockDecisionEngine(simulated_latency_ms=1.0),
        provider_registry=ProviderRegistry(),
        cache=MemoryCache(),
    )
    strategy = JevFlowStrategy(gateway)

    # Simple factual prompt -> small_model or deterministic
    req = GatewayRequest(prompt="What is the capital of France?")
    res = await strategy.process(req)
    assert res.route in (RouteType.SMALL_MODEL, RouteType.DETERMINISTIC)
    assert res.telemetry.baseline_cost_usd > 0


@pytest.mark.asyncio
async def test_benchmark_runner_and_table_formatter():
    """Verify BenchmarkRunner executes across strategies and formats markdown table."""
    runner = BenchmarkRunner()

    # Run on a tiny subset of 3 items for speed
    test_subset = BENCHMARK_DATASET[:3]
    baseline_summary = await runner.run_strategy("baseline", items=test_subset)
    assert baseline_summary["requests_count"] == 3
    assert baseline_summary["cost_reduction_percent"] == 0.0

    rules_summary = await runner.run_strategy("rules", items=test_subset)
    assert rules_summary["requests_count"] == 3

    jevflow_summary = await runner.run_strategy("jevflow", items=test_subset)
    assert jevflow_summary["requests_count"] == 3

    # Test Markdown formatting
    report = {
        "baseline": baseline_summary,
        "rules": rules_summary,
        "jevflow": jevflow_summary,
    }
    table = format_markdown_table(report)
    assert "| Metric | Baseline (All Frontier) | Strategy A (Rules) | Strategy B (JevFlow) |" in table
    assert "| **Route Match / Accuracy** |" in table
    assert "| **Cost Reduction vs Baseline** |" in table


@pytest.mark.asyncio
async def test_experiments_api_endpoints():
    """Verify POST /v1/experiments/run and GET /v1/experiments API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Run single strategy benchmark via API
        run_res = await client.post("/v1/experiments/run?strategy=rules")
        assert run_res.status_code == 200
        run_data = run_res.json()
        assert run_data["strategy"] == "rules"
        assert run_data["requests_count"] >= 12
        assert "p50_latency_ms" in run_data
        assert "cost_reduction_percent" in run_data

        # List experiment runs
        list_res = await client.get("/v1/experiments")
        assert list_res.status_code == 200
        experiments = list_res.json()
        assert isinstance(experiments, list)
        assert len(experiments) >= 1
        assert experiments[0]["strategy"] == "rules"
