from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Git Analytics"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./git_analytics.db"

    github_client_id: str | None = None
    github_client_secret: str | None = None
    github_callback_url: str = "http://localhost:8000/auth/github/callback"
    secret_key: str = Field(default="change-me-in-local-env")
    encryption_key: str | None = None

    session_cookie_name: str = "git_analytics_session"
    oauth_state_cookie_name: str = "git_analytics_oauth_state"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
