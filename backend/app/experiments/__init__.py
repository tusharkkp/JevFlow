"""Evaluation & Benchmarking Engine for JevFlow.

Compares Baseline (100% Frontier), Rule-based, and JevFlow Adaptive Routing
across a curated benchmark dataset of multi-archetype prompts.
"""

from backend.app.experiments.dataset import (
    BENCHMARK_DATASET,
    BenchmarkItem,
    RequestCategory,
)
from backend.app.experiments.strategies import (
    RoutingStrategy,
    BaselineStrategy,
    RuleBasedStrategy,
    JevFlowStrategy,
)
from backend.app.experiments.runner import BenchmarkRunner, format_markdown_table

__all__ = [
    "BENCHMARK_DATASET",
    "BenchmarkItem",
    "RequestCategory",
    "RoutingStrategy",
    "BaselineStrategy",
    "RuleBasedStrategy",
    "JevFlowStrategy",
    "BenchmarkRunner",
    "format_markdown_table",
]
