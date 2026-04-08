import json
import re
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles
import aiohttp
import instaloader
from instaloader import exceptions as iex

from ..core.config import settings
from ..core.exceptions import APIError
from .cache_manager import cache_manager

DOWNLOADS_DIR = Path(__file__).resolve().parents[2] / "data" / "downloads"
EXPORTS_DIR = Path(__file__).resolve().parents[2] / "data" / "exports"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

SHORTCODE_RE = re.compile(r"(?:https?://(?:www\.)?instagram\.com)?/(p|reel)/([^/?#&]+)")
SESSION_RATE_LIMITS: dict[str, datetime] = {}


def _now_utc() -> datetime:
    return datetime.utcnow()


def _get_cooldown_error(until: datetime) -> APIError:
    remaining = max(int((until - _now_utc()).total_seconds()), 1)
    minutes = (remaining + 59) // 60
    return APIError(
        status_code=429,
        code="RATE_LIMITED",
        message=f"Instagram has temporarily restricted this session. Retry after about {minutes} minute(s).",
    )


def _enforce_session_cooldown(session_username: str):
    until = SESSION_RATE_LIMITS.get(session_username)
    if until and _now_utc() < until:
        raise _get_cooldown_error(until)
    if until and _now_utc() >= until:
        SESSION_RATE_LIMITS.pop(session_username, None)


def _set_session_cooldown(session_username: str):
    cooldown = timedelta(minutes=max(settings.instagram_rate_limit_cooldown_minutes, 1))
    SESSION_RATE_LIMITS[session_username] = _now_utc() + cooldown


async def _write_text_file_async(file_path: Path, content: str):
    async with aiofiles.open(file_path, "w", encoding="utf-8") as file_handle:
        await file_handle.write(content)


async def _download_file_async(url: str, file_path: Path):
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status >= 400:
                raise APIError(
                    status_code=502,
                    code="PROFILE_PIC_DOWNLOAD_FAILED",
                    message=f"Profile picture download failed with HTTP {response.status}",
                )
            payload = await response.read()

    async with aiofiles.open(file_path, "wb") as file_handle:
        await file_handle.write(payload)


def _get_field(obj, primary_name: str, fallback_name: str, default=0):
    if hasattr(obj, primary_name):
        return getattr(obj, primary_name)
    if hasattr(obj, fallback_name):
        return getattr(obj, fallback_name)
    return default


def _classify_session_state(loader: instaloader.Instaloader) -> APIError:
    try:
        viewer = loader.test_login()
        if viewer:
            return APIError(status_code=404, code="PROFILE_NOT_FOUND", message="Requested profile does not exist")
        return APIError(
            status_code=429,
            code="RATE_LIMITED",
            message="Instagram temporarily blocked this session. Please wait and retry.",
        )
    except iex.InstaloaderException as exc:
        error_text = str(exc).lower()
        if "please wait a few minutes" in error_text or "too many" in error_text or "429" in error_text:
            return APIError(
                status_code=429,
                code="RATE_LIMITED",
                message="Instagram temporarily blocked this session. Please wait and retry.",
            )
        return APIError(
            status_code=401,
            code="SESSION_INVALID",
            message="Instagram session is invalid or expired. Please login again.",
        )


def _load_profile(loader: instaloader.Instaloader, username: str) -> instaloader.Profile:
    username = username.strip()
    if not username:
        raise APIError(status_code=400, code="INVALID_USERNAME", message="Username is required")

    try:
        return instaloader.Profile.from_username(loader.context, username)
    except iex.ProfileNotExistsException as exc:
        session_error = _classify_session_state(loader)
        if session_error.code == "PROFILE_NOT_FOUND":
            session_error.message = f"Unable to load profile: {username}"
        raise session_error from exc
    except iex.LoginRequiredException as exc:
        raise APIError(status_code=401, code="LOGIN_REQUIRED", message="Instagram login is required for this action") from exc
    except iex.QueryReturnedForbiddenException as exc:
        raise APIError(status_code=403, code="PROFILE_FORBIDDEN", message="Instagram denied access to this profile") from exc
    except iex.TooManyRequestsException as exc:
        raise APIError(status_code=429, code="RATE_LIMITED", message="Instagram rate limit reached. Try again later") from exc
    except iex.ConnectionException as exc:
        raise APIError(status_code=503, code="INSTAGRAM_UNREACHABLE", message="Unable to reach Instagram right now") from exc
    except iex.InstaloaderException as exc:
        raise APIError(status_code=502, code="INSTAGRAM_ERROR", message=f"Instagram request failed: {exc}") from exc


