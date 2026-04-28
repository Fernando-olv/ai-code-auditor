"""Thin service wrapper for deterministic PR scoring."""

from __future__ import annotations

from app.domain.findings import Finding
from app.domain.pr_context import NormalizedPrContext
from app.domain.scoring import PrScoreResult, ScoringConfig, compute_pr_score


def default_scoring_config() -> ScoringConfig:
    """Built-in MVP scoring policy."""

    return ScoringConfig()


def score_pr(
    findings: list[Finding],
    ctx: NormalizedPrContext | None = None,
    config: ScoringConfig | None = None,
) -> PrScoreResult:
    """Compute deterministic PR score from merged findings."""

    return compute_pr_score(findings, ctx, config or default_scoring_config())
