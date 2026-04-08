from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from ..deps import get_bearer_token
from ...models.schemas import AccessTokenResponse, AuthStatusResponse, LoginRequest, MessageResponse
from ...services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AccessTokenResponse)
async def login(payload: LoginRequest):
    return await run_in_threadpool(auth_service.login_user, payload.username, payload.password, payload.two_factor_code)


@router.post("/logout", response_model=MessageResponse)
async def logout(token: str = Depends(get_bearer_token)):
    return await run_in_threadpool(auth_service.logout_token, token)


@router.get("/status", response_model=AuthStatusResponse)
async def status(token: str = Depends(get_bearer_token)):
    username = await run_in_threadpool(auth_service.get_username_from_token, token)
    return {"is_authenticated": True, "username": username}
