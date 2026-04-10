from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError

from app.config import Settings
from app.exceptions.custom_exceptions import InstagramAuthError, SessionNotFoundError
from app.services.instagram_client import InstagramClient
from app.services.session_manager import SessionManager


class AuthService:
    def __init__(self, settings: Settings, session_manager: SessionManager):
        self.settings = settings
        self.session_manager = session_manager

    async def login(
        self, username: str, password: str, otp_code: str | None = None
    ) -> tuple[str, str, datetime]:
        client = InstagramClient(
            username=username,
            password=password,
            headless=self.settings.headless_mode,
            use_real_login=self.settings.enable_real_instagram_login,
            otp_code=otp_code,
        )
        authenticated = await client.login()
        if not authenticated:
            raise InstagramAuthError("Instagram login failed")

        session = await self.session_manager.create_session(username=username, client=client)
        expires_delta = timedelta(minutes=self.settings.access_token_expire_minutes)
        expires_at = datetime.now(UTC) + expires_delta

        token_payload = {
            "sub": username,
            "sid": session.session_id,
            "exp": expires_at,
        }
        access_token = jwt.encode(
            token_payload,
            self.settings.secret_key,
            algorithm=self.settings.algorithm,
        )
        return access_token, session.session_id, expires_at

    async def verify_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.settings.algorithm],
            )
        except InvalidTokenError as exc:
            raise InstagramAuthError("Invalid access token") from exc

        session_id = payload.get("sid")
        if not session_id:
            raise InstagramAuthError("Token does not include session")

        try:
            await self.session_manager.get_session(session_id)
        except SessionNotFoundError as exc:
            raise InstagramAuthError("Session is invalid or expired") from exc

        return payload

    async def logout(self, session_id: str) -> None:
        client = await self.session_manager.get_client(session_id)
        close_method = getattr(client, "close", None)
        if callable(close_method):
            await close_method()
        await self.session_manager.invalidate_session(session_id)
