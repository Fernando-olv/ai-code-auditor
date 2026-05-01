"""Construct an :class:`LlmClient` from :class:`Settings`.

Centralizes vendor selection so callers (services, tests) depend only on the
port. Returns ``None`` when the selected provider has no API key configured,
which the reviewer turns into ``LlmReviewResult(status="skipped", ...)``.
"""

from __future__ import annotations

from app.core.config import Settings
from app.ports.llm_client import LlmClient
from app.vendor.gemini import GeminiGenerativeClient
from app.vendor.openai import OpenAiCompatibleClient


def build_llm_client(settings: Settings) -> tuple[LlmClient | None, str | None]:
    """Return ``(client, skip_reason)``. Exactly one of the two is non-None."""

    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            return None, (
                "gemini_api_key not configured (set GEMINI_API_KEY for LLM_PROVIDER=gemini)"
            )
        return (
            GeminiGenerativeClient(
                settings.gemini_api_key,
                model=settings.gemini_model,
                max_output_tokens=settings.llm_max_output_tokens,
                use_json_mime_type=settings.llm_json_response_format,
            ),
            None,
        )

    if not settings.openai_api_key:
        return None, "openai_api_key not configured (set OPENAI_API_KEY for LLM_PROVIDER=openai)"
    return (
        OpenAiCompatibleClient(
            settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.llm_model,
            max_output_tokens=settings.llm_max_output_tokens,
            use_json_response_format=settings.llm_json_response_format,
        ),
        None,
    )
