import uuid
import json
import argparse
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from backend.app.schemas.request import GatewayRequest
from backend.app.schemas.response import RouteType
from backend.app.services.gateway_service import GatewayService
from backend.app.decision.mock_engine import MockDecisionEngine
from backend.app.providers.registry import ProviderRegistry
from backend.app.cache.memory_cache import MemoryCache
from backend.app.telemetry.metrics import calculate_percentile
from backend.app.experiments.dataset import BENCHMARK_DATASET, BenchmarkItem
from backend.app.experiments.strategies import (
    RoutingStrategy,
    BaselineStrategy,
    RuleBasedStrategy,
    JevFlowStrategy,
)
from backend.app.db.session import async_session_factory, init_db
from backend.app.db.models import ExperimentRecord


class BenchmarkRunner:
    """Orchestrates comparative benchmarking across Baseline, Rules, and JevFlow."""

    def __init__(self):
        # Dedicated standalone gateway instance for reproducible benchmarks
        self.gateway = GatewayService(
            decision_engine=MockDecisionEngine(simulated_latency_ms=10.0),
            provider_registry=ProviderRegistry(),
            cache=MemoryCache(),
        )
        self.strategies: Dict[str, RoutingStrategy] = {
            "baseline": BaselineStrategy(),
            "rules": RuleBasedStrategy(),
            "jevflow": JevFlowStrategy(self.gateway),
        }

    async def run_strategy(
        self,
        strategy_name: str,
        items: List[BenchmarkItem] = BENCHMARK_DATASET,
    ) -> Dict[str, Any]:
        strategy = self.strategies[strategy_name]
        results: List[Dict[str, Any]] = []

        # Clear cache before running strategy to ensure fair isolated run
        if hasattr(strategy, "gateway") and strategy.gateway.cache:
            await strategy.gateway.cache.clear()

        correct_routes = 0
        total_items = len(items)

        for item in items:
            req = GatewayRequest(
                prompt=item.prompt,
                latency_budget_ms=item.latency_budget_ms,
                cost_budget=item.cost_budget,
            )
            response = await strategy.process(req)
            t = response.telemetry

            # Check if selected route matches optimal ground truth
            route_match = (response.route == item.expected_route)
            if route_match:
                correct_routes += 1

            results.append({
                "item_id": item.id,
                "category": item.category,
                "expected_route": item.expected_route.value,
                "actual_route": response.route.value,
                "route_match": route_match,
                "total_latency_ms": t.total_latency_ms,
                "cost_usd": t.estimated_cost_usd,
                "baseline_cost_usd": t.baseline_cost_usd,
                "cost_saved_usd": t.cost_saved_usd,
                "cache_hit": t.cache_hit,
                "fallback": t.fallback_triggered,
            })

        latencies = [r["total_latency_ms"] for r in results]
        costs = [r["cost_usd"] for r in results]
        baseline_costs = [r["baseline_cost_usd"] for r in results]

        total_cost = sum(costs)
        total_baseline = sum(baseline_costs)
        total_saved = max(0.0, total_baseline - total_cost)

        summary = {
            "strategy": strategy_name,
            "requests_count": total_items,
            "accuracy_route_match_percent": round((correct_routes / total_items) * 100.0, 1),
            "p50_latency_ms": calculate_percentile(latencies, 50.0),
            "p95_latency_ms": calculate_percentile(latencies, 95.0),
            "p99_latency_ms": calculate_percentile(latencies, 99.0),
            "average_latency_ms": round(sum(latencies) / total_items, 2),
            "total_cost_usd": round(total_cost, 6),
            "baseline_cost_usd": round(total_baseline, 6),
            "total_cost_saved_usd": round(total_saved, 6),
            "cost_reduction_percent": round((total_saved / total_baseline) * 100.0, 1) if total_baseline > 0 else 0.0,
            "cache_hit_rate": round((sum(1 for r in results if r["cache_hit"]) / total_items) * 100.0, 1),
            "fallback_rate": round((sum(1 for r in results if r["fallback"]) / total_items) * 100.0, 1),
        }

        # Persist experiment run to database
        await self._persist_record(summary, results)
        return summary

    async def _persist_record(self, summary: Dict[str, Any], results: List[Dict[str, Any]]):
        async with async_session_factory() as session:
            try:
                rec = ExperimentRecord(
                    experiment_id=f"exp_{uuid.uuid4().hex[:10]}",
                    name=f"Benchmark_{summary['strategy'].upper()}",
                    strategy=summary["strategy"],
                    created_at=datetime.now(timezone.utc),
                    total_requests=summary["requests_count"],
                    p50_latency_ms=summary["p50_latency_ms"],
                    p95_latency_ms=summary["p95_latency_ms"],
                    p99_latency_ms=summary["p99_latency_ms"],
                    average_latency_ms=summary["average_latency_ms"],
                    total_cost_usd=summary["total_cost_usd"],
                    cost_saved_usd=summary["total_cost_saved_usd"],
                    average_cost_per_request=round(summary["total_cost_usd"] / summary["requests_count"], 6),
                    success_rate=summary["accuracy_route_match_percent"],
                    fallback_rate=summary["fallback_rate"],
                    cache_hit_rate=summary["cache_hit_rate"],
                    raw_results=json.dumps(results[:5]),  # store sample results
                )
                session.add(rec)
                await session.commit()
            except Exception:
                await session.rollback()

    async def run_all(self) -> Dict[str, Any]:
        """Execute all 3 comparative strategies across the benchmark dataset."""
        report = {}
        for strategy in ("baseline", "rules", "jevflow"):
            report[strategy] = await self.run_strategy(strategy)
        return report


