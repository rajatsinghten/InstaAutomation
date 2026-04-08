from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from ..services import auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_bearer_token(token: str = Depends(oauth2_scheme)) -> str:
    return token


def get_current_username(token: str = Depends(get_bearer_token)) -> str:
    return auth_service.get_username_from_token(token)


def get_authenticated_client(username: str = Depends(get_current_username)):
    return auth_service.get_client_for_username(username)