def calculate_engagement(loader: instaloader.Instaloader, username: str, session_username: str) -> dict:
    cache_key = username.strip().lower()
    cached = cache_manager.get("engagement", session_username, cache_key)
    if cached:
        return cached

    _enforce_session_cooldown(session_username)
    profile = _load_profile(loader, username)

    follower_count = _get_field(profile, "follower_count", "followers", 0)
    if follower_count <= 0:
        raise APIError(status_code=400, code="INVALID_FOLLOWER_COUNT", message="Follower count must be greater than zero")

    total_likes = 0
    total_comments = 0
    total_posts = 0

    max_posts = settings.engagement_max_posts

    try:
        for post in profile.get_posts():
            total_likes += _get_field(post, "like_count", "likes", 0)
            total_comments += _get_field(post, "comment_count", "comments", 0)
            total_posts += 1
            # 0 or negative means "official" mode: scan all available posts.
            if max_posts > 0 and total_posts >= max_posts:
                break
    except iex.PrivateProfileNotFollowedException as exc:
        raise APIError(status_code=403, code="PRIVATE_PROFILE", message="Cannot read posts from a private profile you do not follow") from exc
    except iex.TooManyRequestsException as exc:
        _set_session_cooldown(session_username)
        raise APIError(status_code=429, code="RATE_LIMITED", message="Instagram rate limit reached. Try again later") from exc
    except iex.InstaloaderException as exc:
        if "please wait" in str(exc).lower() or "too many" in str(exc).lower() or "429" in str(exc):
            _set_session_cooldown(session_username)
        raise APIError(status_code=502, code="INSTAGRAM_ERROR", message=f"Instagram request failed: {exc}") from exc

    if total_posts == 0:
        raise APIError(status_code=404, code="NO_POSTS", message="No posts found for this profile")

    engagement_rate = ((total_likes + total_comments) / (follower_count * total_posts)) * 100

    result = {
        "username": profile.username,
        "followers": follower_count,
        "total_posts": total_posts,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "engagement_rate": round(engagement_rate, 4),
    }

    cache_manager.set(
        "engagement",
        session_username,
        cache_key,
        result,
        settings.engagement_cache_ttl_seconds,
    )
    return result


def export_followers(loader: instaloader.Instaloader, username: str, output_format: str, session_username: str) -> dict:
    cache_key = f"{username.strip().lower()}::{output_format}"
    cached = cache_manager.get("followers", session_username, cache_key)
    if cached:
        return cached

    _enforce_session_cooldown(session_username)
    profile = _load_profile(loader, username)
    max_items = max(settings.followers_export_max_items, 1)

    try:
        followers = []
        for follower in profile.get_followers():
            followers.append(follower.username)
            if len(followers) >= max_items:
                break
    except iex.PrivateProfileNotFollowedException as exc:
        raise APIError(status_code=403, code="PRIVATE_PROFILE", message="Cannot export followers for a private profile you do not follow") from exc
    except iex.TooManyRequestsException as exc:
        _set_session_cooldown(session_username)
        raise APIError(status_code=429, code="RATE_LIMITED", message="Instagram rate limit reached. Try again later") from exc
    except iex.InstaloaderException as exc:
        if "please wait" in str(exc).lower() or "too many" in str(exc).lower() or "429" in str(exc):
            _set_session_cooldown(session_username)
        raise APIError(status_code=502, code="INSTAGRAM_ERROR", message=f"Instagram request failed: {exc}") from exc

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    ext = "json" if output_format == "json" else "txt"
    file_name = f"{profile.username}_followers_{timestamp}.{ext}"
    file_path = EXPORTS_DIR / file_name

    if output_format == "json":
        payload = json.dumps({"username": profile.username, "followers": followers}, indent=2)
        asyncio.run(_write_text_file_async(file_path, payload))
    else:
        payload = "\n".join(followers)
        asyncio.run(_write_text_file_async(file_path, payload))

    result = {
        "username": profile.username,
        "count": len(followers),
        "file_name": file_name,
        "file_url": f"/api/v1/files/exports/{file_name}",
    }

    cache_manager.set(
        "followers",
        session_username,
        cache_key,
        result,
        settings.followers_cache_ttl_seconds,
    )
    return result


