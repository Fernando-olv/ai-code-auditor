import json
from pathlib import Path

from app.domain.webhooks import PullRequestEvent
from app.services.webhook_service import parse_pull_request_event


def test_parse_pull_request_event_from_fixture() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "github_webhooks"
        / "pull_request_opened.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    event = parse_pull_request_event(payload)
    assert isinstance(event, PullRequestEvent)
    assert event.action == "opened"
    assert event.repository_full_name == "octo-org/octo-repo"
    assert event.pr_number == 42
    assert event.head_sha == "abc1234def5678"
    assert event.html_url == "https://github.com/octo-org/octo-repo/pull/42"
