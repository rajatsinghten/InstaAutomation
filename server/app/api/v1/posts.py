from fastapi import APIRouter, Depends, Request

from app.middleware.auth_middleware import get_session_id_from_payload, get_token_payload
from app.models.schemas import PostDownloadRequest, PostDownloadResponse

router = APIRouter()


@router.post("/download", response_model=PostDownloadResponse)
async def download_post(
    payload: PostDownloadRequest,
    request: Request,
    token_payload: dict = Depends(get_token_payload),
) -> PostDownloadResponse:
    post_service = request.app.state.post_service
    session_id = get_session_id_from_payload(token_payload)
    return await post_service.download_post(session_id, payload.url)
