from datetime import datetime
from pathlib import Path

from app.exceptions.custom_exceptions import PostDownloadError
from app.models.enums import MediaType
from app.models.schemas import PostDownloadResponse
from app.services.session_manager import SessionManager
from app.utils.validators import is_valid_instagram_post_url


class PostService:
    def __init__(self, session_manager: SessionManager, downloads_root: Path):
        self.session_manager = session_manager
        self.downloads_root = downloads_root.resolve()

    def _to_public_download_url(self, local_path: str) -> str:
        path = Path(local_path).resolve()
        try:
            relative = path.relative_to(self.downloads_root)
        except ValueError as exc:
            raise PostDownloadError("Downloaded media path is outside of storage root") from exc
        return f"/downloads/{relative.as_posix()}"

    async def download_post(self, session_id: str, post_url: str) -> PostDownloadResponse:
        if not is_valid_instagram_post_url(post_url):
            raise PostDownloadError("Invalid Instagram post or reel URL")

        client = await self.session_manager.get_client(session_id)
        session_download_dir = self.downloads_root / session_id
        session_download_dir.mkdir(parents=True, exist_ok=True)
        payload = await client.download_post(
            post_url,
            download_dir=str(session_download_dir),
        )

        media_type_value = payload.get("media_type", MediaType.image.value)
        local_path = payload.get("local_path")

        media_url = payload.get("media_url", "")
        if local_path:
            media_url = self._to_public_download_url(local_path)
        if not media_url:
            raise PostDownloadError("No downloadable media URL was returned")

        return PostDownloadResponse(
            media_url=media_url,
            source_media_url=payload.get("source_media_url"),
            caption=payload.get("caption"),
            media_type=MediaType(media_type_value),
            shortcode=payload["shortcode"],
            downloaded_at=datetime.fromisoformat(payload["downloaded_at"]),
        )
