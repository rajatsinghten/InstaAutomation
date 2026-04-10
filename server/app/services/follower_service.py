from datetime import UTC, datetime

from app.config import Settings
from app.models.schemas import AnalysisResponse, FollowerResponse
from app.services.cache_service import CacheService
from app.services.session_manager import SessionManager


class FollowerService:
    def __init__(
        self,
        settings: Settings,
        session_manager: SessionManager,
        cache_service: CacheService,
    ):
        self.settings = settings
        self.session_manager = session_manager
        self.cache_service = cache_service

    def _followers_key(self, session_id: str) -> str:
        return f"followers:{session_id}"

    def _following_key(self, session_id: str) -> str:
        return f"following:{session_id}"

    @staticmethod
    def _as_profile(username: str) -> FollowerResponse:
        return FollowerResponse(
            username=username,
            full_name=username.replace(".", " ").title(),
            profile_pic_url=f"https://cdn.example.com/profiles/{username}.jpg",
            is_verified=False,
        )

    async def list_followers(self, session_id: str, refresh: bool = False) -> list[FollowerResponse]:
        await self.session_manager.get_session(session_id)
        key = self._followers_key(session_id)

        if not refresh:
            cached = await self.cache_service.get(key)
            if cached is not None:
                return [self._as_profile(name) for name in cached]

        client = await self.session_manager.get_client(session_id)
        followers = await client.get_followers()
        await self.cache_service.set(key, followers, self.settings.follower_cache_ttl_seconds)
        return [self._as_profile(name) for name in followers]

    async def list_following(self, session_id: str, refresh: bool = False) -> list[FollowerResponse]:
        await self.session_manager.get_session(session_id)
        key = self._following_key(session_id)

        if not refresh:
            cached = await self.cache_service.get(key)
            if cached is not None:
                return [self._as_profile(name) for name in cached]

        client = await self.session_manager.get_client(session_id)
        following = await client.get_following()
        await self.cache_service.set(key, following, self.settings.follower_cache_ttl_seconds)
        return [self._as_profile(name) for name in following]

    async def get_unfollowers(self, session_id: str, refresh: bool = False) -> list[FollowerResponse]:
        followers = await self.list_followers(session_id, refresh=refresh)
        following = await self.list_following(session_id, refresh=refresh)

        follower_usernames = {item.username for item in followers}
        following_usernames = {item.username for item in following}
        diff = sorted(follower_usernames - following_usernames)
        return [self._as_profile(name) for name in diff]

    async def get_not_following_back(
        self, session_id: str, refresh: bool = False
    ) -> list[FollowerResponse]:
        followers = await self.list_followers(session_id, refresh=refresh)
        following = await self.list_following(session_id, refresh=refresh)

        follower_usernames = {item.username for item in followers}
        following_usernames = {item.username for item in following}
        diff = sorted(following_usernames - follower_usernames)
        return [self._as_profile(name) for name in diff]

    async def get_mutual(self, session_id: str, refresh: bool = False) -> list[FollowerResponse]:
        followers = await self.list_followers(session_id, refresh=refresh)
        following = await self.list_following(session_id, refresh=refresh)

        follower_usernames = {item.username for item in followers}
        following_usernames = {item.username for item in following}
        mutual = sorted(follower_usernames.intersection(following_usernames))
        return [self._as_profile(name) for name in mutual]

    async def get_stats(self, session_id: str, refresh: bool = False) -> AnalysisResponse:
        followers = await self.list_followers(session_id, refresh=refresh)
        following = await self.list_following(session_id, refresh=refresh)
        unfollowers = await self.get_unfollowers(session_id, refresh=refresh)
        not_following_back = await self.get_not_following_back(session_id, refresh=refresh)
        mutual = await self.get_mutual(session_id, refresh=refresh)

        total_followers = len(followers)
        engagement_rate = 0.0
        if total_followers > 0:
            engagement_rate = round((len(mutual) / total_followers) * 100, 2)

        return AnalysisResponse(
            total_followers=total_followers,
            total_following=len(following),
            unfollowers=len(unfollowers),
            not_following_back=len(not_following_back),
            mutual_followers=len(mutual),
            engagement_rate=engagement_rate,
            fetched_at=datetime.now(UTC),
        )
