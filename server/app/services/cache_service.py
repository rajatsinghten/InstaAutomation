import json
import time
from typing import Any

from redis.asyncio import Redis, from_url


class CacheService:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Redis | None = None
        self._memory_cache: dict[str, tuple[float, str]] = {}

    async def startup(self) -> None:
        try:
            self.redis = from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
        except Exception:
            self.redis = None

    async def shutdown(self) -> None:
        if self.redis is not None:
            await self.redis.close()

    async def get(self, key: str) -> Any | None:
        if self.redis is not None:
            raw = await self.redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)

        cached = self._memory_cache.get(key)
        if cached is None:
            return None
        expires_at, raw = cached
        if time.time() > expires_at:
            self._memory_cache.pop(key, None)
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        payload = json.dumps(value)
        if self.redis is not None:
            await self.redis.setex(key, ttl_seconds, payload)
            return

        self._memory_cache[key] = (time.time() + ttl_seconds, payload)

    async def delete(self, key: str) -> None:
        if self.redis is not None:
            await self.redis.delete(key)
            return
        self._memory_cache.pop(key, None)
