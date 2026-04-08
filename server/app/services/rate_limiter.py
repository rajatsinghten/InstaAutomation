import asyncio
import logging
import time
from typing import Dict

from ..core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Handles per-user pacing with exponential backoff."""

    def __init__(self, min_delay: float, max_delay: float, max_backoff_multiplier: float):
        self.min_delay = max(min_delay, 0.0)
        self.max_delay = max(max_delay, self.min_delay)
        self.max_backoff_multiplier = max(max_backoff_multiplier, 1.0)
        self.last_request_time: Dict[str, float] = {}
        self.backoff_multiplier: Dict[str, float] = {}

    async def wait(self, user_key: str):
        current_time = time.time()
        last_time = self.last_request_time.get(user_key, 0.0)
        backoff = self.backoff_multiplier.get(user_key, 1.0)

        delay = min(self.min_delay * backoff, self.max_delay)
        elapsed = current_time - last_time

        if elapsed < delay:
            wait_time = delay - elapsed
            logger.info("Rate limiting %s: waiting %.2fs (backoff %.2fx)", user_key, wait_time, backoff)
            await asyncio.sleep(wait_time)

        self.last_request_time[user_key] = time.time()

    def increase_backoff(self, user_key: str):
        current = self.backoff_multiplier.get(user_key, 1.0)
        next_value = min(current * 1.5, self.max_backoff_multiplier)
        self.backoff_multiplier[user_key] = next_value
        logger.warning("Backoff increased for %s: %.2fx", user_key, next_value)

    def reset_backoff(self, user_key: str):
        self.backoff_multiplier[user_key] = 1.0


rate_limiter = RateLimiter(
    min_delay=settings.rate_limit_min_delay_seconds,
    max_delay=settings.rate_limit_max_delay_seconds,
    max_backoff_multiplier=settings.rate_limit_backoff_cap,
)
