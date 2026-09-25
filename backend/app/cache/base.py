from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseCache(ABC):
    """Abstract interface for gateway response caching layers."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached entry by key, or None if expired or not found."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 3600) -> None:
        """Store an entry in cache with a time-to-live in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove a cached entry by key."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Wipe all cached entries."""
        pass

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Check cache connectivity and item count."""
        pass
