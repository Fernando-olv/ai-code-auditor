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

    @field_validator("github_webhook_secret")
    @classmethod
    def strip_github_webhook_secret(cls, value: str) -> str:
        """Avoid newline/CRLF mismatches when secrets are piped from shells."""

        return value.strip()


def get_settings() -> Settings:
    """Return fresh settings so Secret Manager rotations take effect without stale cache."""

    return Settings()
