from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.exceptions.custom_exceptions import InstagramAuthError

security = HTTPBearer(auto_error=True)


async def get_token_payload(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    token = credentials.credentials
    auth_service = request.app.state.auth_service

    try:
        return await auth_service.verify_access_token(token)
    except InstagramAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


def get_session_id_from_payload(payload: dict) -> str:
    session_id = payload.get("sid")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session in token",
        )
    return session_id
