from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.exceptions.custom_exceptions import SessionNotFoundError
from app.services.cache_service import CacheService


@dataclass
class SessionRecord:
    session_id: str
    username: str
    created_at: datetime
    expires_at: datetime


class SessionManager:
    def __init__(self, cache_service: CacheService, ttl_seconds: int = 86400):
        self.cache_service = cache_service
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, SessionRecord] = {}
        self._clients: dict[str, object] = {}

    def _cache_key(self, session_id: str) -> str:
        return f"session:{session_id}"

    async def create_session(self, username: str, client: object) -> SessionRecord:
        session_id = uuid4().hex
        now = datetime.now(UTC)
        record = SessionRecord(
            session_id=session_id,
            username=username,
            created_at=now,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        self._sessions[session_id] = record
        self._clients[session_id] = client

        payload = asdict(record)
        payload["created_at"] = record.created_at.isoformat()
        payload["expires_at"] = record.expires_at.isoformat()
        await self.cache_service.set(self._cache_key(session_id), payload, self.ttl_seconds)
        return record

    async def get_session(self, session_id: str) -> SessionRecord:
        record = self._sessions.get(session_id)
        if record is None:
            payload = await self.cache_service.get(self._cache_key(session_id))
            if payload is None:
                raise SessionNotFoundError("Session does not exist")
            record = SessionRecord(
                session_id=payload["session_id"],
                username=payload["username"],
                created_at=datetime.fromisoformat(payload["created_at"]),
                expires_at=datetime.fromisoformat(payload["expires_at"]),
            )
            self._sessions[session_id] = record

        if record.expires_at < datetime.now(UTC):
            await self.invalidate_session(session_id)
            raise SessionNotFoundError("Session has expired")

        return record

    async def invalidate_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._clients.pop(session_id, None)
        await self.cache_service.delete(self._cache_key(session_id))

    async def get_client(self, session_id: str) -> object:
        await self.get_session(session_id)
        client = self._clients.get(session_id)
        if client is None:
            raise SessionNotFoundError("Session client unavailable")
        return client
