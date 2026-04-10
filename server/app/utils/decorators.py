from collections.abc import Callable
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def retry_with_backoff(
    attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 8,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return retry(
        reraise=True,
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
    )
