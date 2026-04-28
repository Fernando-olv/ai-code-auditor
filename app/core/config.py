"""Environment-backed settings."""

from typing import Literal

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

    llm_provider: Literal["openai", "gemini"] = "openai"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    llm_max_output_tokens: int = 2048
    llm_max_chars_per_file: int = 24_000
    llm_max_user_payload_chars: int = 120_000
    llm_json_response_format: bool = True

    google_cloud_project: str = ""
    firestore_database_id: str = ""

    @field_validator("llm_provider", mode="before")
    @classmethod
    def normalize_llm_provider(cls, value: object) -> str:
        if value is None or value == "":
            return "openai"
        if isinstance(value, str):
            return value.strip().lower()
        return str(value).strip().lower()

    @field_validator("github_webhook_secret", "github_token", "openai_api_key", "gemini_api_key")
    @classmethod
    def strip_secrets(cls, value: str) -> str:
        """Avoid newline/CRLF mismatches when secrets are piped from shells."""

        return value.strip()

    @field_validator("github_api_base_url", "openai_base_url")
    @classmethod
    def strip_trailing_slash_url(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("google_cloud_project", "firestore_database_id", "gemini_model")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()


def get_settings() -> Settings:
    """Return fresh settings so Secret Manager rotations take effect without stale cache."""

    return Settings()
