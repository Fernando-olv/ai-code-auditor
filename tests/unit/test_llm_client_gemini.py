import json
from pathlib import Path

import httpx
import pytest

from app.services.llm_client import GeminiGenerativeClient


def _gemini_response_json_text(text: str) -> dict:
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": text}]},
                "finishReason": "STOP",
            },
        ],
    }


@pytest.mark.asyncio
async def test_gemini_generative_client_complete_json() -> None:
    fixture = (
        Path(__file__).resolve().parents[1] / "fixtures" / "llm_outputs" / "valid_reviewer.json"
    )
    inner = fixture.read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "gemini-2.0-flash:generateContent" in str(request.url)
        assert request.url.params.get("key") == "secret-key"
        body = json.loads(request.content.decode("utf-8"))
        assert body["systemInstruction"]["parts"][0]["text"] == "sys"
        assert body["contents"][0]["parts"][0]["text"] == "user-payload"
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        return httpx.Response(200, json=_gemini_response_json_text(inner))

    transport = httpx.MockTransport(handler)
    client = GeminiGenerativeClient(
        "secret-key",
        model="gemini-2.0-flash",
        http_client=httpx.AsyncClient(transport=transport),
    )
    try:
        out = await client.complete_json(system="sys", user="user-payload")
        assert json.loads(out)["summary"]
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_gemini_client_strips_models_prefix_in_url() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=_gemini_response_json_text("{}"))

    transport = httpx.MockTransport(handler)
    client = GeminiGenerativeClient(
        "k",
        model="models/gemini-2.0-flash",
        use_json_mime_type=False,
        http_client=httpx.AsyncClient(transport=transport),
    )
    try:
        await client.complete_json(system="s", user="u")
        assert "models/gemini-2.0-flash:generateContent" in captured["url"]
        assert "models/models/" not in captured["url"]
    finally:
        await client.aclose()
