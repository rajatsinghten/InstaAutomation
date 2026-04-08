import re
from pathlib import Path
from typing import Optional
from uuid import uuid4

import instaloader
from instaloader.exceptions import TwoFactorAuthRequiredException

from ..core.config import settings
from ..core.exceptions import APIError
from ..core.security import create_access_token, decode_access_token

SESSIONS_DIR = Path(__file__).resolve().parents[2] / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

REVOKED_JTIS: set[str] = set()


def _sanitize_username(username: str) -> str:
    cleaned = username.strip()
    if not re.fullmatch(r"[A-Za-z0-9._]+", cleaned):
        raise APIError(status_code=400, code="INVALID_USERNAME", message="Invalid username format")
    return cleaned


def _session_path(username: str) -> Path:
    safe_username = _sanitize_username(username)
    return SESSIONS_DIR / f"{safe_username}.session"


def login_user(username: str, password: str, two_factor_code: Optional[str] = None) -> dict:
    username = _sanitize_username(username)
    loader = instaloader.Instaloader()

    try:
        loader.login(username, password)
    except TwoFactorAuthRequiredException:
        if not two_factor_code:
            raise APIError(status_code=401, code="TWO_FACTOR_REQUIRED", message="Two-factor code is required")
        try:
            loader.two_factor_login(str(two_factor_code))
        except Exception as exc:
            raise APIError(status_code=401, code="TWO_FACTOR_FAILED", message="Two-factor authentication failed") from exc
    except Exception as exc:
        raise APIError(status_code=401, code="LOGIN_FAILED", message=f"Login failed: {exc}") from exc

    session_path = _session_path(username)
    loader.save_session_to_file(str(session_path))

    jti = str(uuid4())
    token = create_access_token(username=username, jti=jti)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


def get_username_from_token(token: str) -> str:
    payload = decode_access_token(token)
    username = payload.get("sub")
    jti = payload.get("jti")

    if not username or not jti:
        raise APIError(status_code=401, code="INVALID_TOKEN", message="Token payload is invalid")

    if jti in REVOKED_JTIS:
        raise APIError(status_code=401, code="TOKEN_REVOKED", message="Token has been revoked")

    session_path = _session_path(username)
    if not session_path.exists():
        raise APIError(status_code=401, code="SESSION_EXPIRED", message="Instagram session is missing or expired")

    return username


def get_loader_for_username(username: str) -> instaloader.Instaloader:
    username = _sanitize_username(username)
    session_path = _session_path(username)

    if not session_path.exists():
        raise APIError(status_code=401, code="SESSION_EXPIRED", message="Instagram session is missing or expired")

    loader = instaloader.Instaloader()
    loader.context.max_connection_attempts = 1
    try:
        loader.load_session_from_file(username, str(session_path))
    except Exception as exc:
        raise APIError(status_code=401, code="SESSION_INVALID", message="Failed to restore Instagram session") from exc

    return loader


def logout_token(token: str) -> dict:
    payload = decode_access_token(token)
    username = payload.get("sub")
    jti = payload.get("jti")

    if jti:
        REVOKED_JTIS.add(jti)

    if username:
        session_path = _session_path(username)
        if session_path.exists():
            session_path.unlink()

    return {"message": "Logged out successfully"}
