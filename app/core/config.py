"""Environment-backed settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment (optional `.env`)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    github_webhook_secret: str = ""
    github_token: str = ""
    github_api_base_url: str = "https://api.github.com"

    @field_validator("github_webhook_secret", "github_token")
    @classmethod
    def strip_secrets(cls, value: str) -> str:
        """Avoid newline/CRLF mismatches when secrets are piped from shells."""

        return value.strip()

    @field_validator("github_api_base_url")
    @classmethod
    def strip_trailing_slash_github_api_base_url(cls, value: str) -> str:
        return value.rstrip("/")


def get_settings() -> Settings:
    """Return fresh settings so Secret Manager rotations take effect without stale cache."""

    return Settings()
