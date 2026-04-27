"""Async GitHub REST API client for pull request metadata and changed files."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

GITHUB_ACCEPT = "application/vnd.github+json"
GITHUB_API_VERSION = "2022-11-28"
DEFAULT_USER_AGENT = "ai-dev-auditor/0.1.0"


class GitHubApiError(Exception):
    """Raised when the GitHub API returns an unexpected or error response."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubRef(BaseModel):
    """Head or base ref on a pull request."""

    sha: str
    ref: str = ""


class GitHubPullResponse(BaseModel):
    """Subset of `GET /repos/{owner}/{repo}/pulls/{pull_number}` used for analysis."""

    number: int
    title: str = ""
    html_url: str | None = None
    body: str | None = None
    head: GitHubRef
    base: GitHubRef
    user_login: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> GitHubPullResponse:
        head = data["head"]
        base = data["base"]
        user = data.get("user") or {}
        return cls(
            number=data["number"],
            title=data.get("title") or "",
            html_url=data.get("html_url"),
            body=data.get("body"),
            head=GitHubRef(sha=head["sha"], ref=head.get("ref") or ""),
            base=GitHubRef(sha=base["sha"], ref=base.get("ref") or ""),
            user_login=user.get("login"),
        )


class GitHubPullFile(BaseModel):
    """One row from `GET .../pulls/{pull_number}/files`."""

    filename: str
    status: str
    sha: str
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: str | None = None

    @classmethod
    def from_api(cls, row: dict[str, Any]) -> GitHubPullFile:
        return cls(
            filename=row["filename"],
            status=row["status"],
            sha=row["sha"],
            additions=int(row.get("additions") or 0),
            deletions=int(row.get("deletions") or 0),
            changes=int(row.get("changes") or 0),
            patch=row.get("patch"),
        )


class GitHubRestClient:
    """Thin httpx wrapper around pull request endpoints."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        transport: httpx.BaseTransport | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_seconds: float = 30.0,
    ) -> None:
        if http_client is not None and transport is not None:
            msg = "Pass at most one of http_client and transport"
            raise ValueError(msg)

        self._owns_client = http_client is None
        headers: dict[str, str] = {
            "Accept": GITHUB_ACCEPT,
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": user_agent,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        if http_client is not None:
            self._client = http_client
        else:
            client_kwargs: dict[str, Any] = {
                "base_url": base_url,
                "headers": headers,
                "timeout": timeout_seconds,
            }
            if transport is not None:
                client_kwargs["transport"] = transport
            self._client = httpx.AsyncClient(**client_kwargs)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_pull_request(self, owner: str, repo: str, pull_number: int) -> GitHubPullResponse:
        path = f"/repos/{owner}/{repo}/pulls/{pull_number}"
        response = await self._client.get(path)
        if response.status_code == 404:
            raise GitHubApiError(
                f"Pull request not found: {owner}/{repo}#{pull_number}",
                status_code=404,
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubApiError(
                f"GitHub API error for {path}: {exc.response.status_code}",
                status_code=exc.response.status_code,
            ) from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise GitHubApiError("GitHub API returned non-object JSON for pull request")
        return GitHubPullResponse.from_api(payload)

    async def list_pull_request_files(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        *,
        per_page: int = 100,
    ) -> list[GitHubPullFile]:
        """Fetch all changed-file rows, following GitHub pagination."""

        if per_page > 100:
            per_page = 100

        all_files: list[GitHubPullFile] = []
        page = 1
        path = f"/repos/{owner}/{repo}/pulls/{pull_number}/files"

        while True:
            response = await self._client.get(
                path,
                params={"per_page": per_page, "page": page},
            )
            if response.status_code == 404:
                raise GitHubApiError(
                    f"Pull request files not found: {owner}/{repo}#{pull_number}",
                    status_code=404,
                )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise GitHubApiError(
                    f"GitHub API error for {path}: {exc.response.status_code}",
                    status_code=exc.response.status_code,
                ) from exc

            batch = response.json()
            if not isinstance(batch, list):
                raise GitHubApiError("GitHub API returned non-array JSON for pull files")

            if len(batch) == 0:
                break

            for row in batch:
                if not isinstance(row, dict):
                    raise GitHubApiError("GitHub API returned non-object file row")
                all_files.append(GitHubPullFile.from_api(row))

            if len(batch) < per_page:
                break
            page += 1

        logger.debug(
            "github_list_pull_files",
            extra={
                "owner": owner,
                "repo": repo,
                "pull_number": pull_number,
                "file_count": len(all_files),
            },
        )
        return all_files
