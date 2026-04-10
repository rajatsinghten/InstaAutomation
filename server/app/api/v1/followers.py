from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request

from app.middleware.auth_middleware import get_session_id_from_payload, get_token_payload
from app.models.schemas import (
    AnalysisResponse,
    FollowerListResponse,
    MutualFollowersResponse,
    NotFollowingBackResponse,
    UnfollowerResponse,
)

router = APIRouter()


@router.get("/list", response_model=FollowerListResponse)
async def list_followers(
    request: Request,
    refresh: bool = Query(default=False),
    token_payload: dict = Depends(get_token_payload),
) -> FollowerListResponse:
    follower_service = request.app.state.follower_service
    session_id = get_session_id_from_payload(token_payload)
    followers = await follower_service.list_followers(session_id, refresh=refresh)
    return FollowerListResponse(
        followers=followers,
        total_count=len(followers),
        fetched_at=datetime.now(UTC),
    )


@router.get("/unfollowers", response_model=UnfollowerResponse)
async def get_unfollowers(
    request: Request,
    refresh: bool = Query(default=False),
    token_payload: dict = Depends(get_token_payload),
) -> UnfollowerResponse:
    follower_service = request.app.state.follower_service
    session_id = get_session_id_from_payload(token_payload)
    unfollowers = await follower_service.get_unfollowers(session_id, refresh=refresh)
    return UnfollowerResponse(
        unfollowers=unfollowers,
        total_count=len(unfollowers),
        fetched_at=datetime.now(UTC),
    )


@router.get("/not-following", response_model=NotFollowingBackResponse)
async def get_not_following_back(
    request: Request,
    refresh: bool = Query(default=False),
    token_payload: dict = Depends(get_token_payload),
) -> NotFollowingBackResponse:
    follower_service = request.app.state.follower_service
    session_id = get_session_id_from_payload(token_payload)
    results = await follower_service.get_not_following_back(session_id, refresh=refresh)
    return NotFollowingBackResponse(
        not_following_back=results,
        total_count=len(results),
        fetched_at=datetime.now(UTC),
    )


@router.get("/mutual", response_model=MutualFollowersResponse)
async def get_mutual_followers(
    request: Request,
    refresh: bool = Query(default=False),
    token_payload: dict = Depends(get_token_payload),
) -> MutualFollowersResponse:
    follower_service = request.app.state.follower_service
    session_id = get_session_id_from_payload(token_payload)
    results = await follower_service.get_mutual(session_id, refresh=refresh)
    return MutualFollowersResponse(
        mutual_followers=results,
        total_count=len(results),
        fetched_at=datetime.now(UTC),
    )


@router.get("/stats", response_model=AnalysisResponse)
async def get_follower_stats(
    request: Request,
    refresh: bool = Query(default=False),
    token_payload: dict = Depends(get_token_payload),
) -> AnalysisResponse:
    follower_service = request.app.state.follower_service
    session_id = get_session_id_from_payload(token_payload)
    return await follower_service.get_stats(session_id, refresh=refresh)
