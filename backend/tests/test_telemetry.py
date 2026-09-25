import pytest
from fastapi.testclient import TestClient

from backend.app.telemetry.metrics import calculate_percentile, compute_telemetry_aggregations
from backend.app.schemas.response import TelemetryTrace, RouteType


def test_percentile_calculation():
    data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    p50 = calculate_percentile(data, 50.0)
    p95 = calculate_percentile(data, 95.0)
    assert p50 == 55.0
    assert p95 == 95.5


def test_telemetry_aggregations_empty():
    summary = compute_telemetry_aggregations([])
    assert summary["total_requests"] == 0
    assert summary["latency"]["p50_ms"] == 0.0


def test_telemetry_persistence_and_endpoints(client: TestClient):
    # 1. Send two distinct requests to generate real persisted telemetry
    resp1 = client.post("/v1/chat", json={"prompt": "Explain merge sort in Python."})
    assert resp1.status_code == 200
    req_id1 = resp1.json()["request_id"]

    resp2 = client.post("/v1/chat", json={"prompt": "Hi there!"})
    assert resp2.status_code == 200
    req_id2 = resp2.json()["request_id"]

    # 2. Query telemetry summary
    summary_resp = client.get("/v1/telemetry/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total_requests"] >= 2
    assert "latency" in summary
    assert "p50_ms" in summary["latency"]
    assert "cost" in summary
    assert "total_cost_saved_usd" in summary["cost"]
    assert "route_distribution" in summary

    # 3. Query telemetry request list
    list_resp = client.get("/v1/telemetry/requests?limit=10")
    assert list_resp.status_code == 200
    traces = list_resp.json()
    assert len(traces) >= 2
    request_ids = [t["request_id"] for t in traces]
    assert req_id1 in request_ids
    assert req_id2 in request_ids

    # 4. Query single request detail waterfall
    detail_resp = client.get(f"/v1/telemetry/requests/{req_id1}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["request_id"] == req_id1
    assert "waterfall" in detail
    assert "jev_decision_ms" in detail["waterfall"]
    assert "model_execution_ms" in detail["waterfall"]
    assert "gateway_overhead_ms" in detail["waterfall"]
    assert "economics" in detail
    assert detail["economics"]["baseline_cost_usd"] > 0.0

    # 5. Non-existent ID returns 404
    missing_resp = client.get("/v1/telemetry/requests/non_existent_req_id_9999")
    assert missing_resp.status_code == 404
