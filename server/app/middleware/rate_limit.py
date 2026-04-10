from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import Settings

limiter = Limiter(key_func=get_remote_address)


def build_rate_limit_rule(settings: Settings) -> str:
    if settings.rate_limit_period == 3600:
        return f"{settings.rate_limit_requests}/hour"
    if settings.rate_limit_period == 60:
        return f"{settings.rate_limit_requests}/minute"
    return f"{settings.rate_limit_requests}/{settings.rate_limit_period}seconds"
