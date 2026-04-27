"""Build normalized PR analysis context from webhook identity + GitHub API."""

from __future__ import annotations

import logging

import httpx

from app.core.config import Settings
from app.domain.pr_context import (
    FileFilterConfig,
    NormalizedPrContext,
    filter_pull_files,
    split_repository_full_name,
)
from app.domain.webhooks import PullRequestEvent
from app.services.github_client import GitHubRestClient

logger = logging.getLogger(__name__)


def github_client_from_settings(
    settings: Settings,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> GitHubRestClient:
    """Construct a GitHub REST client from app settings."""

    if not settings.github_token:
        msg = "GITHUB_TOKEN is not configured"
        raise ValueError(msg)
    return GitHubRestClient(
        settings.github_api_base_url,
        settings.github_token,
        http_client=http_client,
    )


async def build_normalized_pr_context(
    client: GitHubRestClient,
    event: PullRequestEvent,
    *,
    file_filter_config: FileFilterConfig | None = None,
) -> NormalizedPrContext:
    """Fetch PR metadata and files, then normalize and filter for analysis."""

    owner, repo = split_repository_full_name(event.repository_full_name)

    pull = await client.get_pull_request(owner, repo, event.pr_number)
    raw_files = await client.list_pull_request_files(owner, repo, event.pr_number)

    truncation_notes: list[str] = []
    partial = False

    if pull.head.sha != event.head_sha:
        partial = True
        note = f"stale_head_sha:webhook={event.head_sha[:7]} api={pull.head.sha[:7]}"
        truncation_notes.append(note)
        logger.warning(
            "pr_context_head_sha_mismatch",
            extra={
                "repository": event.repository_full_name,
                "pr_number": event.pr_number,
                "webhook_head_sha": event.head_sha,
                "api_head_sha": pull.head.sha,
            },
        )

    filtered_files, filter_notes = filter_pull_files(raw_files, config=file_filter_config)
    truncation_notes.extend(filter_notes)

    if filter_notes:
        partial = partial or any(n.startswith("truncated_") for n in filter_notes)

    return NormalizedPrContext(
        repository_full_name=event.repository_full_name,
        pr_number=event.pr_number,
        head_sha=pull.head.sha,
        base_sha=pull.base.sha,
        head_ref=pull.head.ref,
        base_ref=pull.base.ref,
        title=pull.title,
        html_url=pull.html_url or event.html_url,
        author_login=pull.user_login,
        body=pull.body,
        files=filtered_files,
        partial_context=partial,
        truncation_notes=truncation_notes,
    )
