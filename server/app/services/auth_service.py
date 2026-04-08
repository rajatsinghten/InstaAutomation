import re
import logging
import traceback
from pathlib import Path
from typing import Optional
from uuid import uuid4

from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    ChallengeRequired,
    TwoFactorRequired,
)

from ..core.config import settings
from ..core.exceptions import APIError
from ..core.security import create_access_token, decode_access_token

logger = logging.getLogger(__name__)

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
    return SESSIONS_DIR / f"{safe_username}.json"


def login_user(username: str, password: str, two_factor_code: Optional[str] = None) -> dict:
    username = _sanitize_username(username)
    cl = Client()
    
    # Setting a random user agent can sometimes help with JSONDecodeErrors from blocked agents
    cl.set_user_agent()

    logger.info(f"Attempting login for user: {username}")
    try:
        cl.login(username, password, verification_code=two_factor_code or "")
    except TwoFactorRequired:
        logger.warning(f"2FA required for user: {username}")
        if not two_factor_code:
            raise APIError(status_code=401, code="TWO_FACTOR_REQUIRED", message="Two-factor code is required")
        raise APIError(status_code=401, code="TWO_FACTOR_FAILED", message="Two-factor authentication failed")
    except BadPassword as exc:
        error_msg = str(exc)
        logger.error(f"Bad password or account issue for {username}: {error_msg}")
        # If Instagram says the password is wrong but the user is sure, 
        # it's often an IP block or a specific flag mentioned in the message.
        raise APIError(status_code=401, code="LOGIN_FAILED", message=f"Instagram reported: {error_msg}")
    except ChallengeRequired:
        logger.warning(f"Challenge required for user: {username}")
        raise APIError(
            status_code=401,
            code="CHALLENGE_REQUIRED",
            message="Instagram challenge required. Please log in via the official app, complete the verification, and then try again here.",
        )
    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"Unexpected login error for {username}: {error_msg}")
        logger.error(traceback.format_exc())
        
        if "Expecting value: line 1 column 1" in error_msg:
             message = "Instagram returned an invalid response. This often happens if your IP is flagged or a challenge is required. Please try logging in via the official Instagram app first."
        else:
             message = f"Login failed: {error_msg}"
             
        raise APIError(status_code=401, code="LOGIN_FAILED", message=message) from exc

    session_path = _session_path(username)
    cl.dump_settings(str(session_path))
    logger.info(f"Login successful, session saved for {username}")

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


def get_client_for_username(username: str) -> Client:
    username = _sanitize_username(username)
    session_path = _session_path(username)

    if not session_path.exists():
        raise APIError(status_code=401, code="SESSION_EXPIRED", message="Instagram session is missing or expired")

    cl = Client()
    try:
        cl.load_settings(str(session_path))
    except Exception as exc:
        logger.error(f"Failed to load session for {username}: {exc}")
        raise APIError(status_code=401, code="SESSION_INVALID", message="Failed to restore Instagram session") from exc

    return cl


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
