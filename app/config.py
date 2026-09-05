"""Application settings, loaded from environment variables or a local .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "mvp-budget-api"
    app_version: str = "1.0.0"

    # Secret shared with the subscription service. Always override in real runs.
    api_key: str = "budget-local-dev-key"

    database_url: str = "sqlite+aiosqlite:///./data/budget.db"

    # When unset (or unreachable) the service falls back to an in-process cache,
    # so a standalone `docker run` still works without Redis.
    redis_url: str | None = None
    cache_ttl_seconds: int = 900

    seed_on_startup: bool = False
    default_alert_threshold_pct: int = 80

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
