from typing import Literal, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=30)
    password: str = Field(..., min_length=1)
    two_factor_code: Optional[str] = None


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MessageResponse(BaseModel):
    message: str


class AuthStatusResponse(BaseModel):
    is_authenticated: bool
    username: Optional[str] = None


class EngagementRequest(BaseModel):
    username: Optional[str] = Field(default=None, min_length=1, max_length=30)


class EngagementResponse(BaseModel):
    username: str
    followers: int
    total_posts: int
    total_likes: int
    total_comments: int
    engagement_rate: float


class FollowersExportRequest(BaseModel):
    username: Optional[str] = Field(default=None, min_length=1, max_length=30)
    output_format: Literal["txt", "json"] = "txt"


class FollowersExportResponse(BaseModel):
    username: str
    count: int
    file_name: str
    file_url: str


class DownloadPostRequest(BaseModel):
    url: str = Field(..., min_length=1)


class DownloadPostResponse(BaseModel):
    shortcode: str
    owner_username: str
    output_folder: str


class ProfilePictureRequest(BaseModel):
    username: Optional[str] = Field(default=None, min_length=1, max_length=30)


class ProfilePictureResponse(BaseModel):
    username: str
    output_folder: str
