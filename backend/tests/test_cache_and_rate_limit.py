import pytest
from fastapi.testclient import TestClient

from backend.app.cache.key_generator import normalize_prompt, generate_cache_key
from backend.app.cache.memory_cache import MemoryCache
from backend.app.rate_limiter.token_bucket import TokenBucketRateLimiter


def test_normalize_prompt_and_key_generation():
    key1 = generate_cache_key("What is the capital of France?")
    key2 = generate_cache_key("   what is the capital of france   ")
    assert key1 == key2


@pytest.mark.asyncio
async def test_memory_cache_set_get_and_expiration():
    cache = MemoryCache()
    await cache.set("test_key", {"content": "Hello World"}, ttl_seconds=10)

    val = await cache.get("test_key")
    assert val is not None
    assert val["content"] == "Hello World"

    # Non-existent key
    assert await cache.get("missing_key") is None


def test_gateway_cache_hit_on_identical_prompt(client: TestClient):
    client.post("/v1/cache/clear")
    prompt_payload = {"prompt": "Explain photosynthesis in two sentences."}

    # 1. First request -> Cache Miss
    resp1 = client.post("/v1/chat", json=prompt_payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["telemetry"]["cache_hit"] is False
    assert data1["route"] != "cache"

    # 2. Second request with equivalent prompt -> Cache Hit!
    equivalent_prompt = {"prompt": "  explain photosynthesis in two sentences? "}
    resp2 = client.post("/v1/chat", json=equivalent_prompt)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["telemetry"]["cache_hit"] is True
    assert data2["route"] == "cache"
    assert data2["telemetry"]["estimated_cost_usd"] == 0.0
    assert data2["telemetry"]["cost_saved_usd"] > 0.0
    assert data2["telemetry"]["total_latency_ms"] < 25.0


def test_gateway_rate_limiter_rejects_exceeded_quota(client: TestClient):
    # Burst test with a unique user_id
    test_user = "test_rate_limited_user_999"

    # The burst capacity is 10. Sending 12 rapid requests must trigger 429
    got_429 = False
    for i in range(15):
        resp = client.post("/v1/chat", json={"prompt": f"Ping query #{i}", "user_id": test_user})
        if resp.status_code == 429:
            got_429 = True
            assert "Rate limit exceeded" in resp.json()["detail"]
            assert "Retry-After" in resp.headers
            break

    assert got_429 is True


def test_cache_stats_and_clear_endpoints(client: TestClient):
    stats = client.get("/v1/cache/stats")
    assert stats.status_code == 200
    assert "hits" in stats.json()

    clear = client.post("/v1/cache/clear")
    assert clear.status_code == 200
    assert clear.json()["status"] == "cleared"
