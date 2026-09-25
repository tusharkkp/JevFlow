import time
import asyncio
from typing import Dict, Tuple


class Bucket:
    def __init__(self, capacity: float, refill_rate_per_sec: float):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self.tokens = capacity
        self.last_updated = time.time()

    def consume(self) -> Tuple[bool, float, int]:
        now = time.time()
        elapsed = now - self.last_updated
        self.last_updated = now

        # Add newly accrued tokens
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True, 0.0, int(self.tokens)
        else:
            deficit = 1.0 - self.tokens
            retry_after = deficit / self.refill_rate
            return False, round(retry_after, 2), 0


class TokenBucketRateLimiter:
    """
    Token Bucket Gateway Rate Limiter.
    
    Operates at the gateway perimeter before System One or model execution.
    Tracks requests per minute per IP address or user ID.
    """

    def __init__(self, requests_per_minute: int = 60, burst_capacity: int = 10):
        self.capacity = float(burst_capacity)
        self.refill_rate = float(requests_per_minute) / 60.0  # tokens per second
        self._buckets: Dict[str, Bucket] = {}
        self._lock = asyncio.Lock()
        self.rejected_requests_count = 0
        self.total_requests_count = 0

    async def check_rate_limit(self, identifier: str) -> Tuple[bool, float, int]:
        """
        Check and consume 1 token for the specified identifier.
        
        Returns:
            Tuple of (allowed: bool, retry_after_sec: float, remaining_tokens: int)
        """
        async with self._lock:
            self.total_requests_count += 1
            if identifier not in self._buckets:
                self._buckets[identifier] = Bucket(self.capacity, self.refill_rate)

            allowed, retry_after, remaining = self._buckets[identifier].consume()
            if not allowed:
                self.rejected_requests_count += 1
            return allowed, retry_after, remaining

    async def get_stats(self) -> dict:
        async with self._lock:
            return {
                "active_buckets": len(self._buckets),
                "total_requests": self.total_requests_count,
                "rejected_requests": self.rejected_requests_count,
                "refill_rate_per_sec": self.refill_rate,
                "burst_capacity": self.capacity,
            }
