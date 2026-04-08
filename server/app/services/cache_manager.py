import time
from typing import Dict, Optional, Tuple


class CacheManager:
    """Simple in-memory TTL cache."""

    def __init__(self):
        self.cache: Dict[Tuple[str, str, str], Tuple[dict, float]] = {}

    def get(self, namespace: str, session_username: str, key: str) -> Optional[dict]:
        item = self.cache.get((namespace, session_username, key))
        if not item:
            return None

        payload, expires_at = item
        if time.time() >= expires_at:
            self.cache.pop((namespace, session_username, key), None)
            return None

        return payload

    def set(self, namespace: str, session_username: str, key: str, payload: dict, ttl_seconds: int):
        ttl = max(ttl_seconds, 1)
        expires_at = time.time() + ttl
        self.cache[(namespace, session_username, key)] = (payload, expires_at)


cache_manager = CacheManager()
