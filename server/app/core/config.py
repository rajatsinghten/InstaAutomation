import os


class Settings:
    api_title = "Instagram Automation API"
    api_version = "1.0.0"
    jwt_secret_key = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    jwt_algorithm = "HS256"
    access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    # Keep requests modest to avoid Instagram anti-abuse limits.
    engagement_max_posts = int(os.getenv("ENGAGEMENT_MAX_POSTS", "12"))
    followers_export_max_items = int(os.getenv("FOLLOWERS_EXPORT_MAX_ITEMS", "200"))
    instagram_rate_limit_cooldown_minutes = int(os.getenv("IG_RATE_LIMIT_COOLDOWN_MINUTES", "180"))
    engagement_cache_ttl_seconds = int(os.getenv("ENGAGEMENT_CACHE_TTL_SECONDS", "900"))
    followers_cache_ttl_seconds = int(os.getenv("FOLLOWERS_CACHE_TTL_SECONDS", "1800"))
    profile_pic_cache_ttl_seconds = int(os.getenv("PROFILE_PIC_CACHE_TTL_SECONDS", "900"))
    rate_limit_min_delay_seconds = float(os.getenv("RATE_LIMIT_MIN_DELAY_SECONDS", "2"))
    rate_limit_max_delay_seconds = float(os.getenv("RATE_LIMIT_MAX_DELAY_SECONDS", "60"))
    rate_limit_backoff_cap = float(os.getenv("RATE_LIMIT_BACKOFF_CAP", "10"))


settings = Settings()
