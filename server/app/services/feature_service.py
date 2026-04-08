import json
import re
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles
import aiohttp
from instagrapi import Client
from instagrapi import exceptions as iex

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


def _get_user_info(client: Client, username: str):
    try:
        return client.user_info_by_username(username)
    except iex.UserNotFound:
        raise APIError(status_code=404, code="PROFILE_NOT_FOUND", message=f"Unable to load profile: {username}")
    except iex.LoginRequired:
        raise APIError(status_code=401, code="LOGIN_REQUIRED", message="Instagram login is required for this action")
    except (iex.PleaseWaitFewMinutes, iex.RateLimitError):
        raise APIError(status_code=429, code="RATE_LIMITED", message="Instagram rate limit reached. Try again later")
    except Exception as exc:
        raise APIError(status_code=502, code="INSTAGRAM_ERROR", message=f"Instagram request failed: {exc}")


def calculate_engagement(client: Client, username: str, session_username: str) -> dict:
    cache_key = username.strip().lower()
    cached = cache_manager.get("engagement", session_username, cache_key)
    if cached:
        return cached

    _enforce_session_cooldown(session_username)
    user_info = _get_user_info(client, username)

    follower_count = user_info.follower_count
    if follower_count <= 0:
        raise APIError(status_code=400, code="INVALID_FOLLOWER_COUNT", message="Follower count must be greater than zero")

    try:
        max_posts = settings.engagement_max_posts
        medias = client.user_medias(user_info.pk, amount=max_posts)
    except (iex.PleaseWaitFewMinutes, iex.RateLimitError):
        _set_session_cooldown(session_username)
        raise APIError(status_code=429, code="RATE_LIMITED", message="Instagram rate limit reached. Try again later")
    except Exception as exc:
        raise APIError(status_code=502, code="INSTAGRAM_ERROR", message=f"Instagram request failed: {exc}")

    total_posts = len(medias)
    if total_posts == 0:
        raise APIError(status_code=404, code="NO_POSTS", message="No posts found for this profile")

    total_likes = sum([m.like_count for m in medias])
    total_comments = sum([m.comment_count for m in medias])

    engagement_rate = ((total_likes + total_comments) / (follower_count * total_posts)) * 100

    result = {
        "username": user_info.username,
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


def export_followers(client: Client, username: str, output_format: str, session_username: str) -> dict:
    cache_key = f"{username.strip().lower()}::{output_format}"
    cached = cache_manager.get("followers", session_username, cache_key)
    if cached:
        return cached

    _enforce_session_cooldown(session_username)
    user_info = _get_user_info(client, username)
    max_items = max(settings.followers_export_max_items, 1)

    try:
        followers_dict = client.user_followers(user_info.pk, amount=max_items)
        followers = [f.username for f in followers_dict.values()]
    except (iex.PleaseWaitFewMinutes, iex.RateLimitError):
        _set_session_cooldown(session_username)
        raise APIError(status_code=429, code="RATE_LIMITED", message="Instagram rate limit reached. Try again later")
    except Exception as exc:
        raise APIError(status_code=502, code="INSTAGRAM_ERROR", message=f"Instagram request failed: {exc}")

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    ext = "json" if output_format == "json" else "txt"
    file_name = f"{user_info.username}_followers_{timestamp}.{ext}"
    file_path = EXPORTS_DIR / file_name

    if output_format == "json":
        payload = json.dumps({"username": user_info.username, "followers": followers}, indent=2)
        asyncio.run(_write_text_file_async(file_path, payload))
    else:
        payload = "\n".join(followers)
        asyncio.run(_write_text_file_async(file_path, payload))

    result = {
        "username": user_info.username,
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


def download_post_by_url(client: Client, url: str, session_username: str) -> dict:
    _enforce_session_cooldown(session_username)
    shortcode = _extract_shortcode(url)

    try:
        media_pk = client.media_pk_from_url(url)
        media = client.media_info(media_pk)
    except iex.MediaNotFound:
        raise APIError(status_code=404, code="POST_NOT_FOUND", message="Unable to load post from URL")
    except (iex.PleaseWaitFewMinutes, iex.RateLimitError):
        _set_session_cooldown(session_username)
        raise APIError(status_code=429, code="RATE_LIMITED", message="Instagram rate limit reached. Try again later")
    except Exception as exc:
        raise APIError(status_code=502, code="INSTAGRAM_ERROR", message=f"Instagram request failed: {exc}")

    target_dir = DOWNLOADS_DIR / "posts" / media.user.username
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        # media_download handles photos, videos, albums, and clips
        client.media_download(media_pk, target_dir)
    except Exception as exc:
        raise APIError(status_code=500, code="POST_DOWNLOAD_FAILED", message=f"Post download failed: {exc}")

    return {
        "shortcode": shortcode,
        "owner_username": media.user.username,
        "output_folder": str(target_dir),
    }


def download_profile_picture(client: Client, username: str, session_username: str) -> dict:
    cache_key = username.strip().lower()
    cached = cache_manager.get("profile_pic", session_username, cache_key)
    if cached:
        return cached

    _enforce_session_cooldown(session_username)
    user_info = _get_user_info(client, username)

    output_dir = DOWNLOADS_DIR / "profile_pics" / user_info.username
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{user_info.username}_profile.jpg"

    try:
        if not user_info.profile_pic_url:
            raise APIError(status_code=404, code="PROFILE_PIC_NOT_FOUND", message="Profile picture not found")
        asyncio.run(_download_file_async(str(user_info.profile_pic_url), file_path))
    except APIError:
        raise
    except Exception as exc:
        raise APIError(status_code=500, code="PROFILE_PIC_DOWNLOAD_FAILED", message=f"Profile picture download failed: {exc}")

    result = {
        "username": user_info.username,
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
