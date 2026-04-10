from fastapi import APIRouter, Depends, Query, Request

from app.middleware.auth_middleware import get_session_id_from_payload, get_token_payload
from app.models.schemas import AnalysisResponse

router = APIRouter()


@router.get("/summary", response_model=AnalysisResponse)
async def get_analysis_summary(
    request: Request,
    refresh: bool = Query(default=False),
    token_payload: dict = Depends(get_token_payload),
) -> AnalysisResponse:
    follower_service = request.app.state.follower_service
    session_id = get_session_id_from_payload(token_payload)
    return await follower_service.get_stats(session_id, refresh=refresh)
