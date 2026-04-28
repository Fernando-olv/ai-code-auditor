import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from app.services.github_client import GitHubApiError, GitHubIssueComment, GitHubRestClient

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "github_api"


def _load_json(name: str) -> object:
    path = FIXTURES_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_get_pull_request_returns_typed_model() -> None:
    pull = _load_json("pull_42.json")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and str(request.url.path).endswith("/pulls/42"):
            return httpx.Response(200, json=pull)
        return httpx.Response(404, json={"message": "nope"})

    transport = httpx.MockTransport(handler)
    client = GitHubRestClient(
        "https://api.github.com",
        "test-token",
        transport=transport,
    )
    try:
        got = await client.get_pull_request("octo-org", "octo-repo", 42)
        assert got.number == 42
        assert got.title == "Add feature"
        assert got.head.sha == "abc1234def5678"
        assert got.head.ref == "feature-branch"
        assert got.base.sha == "base1112223334445"
        assert got.base.ref == "main"
        assert got.user_login == "octocat"
        assert got.html_url == "https://github.com/octo-org/octo-repo/pull/42"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_get_pull_request_404_raises() -> None:
    transport = httpx.MockTransport(
        lambda _r: httpx.Response(404, json={"message": "Not Found"}),
    )
    client = GitHubRestClient("https://api.github.com", "t", transport=transport)
    try:
        with pytest.raises(GitHubApiError) as excinfo:
            await client.get_pull_request("o", "r", 99)
        assert excinfo.value.status_code == 404
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_list_pull_request_files_paginates() -> None:
    files_p1 = [
        {
            "filename": "a.py",
            "status": "modified",
            "sha": "1",
            "additions": 1,
            "deletions": 0,
            "changes": 1,
            "patch": "@@\n+a\n",
        },
        {
            "filename": "b.py",
            "status": "modified",
            "sha": "2",
            "additions": 1,
            "deletions": 0,
            "changes": 1,
            "patch": "@@\n+b\n",
        },
    ]
    files_p2 = [
        {
            "filename": "c.py",
            "status": "added",
            "sha": "3",
            "additions": 1,
            "deletions": 0,
            "changes": 1,
            "patch": "@@\n+c\n",
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if not str(request.url.path).endswith("/files"):
            return httpx.Response(404)
        page = request.url.params.get("page") or "1"
        per = request.url.params.get("per_page") or "100"
        if per == "2" and page == "1":
            return httpx.Response(200, json=files_p1)
        if per == "2" and page == "2":
            return httpx.Response(200, json=files_p2)
        if per == "2" and page == "3":
            return httpx.Response(200, json=[])
        return httpx.Response(400, json={"message": f"unexpected {page=} {per=}"})

    transport = httpx.MockTransport(handler)
    client = GitHubRestClient("https://api.github.com", "t", transport=transport)
    try:
        all_files = await client.list_pull_request_files(
            "octo-org",
            "octo-repo",
            42,
            per_page=2,
        )
        assert [f.filename for f in all_files] == ["a.py", "b.py", "c.py"]
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_list_issue_comments_paginates() -> None:
    page1 = [{"id": 1, "body": "a"}, {"id": 2, "body": "b"}]
    page2 = [{"id": 3, "body": "c"}]

    def handler(request: httpx.Request) -> httpx.Response:
        if not str(request.url.path).endswith("/issues/42/comments"):
            return httpx.Response(404)
        per = request.url.params.get("per_page")
        page = request.url.params.get("page", "1")
        if per == "2" and page == "1":
            return httpx.Response(200, json=page1)
        if per == "2" and page == "2":
            return httpx.Response(200, json=page2)
        if per == "2" and page == "3":
            return httpx.Response(200, json=[])
        return httpx.Response(400)

    transport = httpx.MockTransport(handler)
    client = GitHubRestClient("https://api.github.com", "t", transport=transport)
    try:
        got = await client.list_issue_comments("o", "r", 42, per_page=2)
        assert [c.id for c in got] == [1, 2, 3]
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_create_issue_comment_returns_model() -> None:
    created = {"id": 99, "body": "hello"}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url.path).endswith("/issues/5/comments"):
            return httpx.Response(201, json=created)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = GitHubRestClient("https://api.github.com", "t", transport=transport)
    try:
        got = await client.create_issue_comment("o", "r", 5, "hello")
        assert isinstance(got, GitHubIssueComment)
        assert got.id == 99
        assert got.body == "hello"
    finally:
        await client.aclose()


def test_github_rest_client_rejects_http_client_and_transport() -> None:
    dummy = httpx.MockTransport(lambda _r: httpx.Response(200, json={}))
    with pytest.raises(ValueError, match="at most one"):
        GitHubRestClient(
            "https://api.github.com",
            "t",
            http_client=MagicMock(),
            transport=dummy,
        )
