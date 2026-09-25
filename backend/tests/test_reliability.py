import asyncio
import time
import pytest
import httpx

from backend.app.reliability.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerOpenException,
)
from backend.app.reliability.retry import retry_with_backoff
from backend.app.decision.jev_engine import TypeSafeJevEngine
from backend.app.jev.client import TypeSafeJevClient
from backend.app.providers.registry import ProviderRegistry
from backend.app.providers.base import ModelProvider, ProviderResponse, ProviderHealth
from backend.app.schemas.response import RouteType


@pytest.mark.asyncio
async def test_circuit_breaker_closed_to_open_transition():
    cb = CircuitBreaker("test_cb", failure_threshold=2, recovery_timeout_sec=0.1)
    assert cb.state == CircuitBreakerState.CLOSED

    async def faulty_call():
        raise ValueError("Simulated provider outage")

    # First failure
    with pytest.raises(ValueError):
        await cb.call(faulty_call)
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 1

    # Second failure -> Should trip to OPEN
    with pytest.raises(ValueError):
        await cb.call(faulty_call)
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.failure_count == 2

    # Third attempt while OPEN -> Should fail-fast with CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        await cb.call(faulty_call)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    cb = CircuitBreaker("recovery_cb", failure_threshold=1, recovery_timeout_sec=0.05)

    async def fail():
        raise RuntimeError("Failure")

    async def succeed():
        return "OK"

    # Trip to OPEN
    with pytest.raises(RuntimeError):
        await cb.call(fail)
    assert cb.state == CircuitBreakerState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(0.06)

    # Next call should be in HALF_OPEN and succeed -> transitions to CLOSED
    result = await cb.call(succeed)
    assert result == "OK"
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0


@pytest.mark.asyncio
async def test_retry_with_backoff_success_on_transient_error():
    attempts = 0

    async def transient_operation():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionError("Temporary connection drop")
        return "success"

    result, retries = await retry_with_backoff(
        transient_operation,
        max_retries=2,
        base_delay_ms=10.0,
        retryable_exceptions=(ConnectionError,),
    )
    assert result == "success"
    assert retries == 1
    assert attempts == 2


@pytest.mark.asyncio
async def test_retry_with_backoff_exhausts_and_raises():
    async def always_fails():
        raise TimeoutError("Model upstream timeout")

    with pytest.raises(TimeoutError):
        await retry_with_backoff(
            always_fails,
            max_retries=2,
            base_delay_ms=10.0,
            retryable_exceptions=(TimeoutError,),
        )


@pytest.mark.asyncio
async def test_jev_engine_circuit_breaker_open_fails_fast():
    cb = CircuitBreaker("jev_test", failure_threshold=1, recovery_timeout_sec=10.0)
    
    # Pre-trip circuit breaker to OPEN
    cb.state = CircuitBreakerState.OPEN
    cb.last_failure_time = time.time()

    client = TypeSafeJevClient(api_key="valid_key")
    engine = TypeSafeJevEngine(client=client, circuit_breaker=cb)

    # When evaluate is called, it should immediately fall back without throwing an error
    decision = await engine.evaluate("Analyze multi-region failover")
    assert decision is not None
    assert decision.raw_details.get("circuit_breaker_tripped") is True
    assert decision.raw_details.get("error_category") == "circuit_breaker_open"
    assert decision.raw_details.get("fallback_reason") == "jev_circuit_breaker_open"


class UnstableFrontierProvider(ModelProvider):
    def __init__(self):
        self.call_count = 0

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        self.call_count += 1
        raise ConnectionResetError("Frontier vendor 503 Service Unavailable")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0

    async def health(self) -> ProviderHealth:
        return ProviderHealth(status="unavailable", error="503")

    @property
    def metadata(self):
        return {"model_name": "unstable-frontier"}


@pytest.mark.asyncio
async def test_provider_registry_circuit_breaker_and_retries_failover():
    frontier = UnstableFrontierProvider()
    registry = ProviderRegistry(frontier_model_provider=frontier)

    # 1. First execution should retry and then failover
    resp1, fallback1, reason1, retries1, cb_tripped1, err_cat1 = await registry.execute_route(
        RouteType.FRONTIER_MODEL, "Task 1"
    )
    assert fallback1 is True
    assert retries1 == 1  # Retried once before failing over
    assert resp1.model_name == "small-fast-v1"

    # 2. Second failure trips the circuit breaker (failure_threshold=2)
    resp2, fallback2, reason2, retries2, cb_tripped2, err_cat2 = await registry.execute_route(
        RouteType.FRONTIER_MODEL, "Task 2"
    )
    assert fallback2 is True

    # Check frontier circuit breaker is now OPEN
    frontier_cb = registry.circuit_breakers[RouteType.FRONTIER_MODEL]
    assert frontier_cb.state == CircuitBreakerState.OPEN

    # 3. Third execution should trip circuit breaker fail-fast immediately (0 retries)
    resp3, fallback3, reason3, retries3, cb_tripped3, err_cat3 = await registry.execute_route(
        RouteType.FRONTIER_MODEL, "Task 3"
    )
    assert fallback3 is True
    assert cb_tripped3 is True
    assert err_cat3 == "circuit_breaker_open"
    assert retries3 == 0  # No network retries attempted because circuit was OPEN!
    assert resp3.model_name == "small-fast-v1"
