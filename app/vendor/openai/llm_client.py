"""OpenAI-compatible chat-completions adapter implementing :class:`LlmClient`."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.vendor._http import raise_for_status_with_body

logger = logging.getLogger(__name__)


class OpenAiCompatibleClient:
    """httpx-based client for ``/v1/chat/completions``.

    Works with OpenAI itself and with API-compatible servers (Azure OpenAI, vLLM,
    Together, Groq, etc.) by overriding ``base_url`` and ``model``.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        max_output_tokens: int = 2048,
        use_json_response_format: bool = True,
        timeout_seconds: float = 120.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._use_json_response_format = use_json_response_format
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def complete_json(self, *, system: str, user: str) -> str:
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": self._max_output_tokens,
        }
        if self._use_json_response_format:
            body["response_format"] = {"type": "json_object"}

        response = await self._client.post(url, headers=headers, json=body)
        raise_for_status_with_body(response, provider="openai")
        payload = response.json()
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            msg = "OpenAI response missing choices"
            raise ValueError(msg)
        first = choices[0]
        if not isinstance(first, dict):
            msg = "OpenAI choice is not an object"
            raise ValueError(msg)
        message = first.get("message")
        if not isinstance(message, dict):
            msg = "OpenAI message is not an object"
            raise ValueError(msg)
        content = message.get("content")
        if not isinstance(content, str):
            msg = "OpenAI message content is not a string"
            raise ValueError(msg)
        logger.debug(
            "llm_chat_completion_ok",
            extra={"model": self._model, "chars": len(content)},
        )
        return content
