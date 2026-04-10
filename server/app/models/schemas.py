from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import MediaType
from app.utils.constants import INVALID_INSTAGRAM_URL_MESSAGE, INSTAGRAM_USERNAME_PATTERN


class LoginRequest(BaseModel):
    username: str = Field(..., pattern=INSTAGRAM_USERNAME_PATTERN)
    password: str = Field(..., min_length=1)
    otp_code: str | None = Field(default=None, min_length=4, max_length=8)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    session_id: str
    expires_at: datetime


class LogoutResponse(BaseModel):
    success: bool
    message: str


class SessionStatusResponse(BaseModel):
    authenticated: bool
    username: str | None = None
    session_id: str | None = None
    expires_at: datetime | None = None


class FollowerResponse(BaseModel):
    username: str
    full_name: str
    profile_pic_url: str
    is_verified: bool = False


class FollowerListResponse(BaseModel):
    followers: list[FollowerResponse]
    total_count: int
    fetched_at: datetime


class UnfollowerResponse(BaseModel):
    unfollowers: list[FollowerResponse]
    total_count: int
    fetched_at: datetime


class NotFollowingBackResponse(BaseModel):
    not_following_back: list[FollowerResponse]
    total_count: int
    fetched_at: datetime


class MutualFollowersResponse(BaseModel):
    mutual_followers: list[FollowerResponse]
    total_count: int
    fetched_at: datetime


class AnalysisResponse(BaseModel):
    total_followers: int
    total_following: int
    unfollowers: int
    not_following_back: int
    mutual_followers: int
    engagement_rate: float
    fetched_at: datetime


class PostDownloadRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_instagram_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(INVALID_INSTAGRAM_URL_MESSAGE)

        if parsed.netloc not in {"instagram.com", "www.instagram.com"}:
            raise ValueError(INVALID_INSTAGRAM_URL_MESSAGE)

        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2 or parts[0] not in {"p", "reel"}:
            raise ValueError(INVALID_INSTAGRAM_URL_MESSAGE)

        return value


class PostDownloadResponse(BaseModel):
    media_url: str
    source_media_url: str | None = None
    caption: str | None = None
    media_type: MediaType
    shortcode: str
    downloaded_at: datetime


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(extra="ignore")
