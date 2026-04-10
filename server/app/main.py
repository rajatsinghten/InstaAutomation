from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.analysis import router as analysis_router
from app.api.v1.auth import router as auth_router
from app.api.v1.followers import router as followers_router
from app.api.v1.health import router as health_router
from app.api.v1.posts import router as posts_router
from app.config import get_settings
from app.database.db import init_db
from app.middleware.error_handler import register_exception_handlers
from app.middleware.rate_limit import limiter
from app.services.auth_service import AuthService
from app.services.cache_service import CacheService
from app.services.follower_service import FollowerService
from app.services.post_service import PostService
from app.services.session_manager import SessionManager
from app.utils.logger import configure_logging

settings = get_settings()
SERVER_ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS_ROOT = (SERVER_ROOT / settings.downloads_dir).resolve()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    DOWNLOADS_ROOT.mkdir(parents=True, exist_ok=True)

    cache_service = CacheService(settings.redis_url)
    await cache_service.startup()

    session_manager = SessionManager(
        cache_service=cache_service,
        ttl_seconds=settings.session_ttl_seconds,
    )

    auth_service = AuthService(settings=settings, session_manager=session_manager)
    follower_service = FollowerService(
        settings=settings,
        session_manager=session_manager,
        cache_service=cache_service,
    )
    post_service = PostService(
        session_manager=session_manager,
        downloads_root=DOWNLOADS_ROOT,
    )

    app.state.settings = settings
    app.state.cache_service = cache_service
    app.state.session_manager = session_manager
    app.state.auth_service = auth_service
    app.state.follower_service = follower_service
    app.state.post_service = post_service

    await init_db()
    yield
    await cache_service.shutdown()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = sorted(set(settings.cors_origins + [settings.frontend_url]))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)
app.mount(
    "/downloads",
    StaticFiles(directory=DOWNLOADS_ROOT, check_dir=False),
    name="downloads",
)

register_exception_handlers(app)

app.include_router(health_router, prefix=f"{settings.api_v1_prefix}/health", tags=["health"])
app.include_router(auth_router, prefix=f"{settings.api_v1_prefix}/auth", tags=["auth"])
app.include_router(
    followers_router,
    prefix=f"{settings.api_v1_prefix}/followers",
    tags=["followers"],
)
app.include_router(analysis_router, prefix=f"{settings.api_v1_prefix}/analysis", tags=["analysis"])
app.include_router(posts_router, prefix=f"{settings.api_v1_prefix}/posts", tags=["posts"])