def _extract_shortcode(url: str) -> str:
    match = SHORTCODE_RE.search(url.strip())
    if not match:
        raise APIError(status_code=400, code="INVALID_URL", message="Invalid Instagram post or reel URL")
    return match.group(2)


def download_post_by_url(loader: instaloader.Instaloader, url: str, session_username: str) -> dict:
    _enforce_session_cooldown(session_username)
    shortcode = _extract_shortcode(url)

    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
    except iex.QueryReturnedNotFoundException as exc:
        raise APIError(status_code=404, code="POST_NOT_FOUND", message="Unable to load post from URL") from exc
    except iex.QueryReturnedForbiddenException as exc:
        raise APIError(status_code=403, code="POST_FORBIDDEN", message="Instagram denied access to this post") from exc
    except iex.TooManyRequestsException as exc:
        _set_session_cooldown(session_username)
        raise APIError(status_code=429, code="RATE_LIMITED", message="Instagram rate limit reached. Try again later") from exc
    except iex.InstaloaderException as exc:
        if "please wait" in str(exc).lower() or "too many" in str(exc).lower() or "429" in str(exc):
            _set_session_cooldown(session_username)
        raise APIError(status_code=502, code="INSTAGRAM_ERROR", message=f"Instagram request failed: {exc}") from exc

    previous_dirname_pattern = loader.dirname_pattern
    posts_dir_pattern = str(DOWNLOADS_DIR / "posts" / "{target}")

    try:
        loader.dirname_pattern = posts_dir_pattern
        loader.download_post(post, target=post.owner_username)
    except Exception as exc:
        raise APIError(status_code=500, code="POST_DOWNLOAD_FAILED", message=f"Post download failed: {exc}") from exc
    finally:
        loader.dirname_pattern = previous_dirname_pattern

    return {
        "shortcode": shortcode,
        "owner_username": post.owner_username,
        "output_folder": str(DOWNLOADS_DIR / "posts" / post.owner_username),
    }


def download_profile_picture(loader: instaloader.Instaloader, username: str, session_username: str) -> dict:
    cache_key = username.strip().lower()
    cached = cache_manager.get("profile_pic", session_username, cache_key)
    if cached:
        return cached

    _enforce_session_cooldown(session_username)
    profile = _load_profile(loader, username)

    output_dir = DOWNLOADS_DIR / "profile_pics" / profile.username
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{profile.username}_profile.jpg"

    try:
        if not profile.profile_pic_url:
            raise APIError(status_code=404, code="PROFILE_PIC_NOT_FOUND", message="Profile picture not found")
        asyncio.run(_download_file_async(str(profile.profile_pic_url), file_path))
    except APIError:
        raise
    except Exception as exc:
        raise APIError(status_code=500, code="PROFILE_PIC_DOWNLOAD_FAILED", message=f"Profile picture download failed: {exc}") from exc

    result = {
        "username": profile.username,
        "output_folder": str(output_dir),
    }

    cache_manager.set(
        "profile_pic",
        session_username,
        cache_key,
        result,
        settings.profile_pic_cache_ttl_seconds,
    )
    return result
