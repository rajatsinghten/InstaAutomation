import os
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from .api.v1.router import api_router
from .core.config import settings
from .core.exceptions import APIError

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(title=settings.api_title, version=settings.api_version)


def _get_allowed_origins() -> list[str]:
    raw_value = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(APIError)
async def api_error_handler(_: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.code, "message": exc.message},
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api", include_in_schema=False)
@app.get("/api/", include_in_schema=False)
@app.get("/api/v1", include_in_schema=False)
@app.get("/api/v1/", include_in_schema=False)
async def api_index():
    return {
        "message": "Instagram Automation API",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "versioned_routes": "/api/v1/*",
    }


@app.get("/api/docs", include_in_schema=False)
@app.get("/api/v1/docs", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/docs", status_code=307)


@app.get("/api/openapi.json", include_in_schema=False)
@app.get("/api/v1/openapi.json", include_in_schema=False)
async def openapi_redirect():
    return RedirectResponse(url="/openapi.json", status_code=307)


app.include_router(api_router, prefix="/api/v1")
