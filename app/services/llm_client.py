"""LLM HTTP clients: OpenAI-compatible chat and Google Gemini (AI Studio) generateContent."""

from __future__ import annotations

import logging
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

GEMINI_GENERATE_CONTENT_BASE_DEFAULT = "https://generativelanguage.googleapis.com/v1beta"


def _gemini_model_id(model: str) -> str:
    """Strip optional ``models/`` prefix for REST path ``models/{id}:generateContent``."""

    m = model.strip()
    prefix = "models/"
    if m.startswith(prefix):
        return m[len(prefix) :]
    return m


class LlmClient(Protocol):
    """Minimal contract for an async text-in/text-out model call."""

    async def complete_json(self, *, system: str, user: str) -> str:
        """Return assistant message content (plain text, expected to be JSON)."""


class OpenAiCompatibleClient:
    """httpx-based client for `/v1/chat/completions`."""

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
        response.raise_for_status()
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


class GeminiGenerativeClient:
    """httpx client for Gemini ``:generateContent`` (Google AI Studio API key)."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gemini-2.0-flash",
        max_output_tokens: int = 2048,
        use_json_mime_type: bool = True,
        api_base: str = GEMINI_GENERATE_CONTENT_BASE_DEFAULT,
        timeout_seconds: float = 120.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._model = _gemini_model_id(model)
        self._max_output_tokens = max_output_tokens
        self._use_json_mime_type = use_json_mime_type
        self._api_base = api_base.rstrip("/")
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def complete_json(self, *, system: str, user: str) -> str:
        url = f"{self._api_base}/models/{self._model}:generateContent"
        params = {"key": self._api_key}
        gen_cfg: dict[str, Any] = {"maxOutputTokens": self._max_output_tokens}
        if self._use_json_mime_type:
            gen_cfg["responseMimeType"] = "application/json"
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": gen_cfg,
        }

        response = await self._client.post(url, params=params, json=body)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            msg = "Gemini response is not a JSON object"
            raise ValueError(msg)

        pfb = payload.get("promptFeedback")
        if isinstance(pfb, dict) and pfb.get("blockReason"):
            br = pfb.get("blockReason")
            msg = f"Gemini prompt blocked: {br}"
            raise ValueError(msg)

        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            msg = "Gemini response missing candidates"
            raise ValueError(msg)

        first = candidates[0]
        if not isinstance(first, dict):
            msg = "Gemini candidate is not an object"
            raise ValueError(msg)

        finish = first.get("finishReason")
        if finish in ("SAFETY", "RECITATION", "OTHER"):
            msg = f"Gemini finishReason: {finish}"
            raise ValueError(msg)

        content = first.get("content")
        if not isinstance(content, dict):
            msg = "Gemini content is not an object"
            raise ValueError(msg)
        parts = content.get("parts")
        if not isinstance(parts, list) or not parts:
            msg = "Gemini candidate has no parts"
            raise ValueError(msg)

        texts: list[str] = []
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                texts.append(part["text"])
        if not texts:
            msg = "Gemini candidate parts contain no text"
            raise ValueError(msg)

        text = "".join(texts)
        logger.debug(
            "llm_gemini_generate_ok",
            extra={"model": self._model, "chars": len(text)},
        )
        return text
