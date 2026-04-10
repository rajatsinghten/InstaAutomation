import re
from urllib.parse import urlparse

from app.utils.constants import INSTAGRAM_USERNAME_PATTERN


_instagram_username_re = re.compile(INSTAGRAM_USERNAME_PATTERN)


def is_valid_instagram_username(value: str) -> bool:
    return bool(_instagram_username_re.fullmatch(value))


def is_valid_instagram_post_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc not in {"instagram.com", "www.instagram.com"}:
        return False

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return False

    return parts[0] in {"p", "reel"} and bool(parts[1])
