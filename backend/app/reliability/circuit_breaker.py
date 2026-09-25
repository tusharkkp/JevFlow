import time
import logging
from enum import Enum
from typing import Callable, Any, Optional

logger = logging.getLogger("jevflow.circuit_breaker")


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"          # Normal operation: requests pass through
    OPEN = "open"              # Failing upstream: fail fast without executing calls
    HALF_OPEN = "half_open"    # Trial recovery: send limited test requests


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""
    def __init__(self, name: str, retry_after_sec: float):
        super().__init__(f"Circuit breaker '{name}' is OPEN. Retry after {retry_after_sec:.1f}s.")
        self.name = name
        self.retry_after_sec = retry_after_sec


class CircuitBreaker:
    """
    Asynchronous Circuit Breaker.
    
    Protects downstream services (Jev API, LLM providers) from cascading failures.
    Transitions:
    - CLOSED -> OPEN: When consecutive failures >= failure_threshold
    - OPEN -> HALF_OPEN: When recovery_timeout_sec elapses
    - HALF_OPEN -> CLOSED: When a trial request succeeds
    - HALF_OPEN -> OPEN: When a trial request fails
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout_sec: float = 10.0,
        half_open_success_threshold: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.half_open_success_threshold = half_open_success_threshold

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change: float = time.time()

    def _check_and_update_state(self):
        now = time.time()
        if self.state == CircuitBreakerState.OPEN:
            elapsed = now - (self.last_failure_time or now)
            if elapsed >= self.recovery_timeout_sec:
                logger.info("Circuit breaker '%s' transition: OPEN -> HALF_OPEN", self.name)
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                self.last_state_change = now

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        self._check_and_update_state()

        if self.state == CircuitBreakerState.OPEN:
            elapsed = time.time() - (self.last_failure_time or time.time())
            remaining = max(0.1, self.recovery_timeout_sec - elapsed)
            raise CircuitBreakerOpenException(self.name, remaining)

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as exc:
            self._record_failure(exc)
            raise

    def _record_success(self):
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_success_threshold:
                logger.info("Circuit breaker '%s' recovered: HALF_OPEN -> CLOSED", self.name)
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.last_state_change = time.time()
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0

    def _record_failure(self, exc: Exception):
        now = time.time()
        self.last_failure_time = now
        self.failure_count += 1
        logger.warning(
            "Circuit breaker '%s' recorded failure (%d/%d): %s",
            self.name,
            self.failure_count,
            self.failure_threshold,
            exc,
        )

        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.warning("Circuit breaker '%s' failed trial: HALF_OPEN -> OPEN", self.name)
            self.state = CircuitBreakerState.OPEN
            self.last_state_change = now
        elif self.state == CircuitBreakerState.CLOSED and self.failure_count >= self.failure_threshold:
            logger.error("Circuit breaker '%s' tripped: CLOSED -> OPEN", self.name)
            self.state = CircuitBreakerState.OPEN
            self.last_state_change = now

    def get_status(self) -> dict:
        self._check_and_update_state()
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "last_state_change": self.last_state_change,
        }
