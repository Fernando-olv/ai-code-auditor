import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings
from app.domain.webhooks import PullRequestEvent
from app.services.github_client import GitHubRestClient
from app.services.pr_context_service import (
    build_normalized_pr_context,
    github_client_from_settings,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "github_api"


def _handler_for_pull_and_files(
    pull: object,
    files: object,
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        path = str(request.url.path)
        if path.endswith("/pulls/42") and not path.endswith("/files"):
            return httpx.Response(200, json=pull)
        if path.endswith("/files"):
            return httpx.Response(200, json=files)
        return httpx.Response(404, json={"message": "not found", "path": path})

    return handler


@pytest.mark.asyncio
async def test_build_normalized_pr_context_happy_path() -> None:
    pull = json.loads((FIXTURES_DIR / "pull_42.json").read_text(encoding="utf-8"))
    files = json.loads((FIXTURES_DIR / "files_mixed.json").read_text(encoding="utf-8"))
    transport = httpx.MockTransport(_handler_for_pull_and_files(pull, files))
    client = GitHubRestClient("https://api.github.com", "tok", transport=transport)
    event = PullRequestEvent(
        action="opened",
        repository_full_name="octo-org/octo-repo",
        pr_number=42,
        head_sha="abc1234def5678",
        html_url="https://github.com/octo-org/octo-repo/pull/42",
    )
    try:
        ctx = await build_normalized_pr_context(client, event)
        assert ctx.repository_full_name == "octo-org/octo-repo"
        assert ctx.pr_number == 42
        assert ctx.head_sha == "abc1234def5678"
        assert ctx.base_sha == "base1112223334445"
        assert ctx.title == "Add feature"
        assert ctx.author_login == "octocat"
        assert not ctx.partial_context
        assert [f.path for f in ctx.files] == ["src/app.py"]
        assert any("skipped_no_patch" in n for n in ctx.truncation_notes)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_build_normalized_pr_context_stale_head_marks_partial() -> None:
    pull = json.loads((FIXTURES_DIR / "pull_42.json").read_text(encoding="utf-8"))
    files = json.loads((FIXTURES_DIR / "files_mixed.json").read_text(encoding="utf-8"))
    transport = httpx.MockTransport(_handler_for_pull_and_files(pull, files))
    client = GitHubRestClient("https://api.github.com", "tok", transport=transport)
    event = PullRequestEvent(
        action="synchronize",
        repository_full_name="octo-org/octo-repo",
        pr_number=42,
        head_sha="deadbeef0000000",
    )
    try:
        ctx = await build_normalized_pr_context(client, event)
        assert ctx.partial_context
        assert any("stale_head_sha" in n for n in ctx.truncation_notes)
        assert ctx.head_sha == "abc1234def5678"
    finally:
        await client.aclose()


def test_github_client_from_settings_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "")
    settings = Settings()
    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        github_client_from_settings(settings)
