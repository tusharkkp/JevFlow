# JevFlow Experiments & Benchmarking Guide

## 1. Running Benchmarks via CLI

You can execute comparative benchmarks directly from the command line using the Python benchmark module:

```powershell
# Set PYTHONPATH to project root
$env:PYTHONPATH="."

# Run all 3 strategies and print formatted comparison table
.venv\Scripts\python -m backend.app.experiments.runner --strategy all

# Run a single strategy
.venv\Scripts\python -m backend.app.experiments.runner --strategy jevflow
.venv\Scripts\python -m backend.app.experiments.runner --strategy rules
.venv\Scripts\python -m backend.app.experiments.runner --strategy baseline
```

All benchmark runs are automatically committed to the database table `experiments`.

---

## 2. Running Benchmarks via HTTP API

### Execute Benchmark
```http
POST /v1/experiments/run?strategy=all
Content-Type: application/json
```

**Response (Summary per Strategy):**
```json
{
  "baseline": {
    "strategy": "baseline",
    "requests_count": 12,
    "accuracy_route_match_percent": 33.3,
    "p50_latency_ms": 141.79,
    "p95_latency_ms": 154.94,
    "p99_latency_ms": 155.17,
    "average_latency_ms": 140.25,
    "total_cost_usd": 0.011241,
    "baseline_cost_usd": 0.011241,
    "total_cost_saved_usd": 0.0,
    "cost_reduction_percent": 0.0,
    "cache_hit_rate": 0.0,
    "fallback_rate": 0.0
  },
  "rules": { ... },
  "jevflow": {
    "strategy": "jevflow",
    "requests_count": 12,
    "accuracy_route_match_percent": 83.3,
    "p50_latency_ms": 64.06,
    "p95_latency_ms": 165.4,
    "p99_latency_ms": 168.76,
    "average_latency_ms": 78.42,
    "total_cost_usd": 0.002665,
    "baseline_cost_usd": 0.011241,
    "total_cost_saved_usd": 0.008576,
    "cost_reduction_percent": 66.3,
    "cache_hit_rate": 8.3,
    "fallback_rate": 0.0
  }
}
```

### Retrieve Past Experiment Runs
```http
GET /v1/experiments?limit=20&offset=0
```

---

## 3. Extending the Benchmark Dataset

To add new queries to the benchmark suite, edit `backend/app/experiments/dataset.py`:

```python
BenchmarkItem(
    id="custom_01",
    prompt="Explain CAP theorem tradeoffs in distributed systems.",
    category=RequestCategory.REASONING.value,
    expected_route=RouteType.FRONTIER_MODEL,
    expected_intent="reasoning",
    description="Distributed systems theoretical explanation."
)
```

Ensure all newly added items provide an `expected_route` so the route matching accuracy metric continues to evaluate ground truth alignment correctly.
