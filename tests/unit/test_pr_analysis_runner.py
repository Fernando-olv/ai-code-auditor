from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.domain.findings import RuleEngineResult
from app.domain.pr_context import NormalizedPrContext
from app.domain.webhooks import PullRequestEvent
from app.services import pr_analysis_runner as runner
from app.services import store_factory
from app.services.feedback_service import append_head_sha_marker
from app.services.github_client import GitHubIssueComment
from app.services.llm_reviewer import LlmReviewResult


def test_persistence_enabled_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    s = Settings(google_cloud_project="my-proj")
    assert store_factory.persistence_enabled(s) is True


def test_persistence_enabled_emulator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
    s = Settings(google_cloud_project="")
    assert store_factory.persistence_enabled(s) is True


def test_persistence_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    s = Settings(google_cloud_project="")
    assert store_factory.persistence_enabled(s) is False


@pytest.mark.asyncio
async def test_run_pr_analysis_skips_without_github_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: Settings(github_token="", github_webhook_secret="x"),
    )
    ev = PullRequestEvent(
        action="opened",
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
    )
    await runner.run_pr_analysis_for_pull_request(ev, delivery="d1")


@pytest.mark.asyncio
async def test_run_pr_analysis_posts_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="c" * 40,
        base_sha="d" * 40,
    )

    async def fake_build(_client: object, _event: PullRequestEvent) -> NormalizedPrContext:
        return ctx

    rule_result = RuleEngineResult(rule_pack_version="v0_1_0", findings=[], engine_notes=[])

    class FakeEngine:
        def run(self, _ctx: NormalizedPrContext) -> RuleEngineResult:
            return rule_result

    mock_gh = MagicMock()
    mock_gh.list_issue_comments = AsyncMock(return_value=[])
    mock_gh.create_issue_comment = AsyncMock(
        return_value=GitHubIssueComment(id=1, body="x"),
    )
    mock_gh.aclose = AsyncMock()

    async def fake_llm(_c: NormalizedPrContext, _s: Settings) -> LlmReviewResult:
        return LlmReviewResult(status="skipped", findings=[], notes=[])

    monkeypatch.setattr(runner, "github_client_from_settings", lambda _s: mock_gh)
    monkeypatch.setattr(runner, "build_normalized_pr_context", fake_build)
    monkeypatch.setattr(runner, "default_rule_engine", lambda: FakeEngine())
    monkeypatch.setattr(runner, "run_llm_reviewer_from_settings", fake_llm)
    monkeypatch.setattr(runner, "build_analysis_store", lambda _s: None)
    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: Settings(
            github_token="tok",
            github_webhook_secret="x",
            github_api_base_url="https://api.github.com",
        ),
    )

    ev = PullRequestEvent(
        action="opened",
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
    )
    await runner.run_pr_analysis_for_pull_request(ev, delivery="d2")

    mock_gh.create_issue_comment.assert_awaited_once()
    call_kw = mock_gh.create_issue_comment.await_args
    assert call_kw[0][0] == "o"
    assert call_kw[0][1] == "r"
    assert call_kw[0][2] == 1
    assert "AI Dev Auditor" in call_kw[0][3]


@pytest.mark.asyncio
async def test_run_pr_analysis_skips_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="c" * 40,
        base_sha="d" * 40,
    )

    async def fake_build(_client: object, _event: PullRequestEvent) -> NormalizedPrContext:
        return ctx

    rule_result = RuleEngineResult(rule_pack_version="v0_1_0", findings=[], engine_notes=[])

    class FakeEngine:
        def run(self, _ctx: NormalizedPrContext) -> RuleEngineResult:
            return rule_result

    existing_body = append_head_sha_marker("old", ctx.head_sha)
    mock_gh = MagicMock()
    mock_gh.list_issue_comments = AsyncMock(
        return_value=[GitHubIssueComment(id=1, body=existing_body)],
    )
    mock_gh.create_issue_comment = AsyncMock()
    mock_gh.aclose = AsyncMock()

    async def fake_llm(_c: NormalizedPrContext, _s: Settings) -> LlmReviewResult:
        return LlmReviewResult(status="skipped", findings=[], notes=[])

    monkeypatch.setattr(runner, "github_client_from_settings", lambda _s: mock_gh)
    monkeypatch.setattr(runner, "build_normalized_pr_context", fake_build)
    monkeypatch.setattr(runner, "default_rule_engine", lambda: FakeEngine())
    monkeypatch.setattr(runner, "run_llm_reviewer_from_settings", fake_llm)
    monkeypatch.setattr(runner, "build_analysis_store", lambda _s: None)
    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: Settings(
            github_token="tok",
            github_webhook_secret="x",
            github_api_base_url="https://api.github.com",
        ),
    )

    ev = PullRequestEvent(
        action="opened",
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
    )
    await runner.run_pr_analysis_for_pull_request(ev)

    mock_gh.create_issue_comment.assert_not_called()
