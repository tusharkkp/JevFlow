import math
from typing import List, Dict, Any
from collections import Counter


def calculate_percentile(data: List[float], percentile: float) -> float:
    """
    Calculate the k-th percentile using linear interpolation.
    
    Args:
        data: List of numerical measurements.
        percentile: Float between 0.0 and 100.0.
    """
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n == 1:
        return round(sorted_data[0], 2)

    k = (percentile / 100.0) * (n - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(sorted_data[int(k)], 2)

    # Linear interpolation between adjacent ranks
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return round(d0 + d1, 2)


def compute_telemetry_aggregations(records: List[Any]) -> Dict[str, Any]:
    """
    Compute latency percentiles, cost savings, and routing distribution
    from a collection of telemetry records.
    """
    total_count = len(records)
    if total_count == 0:
        return {
            "total_requests": 0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "average_latency_ms": 0.0,
            "total_cost_usd": 0.0,
            "total_cost_saved_usd": 0.0,
            "cost_reduction_percent": 0.0,
            "cache_hit_rate_percent": 0.0,
            "fallback_rate_percent": 0.0,
            "circuit_breaker_trip_count": 0,
            "latency": {
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "avg_ms": 0.0,
                "avg_jev_ms": 0.0,
                "avg_model_ms": 0.0,
                "avg_overhead_ms": 0.0,
            },
            "cost": {
                "total_cost_usd": 0.0,
                "average_cost_usd": 0.0,
                "baseline_cost_usd": 0.0,
                "total_cost_saved_usd": 0.0,
                "cost_reduction_percent": 0.0,
            },
            "rates": {
                "fallback_rate": 0.0,
                "cache_hit_rate": 0.0,
                "circuit_tripped_rate": 0.0,
            },
            "route_distribution": {},
            "intent_distribution": {},
        }

    total_latencies = [r.total_latency_ms for r in records]
    jev_latencies = [r.jev_latency_ms for r in records]
    model_latencies = [r.model_latency_ms for r in records]
    overhead_latencies = [r.gateway_overhead_ms for r in records]

    total_cost = sum(r.estimated_cost_usd for r in records)
    total_baseline = sum(r.baseline_cost_usd for r in records)
    total_saved = sum(r.cost_saved_usd for r in records)

    fallback_count = sum(1 for r in records if r.fallback_triggered)
    cache_hit_count = sum(1 for r in records if r.cache_hit)
    cb_trips = sum(1 for r in records if r.circuit_breaker_tripped)

    route_counts = Counter(r.selected_route for r in records)
    route_dist = {
        route: {
            "count": cnt,
            "percentage": round((cnt / total_count) * 100.0, 1),
        }
        for route, cnt in route_counts.items()
    }

    intent_counts = Counter(r.intent for r in records)
    intent_dist = {
        intent: round((cnt / total_count) * 100.0, 1)
        for intent, cnt in intent_counts.items()
    }

    cost_reduction_pct = (
        round((total_saved / total_baseline) * 100.0, 1) if total_baseline > 0 else 0.0
    )

    p50 = calculate_percentile(total_latencies, 50.0)
    p95 = calculate_percentile(total_latencies, 95.0)
    p99 = calculate_percentile(total_latencies, 99.0)
    avg_latency = round(sum(total_latencies) / total_count, 2)
    tot_cost = round(total_cost, 6)
    tot_saved = round(total_saved, 6)
    cache_rate = round((cache_hit_count / total_count) * 100.0, 1)
    fallback_rate = round((fallback_count / total_count) * 100.0, 1)

    return {
        "total_requests": total_count,
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "p99_latency_ms": p99,
        "average_latency_ms": avg_latency,
        "total_cost_usd": tot_cost,
        "total_cost_saved_usd": tot_saved,
        "cost_reduction_percent": cost_reduction_pct,
        "cache_hit_rate_percent": cache_rate,
        "fallback_rate_percent": fallback_rate,
        "circuit_breaker_trip_count": cb_trips,
        "latency": {
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "avg_ms": avg_latency,
            "avg_jev_ms": round(sum(jev_latencies) / total_count, 2),
            "avg_model_ms": round(sum(model_latencies) / total_count, 2),
            "avg_overhead_ms": round(sum(overhead_latencies) / total_count, 2),
        },
        "cost": {
            "total_cost_usd": tot_cost,
            "average_cost_usd": round(total_cost / total_count, 6),
            "baseline_cost_usd": round(total_baseline, 6),
            "total_cost_saved_usd": tot_saved,
            "cost_reduction_percent": cost_reduction_pct,
        },
        "rates": {
            "fallback_rate": fallback_rate,
            "cache_hit_rate": cache_rate,
            "circuit_tripped_rate": round((cb_trips / total_count) * 100.0, 1),
        },
        "route_distribution": route_dist,
        "intent_distribution": intent_dist,
    }
