from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from .config import settings
from .exceptions import APIError


def create_access_token(username: str, jti: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": username,
        "jti": jti,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise APIError(status_code=401, code="INVALID_TOKEN", message="Invalid or expired token") from exc
