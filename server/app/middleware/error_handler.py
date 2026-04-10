from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.custom_exceptions import (
    InstagramAuthError,
    InstagramAutomationError,
    PostDownloadError,
    SessionNotFoundError,
)


async def _handle_base_error(request: Request, exc: Exception) -> JSONResponse:
    del request
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def _handle_auth_error(request: Request, exc: InstagramAuthError) -> JSONResponse:
    del request
    return JSONResponse(status_code=401, content={"detail": str(exc)})


async def _handle_session_error(request: Request, exc: SessionNotFoundError) -> JSONResponse:
    del request
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def _handle_post_error(request: Request, exc: PostDownloadError) -> JSONResponse:
    del request
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def _handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    del request
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(InstagramAutomationError, _handle_base_error)
    app.add_exception_handler(InstagramAuthError, _handle_auth_error)
    app.add_exception_handler(SessionNotFoundError, _handle_session_error)
    app.add_exception_handler(PostDownloadError, _handle_post_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
