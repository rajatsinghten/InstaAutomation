from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from ..deps import get_authenticated_loader, get_current_username
from ...core.exceptions import APIError
from ...models.schemas import (
    DownloadPostRequest,
    DownloadPostResponse,
    EngagementRequest,
    EngagementResponse,
    FollowersExportRequest,
    FollowersExportResponse,
    ProfilePictureRequest,
    ProfilePictureResponse,
)
from ...services import feature_service
from ...services.rate_limiter import rate_limiter

router = APIRouter(tags=["instagram"])


async def _run_with_rate_limit(user_key: str, fn: Callable[..., Any], *args):
    await rate_limiter.wait(user_key)
    try:
        result = await run_in_threadpool(fn, *args)
        rate_limiter.reset_backoff(user_key)
        return result
    except APIError as exc:
        if exc.status_code == 429 or exc.code == "RATE_LIMITED":
            rate_limiter.increase_backoff(user_key)
        raise


@router.post("/engagement/calculate", response_model=EngagementResponse)
async def calculate_engagement(
    payload: EngagementRequest,
    loader=Depends(get_authenticated_loader),
    current_username: str = Depends(get_current_username),
):
    target_username = (payload.username or current_username).strip()
    return await _run_with_rate_limit(current_username, feature_service.calculate_engagement, loader, target_username, current_username)


@router.post("/followers/export", response_model=FollowersExportResponse)
async def export_followers(
    payload: FollowersExportRequest,
    loader=Depends(get_authenticated_loader),
    current_username: str = Depends(get_current_username),
):
    target_username = (payload.username or current_username).strip()
    return await _run_with_rate_limit(
        current_username,
        feature_service.export_followers,
        loader,
        target_username,
        payload.output_format,
        current_username,
    )


@router.post("/posts/download", response_model=DownloadPostResponse)
async def download_post(
    payload: DownloadPostRequest,
    loader=Depends(get_authenticated_loader),
    current_username: str = Depends(get_current_username),
):
    return await _run_with_rate_limit(current_username, feature_service.download_post_by_url, loader, payload.url, current_username)


@router.post("/profile/picture", response_model=ProfilePictureResponse)
async def download_profile_picture(
    payload: ProfilePictureRequest,
    loader=Depends(get_authenticated_loader),
    current_username: str = Depends(get_current_username),
):
    target_username = (payload.username or current_username).strip()
    return await _run_with_rate_limit(current_username, feature_service.download_profile_picture, loader, target_username, current_username)


@router.get("/files/{category}/{file_name}")
async def download_generated_file(category: str, file_name: str):
    safe_name = Path(file_name).name
    if category == "exports":
        base_dir = feature_service.EXPORTS_DIR
    elif category == "downloads":
        base_dir = feature_service.DOWNLOADS_DIR
    else:
        raise APIError(status_code=400, code="INVALID_CATEGORY", message="Unsupported file category")

    file_path = base_dir / safe_name
    if not file_path.exists():
        raise APIError(status_code=404, code="FILE_NOT_FOUND", message="Requested file was not found")

    return FileResponse(path=file_path, filename=safe_name)
