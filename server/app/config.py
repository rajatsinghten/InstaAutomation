from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Instagram Automation API"
    app_version: str = "1.0.0"
    fastapi_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite+aiosqlite:///./instagram.db"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "please-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )

    rate_limit_requests: int = 100
    rate_limit_period: int = 3600

    headless_mode: bool = True
    follower_cache_ttl_seconds: int = 21600
    session_ttl_seconds: int = 86400
    enable_real_instagram_login: bool = True
    downloads_dir: str = "downloads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def normalized_database_url(self) -> str:
        if self.database_url.startswith("sqlite:///"):
            return self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        return self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