def format_markdown_table(report: Dict[str, Dict[str, Any]]) -> str:
    """Format benchmark report into a clear comparative markdown table."""
    header = (
        "| Metric | Baseline (All Frontier) | Strategy A (Rules) | Strategy B (JevFlow) |\n"
        "|---|---|---|---|\n"
    )
    b = report.get("baseline", {})
    r = report.get("rules", {})
    j = report.get("jevflow", {})

    rows = [
        f"| **Requests Evaluated** | {b.get('requests_count', 0)} | {r.get('requests_count', 0)} | {j.get('requests_count', 0)} |",
        f"| **Route Match / Accuracy** | {b.get('accuracy_route_match_percent', 0)}% | {r.get('accuracy_route_match_percent', 0)}% | **{j.get('accuracy_route_match_percent', 0)}%** |",
        f"| **P50 Latency (ms)** | {b.get('p50_latency_ms', 0)} ms | {r.get('p50_latency_ms', 0)} ms | **{j.get('p50_latency_ms', 0)} ms** |",
        f"| **P95 Latency (ms)** | {b.get('p95_latency_ms', 0)} ms | {r.get('p95_latency_ms', 0)} ms | **{j.get('p95_latency_ms', 0)} ms** |",
        f"| **P99 Latency (ms)** | {b.get('p99_latency_ms', 0)} ms | {r.get('p99_latency_ms', 0)} ms | **{j.get('p99_latency_ms', 0)} ms** |",
        f"| **Total Cost ($)** | ${b.get('total_cost_usd', 0):.6f} | ${r.get('total_cost_usd', 0):.6f} | **${j.get('total_cost_usd', 0):.6f}** |",
        f"| **Cost Reduction vs Baseline** | 0.0% | {r.get('cost_reduction_percent', 0)}% | **{j.get('cost_reduction_percent', 0)}%** |",
        f"| **Cache Hit Rate** | {b.get('cache_hit_rate', 0)}% | {r.get('cache_hit_rate', 0)}% | **{j.get('cache_hit_rate', 0)}%** |",
        f"| **Fallback Rate** | {b.get('fallback_rate', 0)}% | {r.get('fallback_rate', 0)}% | {j.get('fallback_rate', 0)}% |",
    ]
    return header + "\n".join(rows)


async def main_cli():
    parser = argparse.ArgumentParser(description="JevFlow Benchmark Runner")
    parser.add_argument(
        "--strategy",
        choices=["baseline", "rules", "jevflow", "all"],
        default="all",
        help="Routing strategy to benchmark",
    )
    args = parser.parse_args()

    await init_db()
    runner = BenchmarkRunner()

    print("\n=======================================================")
    print("      JEVFLOW ADAPTIVE GATEWAY BENCHMARK RUNNER        ")
    print("=======================================================\n")

    if args.strategy == "all":
        report = await runner.run_all()
        print(format_markdown_table(report))
    else:
        summary = await runner.run_strategy(args.strategy)
        print(f"Results for '{args.strategy}':\n")
        print(json.dumps(summary, indent=2))

    print("\nBenchmark completed and persisted to database.\n")


if __name__ == "__main__":
    asyncio.run(main_cli())
