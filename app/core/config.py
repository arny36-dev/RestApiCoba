"""Application settings loaded from the environment / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. DATABASE_URL and ALLOWED_TABLES are required."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Generic CRUD API"
    app_env: str = "local"
    debug: bool = False

    database_url: str
    allowed_tables: str

    default_page_size: int = 20
    max_page_size: int = 100

    api_prefix: str = "/api/v1"

    @property
    def allowed_tables_list(self) -> list[str]:
        """ALLOWED_TABLES parsed as an ordered, whitespace-trimmed whitelist."""
        return [name.strip() for name in self.allowed_tables.split(",") if name.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
