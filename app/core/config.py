"""Application settings loaded from the environment / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. DATABASE_URL is required."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RestApiCoba"
    app_env: str = "local"
    debug: bool = False

    database_url: str

    default_object_id: int | None = None
    default_page_size: int = 20
    max_page_size: int = 100

    api_prefix: str = "/api/v1"

    log_dir: str = "logs"
    log_sql: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
