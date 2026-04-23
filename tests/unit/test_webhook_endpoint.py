import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from main import app


def _signature_256(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.fixture
def webhook_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "test_webhook_secret"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    get_settings.cache_clear()
    return secret


@pytest.fixture
async def client(webhook_secret: str) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _fixture_bytes(name: str) -> bytes:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "github_webhooks" / name
    return fixture_path.read_bytes()


@pytest.mark.asyncio
async def test_webhook_ping_accepts_valid_signature(
    client: AsyncClient, webhook_secret: str
) -> None:
    body = _fixture_bytes("ping.json")
    headers = {
        "X-GitHub-Event": "ping",
        "X-GitHub-Delivery": "delivery-1",
        "X-Hub-Signature-256": _signature_256(body, webhook_secret),
    }

    response = await client.post("/webhooks/github", content=body, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_webhook_pull_request_accepts_valid_signature(
    client: AsyncClient, webhook_secret: str
) -> None:
    body = _fixture_bytes("pull_request_opened.json")
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "delivery-2",
        "X-Hub-Signature-256": _signature_256(body, webhook_secret),
    }

    response = await client.post("/webhooks/github", content=body, headers=headers)
    assert response.status_code == 202
    assert response.json() == {"accepted": True}


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(client: AsyncClient, webhook_secret: str) -> None:
    body = json.dumps({"hello": "world"}).encode("utf-8")
    headers = {
        "X-GitHub-Event": "ping",
        "X-Hub-Signature-256": "sha256=deadbeef",
    }
    response = await client.post("/webhooks/github", content=body, headers=headers)
    assert response.status_code == 401
