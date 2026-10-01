import time
import asyncio
from typing import Optional, Dict, Any, Tuple
from backend.app.cache.base import BaseCache


class MemoryCache(BaseCache):
    """
    High-performance in-memory cache with TTL and capacity limits.
    
    Used for local execution and as a fallback when Redis is unconfigured.
    """

    def __init__(self, max_entries: int = 5000):
        self.max_entries = max_entries
        self._store: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        async with self._lock:
            if key not in self._store:
                self.misses += 1
                return None

            value, expire_at = self._store[key]
            if now > expire_at:
                # Key expired
                del self._store[key]
                self.misses += 1
                return None

            self.hits += 1
            return value

    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 3600) -> None:
        now = time.time()
        expire_at = now + ttl_seconds
        async with self._lock:
            # Simple eviction: if at max capacity, remove oldest entry
            if len(self._store) >= self.max_entries and key not in self._store:
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]

            self._store[key] = (value, expire_at)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()
            self.hits = 0
            self.misses = 0

    async def health(self) -> Dict[str, Any]:
        async with self._lock:
            return {
                "backend": "MemoryCache",
                "status": "healthy",
                "active_entries": len(self._store),
                "max_entries": self.max_entries,
                "size": len(self._store),
                "max_size": self.max_entries,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(self.hits / max(1, self.hits + self.misses), 3),
            }
