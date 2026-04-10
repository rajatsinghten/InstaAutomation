from fastapi import APIRouter, Depends, Request

from app.middleware.auth_middleware import get_session_id_from_payload, get_token_payload
from app.middleware.rate_limit import limiter
from app.models.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SessionStatusResponse,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
@limiter.limit("20/minute")
async def login(request: Request, payload: LoginRequest) -> LoginResponse:

    auth_service = request.app.state.auth_service
    token, session_id, expires_at = await auth_service.login(
        username=payload.username,
        password=payload.password,
        otp_code=payload.otp_code,
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        session_id=session_id,
        expires_at=expires_at,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: Request, token_payload: dict = Depends(get_token_payload)) -> LogoutResponse:
    auth_service = request.app.state.auth_service
    session_id = get_session_id_from_payload(token_payload)
    await auth_service.logout(session_id)
    return LogoutResponse(success=True, message="Logged out successfully")


@router.get("/status", response_model=SessionStatusResponse)
async def session_status(
    request: Request,
    token_payload: dict = Depends(get_token_payload),
) -> SessionStatusResponse:
    session_id = get_session_id_from_payload(token_payload)
    session_manager = request.app.state.session_manager
    session = await session_manager.get_session(session_id)

    return SessionStatusResponse(
        authenticated=True,
        username=session.username,
        session_id=session.session_id,
        expires_at=session.expires_at,
    )
