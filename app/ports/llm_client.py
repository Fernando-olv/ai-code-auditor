"""LLM port: minimal contract for an async text-in / JSON-text-out model call."""

from __future__ import annotations

from typing import Protocol


class LlmClient(Protocol):
    """Contract every vendor adapter (OpenAI, Gemini, ...) must satisfy."""

    async def complete_json(self, *, system: str, user: str) -> str:
        """Return assistant message content (plain text, expected to be JSON)."""

    async def aclose(self) -> None:
        """Release any owned HTTP resources. Idempotent."""
