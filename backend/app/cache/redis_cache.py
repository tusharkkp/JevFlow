import json
import logging
from typing import Optional, Dict, Any
from backend.app.cache.base import BaseCache
from backend.app.cache.memory_cache import MemoryCache

logger = logging.getLogger("jevflow.redis_cache")


class RedisCache(BaseCache):
    """
    Distributed Redis Cache.
    
    If Redis connection fails or redis package is missing,
    transparently falls back to local MemoryCache.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._fallback_cache = MemoryCache()
        self._redis_client = None
        self._connected = False

    async def _get_client(self):
        if self._redis_client is not None:
            return self._redis_client

        try:
            import redis.asyncio as aioredis
            self._redis_client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=1.0,
            )
            # Ping to verify connection
            await self._redis_client.ping()
            self._connected = True
            logger.info("Connected to Redis at %s", self.redis_url)
            return self._redis_client
        except Exception as exc:
            logger.warning("Redis unavailable (%s); falling back to in-memory cache.", exc)
            self._connected = False
            self._redis_client = None
            return None

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        client = await self._get_client()
        if not client:
            return await self._fallback_cache.get(key)

        try:
            val = await client.get(key)
            if val:
                return json.loads(val)
            return None
        except Exception as exc:
            logger.warning("Redis GET error (%s); reading from fallback cache.", exc)
            return await self._fallback_cache.get(key)

    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 3600) -> None:
        client = await self._get_client()
        if not client:
            await self._fallback_cache.set(key, value, ttl_seconds)
            return

        try:
            serialized = json.dumps(value)
            await client.setex(key, ttl_seconds, serialized)
        except Exception as exc:
            logger.warning("Redis SET error (%s); writing to fallback cache.", exc)
            await self._fallback_cache.set(key, value, ttl_seconds)

    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        if not client:
            return await self._fallback_cache.delete(key)

        try:
            count = await client.delete(key)
            return count > 0
        except Exception:
            return await self._fallback_cache.delete(key)

    async def clear(self) -> None:
        client = await self._get_client()
        if not client:
            await self._fallback_cache.clear()
            return

        try:
            await client.flushdb()
        except Exception:
            await self._fallback_cache.clear()

    async def health(self) -> Dict[str, Any]:
        client = await self._get_client()
        if not client or not self._connected:
            fallback_h = await self._fallback_cache.health()
            fallback_h["backend"] = "RedisCache (Degraded to MemoryCache)"
            return fallback_h

        return {
            "backend": "RedisCache",
            "status": "connected",
            "redis_url": self.redis_url,
        }
