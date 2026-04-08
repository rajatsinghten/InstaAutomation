from fastapi import APIRouter

from . import auth, instagram

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(instagram.router)
