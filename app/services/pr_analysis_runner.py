"""End-to-end PR analysis: context, rules, LLM, score, Firestore, GitHub comment."""

from __future__ import annotations

import logging
import os
from time import perf_counter

from app.core.config import Settings, get_settings
from app.domain.pr_context import split_repository_full_name
from app.domain.webhooks import PullRequestEvent
from app.repositories.analysis_repository import AnalysisRepository
from app.services.analysis_merge import concat_findings
from app.services.analysis_persistence import persist_analysis_run
from app.services.feedback_service import (
    append_head_sha_marker,
    comment_body_includes_marker_for_sha,
    render_pr_feedback_markdown,
)
from app.services.github_client import GitHubRestClient
from app.services.llm_reviewer import LLM_RULE_PACK_VERSION_DEFAULT, run_llm_reviewer_from_settings
from app.services.pr_context_service import build_normalized_pr_context, github_client_from_settings
from app.services.rule_engine import default_rule_engine
from app.services.scoring_service import score_pr

logger = logging.getLogger(__name__)


def firestore_persistence_enabled(settings: Settings) -> bool:
    """True when Firestore client can be constructed for this process (project or emulator)."""

    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        return True
    return bool(settings.google_cloud_project.strip())


async def _comment_exists_for_head_sha(
    gh: GitHubRestClient,
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
) -> bool:
    comments = await gh.list_issue_comments(owner, repo, pr_number)
    for c in comments:
        if c.body and comment_body_includes_marker_for_sha(c.body, head_sha):
            return True
    return False


async def run_pr_analysis_for_pull_request(
    pr_event: PullRequestEvent,
    *,
    delivery: str = "",
) -> None:
    """Fetch PR, run engines, persist (optional), post markdown issue comment."""

    settings = get_settings()
    base_log: dict[str, object] = {
        "delivery": delivery,
        "repository": pr_event.repository_full_name,
        "pr_number": pr_event.pr_number,
        "action": pr_event.action,
    }

    if not settings.github_token.strip():
        logger.warning("pr_analysis_skipped_missing_github_token", extra=base_log)
        return

    gh: GitHubRestClient | None = None
    try:
        gh = github_client_from_settings(settings)
        t0 = perf_counter()
        ctx = await build_normalized_pr_context(gh, pr_event)
        rule_result = default_rule_engine().run(ctx)
        llm = await run_llm_reviewer_from_settings(ctx, settings)
        merged = concat_findings(rule_result.findings, llm.findings)
        score = score_pr(merged, ctx)
        latency_ms = int((perf_counter() - t0) * 1000)

        llm_pack_version = LLM_RULE_PACK_VERSION_DEFAULT if llm.status == "ok" else None

        if firestore_persistence_enabled(settings):
            try:
                repo = AnalysisRepository.from_settings(settings)
                await persist_analysis_run(
                    repo,
                    ctx=ctx,
                    findings=merged,
                    score=score,
                    rule_result=rule_result,
                    llm=llm,
                    llm_pack_version=llm_pack_version,
                    latency_ms=latency_ms,
                    error_message=None,
                )
            except Exception:
                logger.exception("pr_analysis_firestore_persist_failed", extra=base_log)
        else:
            logger.info("pr_analysis_firestore_skipped_not_configured", extra=base_log)

        markdown = render_pr_feedback_markdown(
            ctx=ctx,
            score=score,
            findings=merged,
            llm=llm,
            rule_pack_version=rule_result.rule_pack_version,
        )
        owner, repo = split_repository_full_name(pr_event.repository_full_name)

        if await _comment_exists_for_head_sha(gh, owner, repo, pr_event.pr_number, ctx.head_sha):
            logger.info(
                "pr_analysis_skip_duplicate_github_comment",
                extra={**base_log, "head_sha": ctx.head_sha},
            )
            return

        body = append_head_sha_marker(markdown, ctx.head_sha)
        await gh.create_issue_comment(owner, repo, pr_event.pr_number, body)
        logger.info(
            "pr_analysis_github_comment_posted",
            extra={**base_log, "head_sha": ctx.head_sha},
        )
    except Exception:
        logger.exception("pr_analysis_failed", extra=base_log)
    finally:
        if gh is not None:
            await gh.aclose()
