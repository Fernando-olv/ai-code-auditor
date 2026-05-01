"""Shared helpers for vendor HTTP adapters."""

from __future__ import annotations

import httpx


def raise_for_status_with_body(
    response: httpx.Response,
    *,
    provider: str,
) -> None:
    """``raise_for_status`` that surfaces a truncated response body in the message.

    The default httpx error swallows the body, which is the most actionable signal
    coming from LLM providers (quota, invalid key, model not found, safety block).
    Re-raising as ``ValueError`` makes the reviewer's blanket-catch path record a
    note like ``llm_parse_or_request_failed:ValueError:gemini HTTP 429: ...``.
    """

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        snippet = (response.text or "")[:500].replace("\n", " ")
        msg = f"{provider} HTTP {response.status_code}: {snippet}"
        raise ValueError(msg) from exc
