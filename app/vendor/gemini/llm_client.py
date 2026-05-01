"""Google AI Studio Gemini ``generateContent`` adapter implementing :class:`LlmClient`."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.vendor._http import raise_for_status_with_body

logger = logging.getLogger(__name__)

GEMINI_GENERATE_CONTENT_BASE_DEFAULT = "https://generativelanguage.googleapis.com/v1beta"


def _gemini_model_id(model: str) -> str:
    """Strip optional ``models/`` prefix for REST path ``models/{id}:generateContent``."""

    m = model.strip()
    prefix = "models/"
    if m.startswith(prefix):
        return m[len(prefix) :]
    return m


class GeminiGenerativeClient:
    """httpx client for Gemini ``:generateContent`` (Google AI Studio API key)."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gemini-2.5-flash-lite",
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
        raise_for_status_with_body(response, provider="gemini")
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
