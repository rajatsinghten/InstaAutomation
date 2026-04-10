import asyncio
import re
from datetime import UTC, datetime
from pathlib import Path

from app.exceptions.custom_exceptions import InstagramAuthError, PostDownloadError
from app.models.enums import MediaType

try:
    from instagrapi import Client
    from instagrapi.exceptions import (
        BadPassword,
        ChallengeError,
        ChallengeRequired,
        ClientLoginRequired,
        LoginRequired,
    )
except ImportError:  # pragma: no cover - handled at runtime in login
    Client = None
    BadPassword = Exception
    ChallengeError = Exception
    ChallengeRequired = Exception
    ClientLoginRequired = Exception
    LoginRequired = Exception


class InstagramClient:
    """Instagram operations abstraction with real and demo modes."""

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True,
        use_real_login: bool = True,
    ):
        self.username = username
        self._password = password
        self.headless = headless
        self.use_real_login = use_real_login and not username.startswith("demo")
        self._logged_in = False
        self._client = None
        self._user_id = None

    async def login(self) -> bool:
        if not self.username or not self._password:
            raise InstagramAuthError("Invalid credentials")

        if self.use_real_login:
            if Client is None:
                raise InstagramAuthError(
                    "instagrapi is not installed. Install dependencies and retry."
                )
            try:
                await asyncio.to_thread(self._login_with_instagrapi)
            except BadPassword as exc:
                raise InstagramAuthError("Instagram login failed: bad password") from exc
            except (ChallengeRequired, ChallengeError) as exc:
                raise InstagramAuthError(
                    "Instagram login failed: challenge required on account"
                ) from exc
            except (LoginRequired, ClientLoginRequired) as exc:
                raise InstagramAuthError("Instagram login failed: login required") from exc
            except Exception as exc:
                raise InstagramAuthError(f"Instagram login failed: {exc}") from exc

        self._logged_in = True
        return True

    async def get_followers(self) -> list[str]:
        self._ensure_authenticated()
        if not self.use_real_login:
            return [
                "alex.dev",
                "sam.codes",
                "maya.design",
                "lin.analytics",
                "noah.writer",
                "tara.ai",
            ]
        try:
            return await asyncio.to_thread(self._collect_followers_sync)
        except Exception as exc:
            raise InstagramAuthError(f"Failed to fetch followers: {exc}") from exc

    async def get_following(self) -> list[str]:
        self._ensure_authenticated()
        if not self.use_real_login:
            return [
                "alex.dev",
                "sam.codes",
                "jules.video",
                "tara.ai",
                "casey.ops",
            ]
        try:
            return await asyncio.to_thread(self._collect_following_sync)
        except Exception as exc:
            raise InstagramAuthError(f"Failed to fetch following: {exc}") from exc

    async def download_post(self, post_url: str, download_dir: str | None = None) -> dict[str, str]:
        self._ensure_authenticated()
        match = re.search(r"/(?:p|reel)/([A-Za-z0-9_-]+)/?", post_url)
        if not match:
            raise PostDownloadError("Unable to extract Instagram shortcode")
        shortcode = match.group(1)

        if self.use_real_login:
            try:
                return await asyncio.to_thread(self._get_post_info_sync, post_url, download_dir)
            except Exception as exc:
                raise PostDownloadError(f"Failed to fetch post details: {exc}") from exc

        return {
            "media_url": f"https://instagram.com/p/{shortcode}/media/?size=l",
            "caption": "Downloaded via automation service",
            "media_type": MediaType.image.value,
            "shortcode": shortcode,
            "downloaded_at": datetime.now(UTC).isoformat(),
            "is_demo": True,
        }

    async def close(self) -> None:
        if self._client is not None:
            try:
                await asyncio.to_thread(self._client.logout)
            except Exception:
                pass
        self._logged_in = False
        self._client = None
        self._user_id = None

    def _ensure_authenticated(self) -> None:
        if not self._logged_in:
            raise InstagramAuthError("Instagram client not authenticated")

    def _login_with_instagrapi(self) -> None:
        client = Client()
        success = client.login(self.username, self._password)
        if not success:
            raise InstagramAuthError("Instagram login did not return success")
        self._client = client
        self._user_id = client.user_id_from_username(self.username)

    def _collect_followers_sync(self) -> list[str]:
        if self._client is None or self._user_id is None:
            raise InstagramAuthError("Profile context is missing")
        followers = self._client.user_followers(self._user_id, amount=0)
        return sorted(
            {
                user.username
                for user in followers.values()
                if getattr(user, "username", None)
            }
        )

    def _collect_following_sync(self) -> list[str]:
        if self._client is None or self._user_id is None:
            raise InstagramAuthError("Profile context is missing")
        following = self._client.user_following(self._user_id, amount=0)
        return sorted(
            {
                user.username
                for user in following.values()
                if getattr(user, "username", None)
            }
        )

    def _get_post_info_sync(self, post_url: str, download_dir: str | None = None) -> dict[str, str]:
        if self._client is None:
            raise InstagramAuthError("Instagram context is missing")

        target_folder = Path(download_dir) if download_dir else Path("downloads")
        target_folder.mkdir(parents=True, exist_ok=True)

        media_pk = self._client.media_pk_from_url(post_url)
        media = self._client.media_info(media_pk)

        media_type_raw = int(getattr(media, "media_type", 1))
        local_path = ""

        if media_type_raw == 2:
            media_type = MediaType.video.value
            product_type = str(getattr(media, "product_type", "") or "")
            if product_type == "clips":
                local_path = str(self._client.clip_download(media_pk, folder=target_folder))
            else:
                local_path = str(self._client.video_download(media_pk, folder=target_folder))
            media_url = getattr(media, "video_url", None) or getattr(
                media, "thumbnail_url", ""
            )
        elif media_type_raw == 8:
            media_type = MediaType.carousel.value
            album_files = self._client.album_download(media_pk, folder=target_folder)
            local_path = str(album_files[0]) if album_files else ""
            media_url = getattr(media, "thumbnail_url", "")
        else:
            media_type = MediaType.image.value
            local_path = str(self._client.photo_download(media_pk, folder=target_folder))
            media_url = getattr(media, "thumbnail_url", "")

        resolved_shortcode = getattr(media, "code", None)
        if not resolved_shortcode:
            match = re.search(r"/(?:p|reel)/([A-Za-z0-9_-]+)/?", post_url)
            resolved_shortcode = match.group(1) if match else "unknown"

        return {
            "media_url": media_url,
            "source_media_url": media_url,
            "local_path": local_path,
            "caption": getattr(media, "caption_text", None),
            "media_type": media_type,
            "shortcode": resolved_shortcode,
            "downloaded_at": datetime.now(UTC).isoformat(),
        }
