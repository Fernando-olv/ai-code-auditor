from app.domain.findings import Finding, Severity
from app.domain.pr_context import NormalizedPrContext
from app.domain.scoring import PrScoreResult, Subscores
from app.services.feedback_service import (
    append_head_sha_marker,
    comment_body_includes_marker_for_sha,
    head_sha_comment_marker,
    render_pr_feedback_markdown,
)
from app.services.llm_reviewer import LlmReviewResult


def _ctx() -> NormalizedPrContext:
    return NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=3,
        head_sha="a" * 40,
        base_sha="b" * 40,
        partial_context=False,
    )


def _score() -> PrScoreResult:
    return PrScoreResult(
        final_score=82,
        subscores=Subscores(
            maintainability=80,
            correctness_confidence=85,
            testing=78,
            security=90,
            readability=80,
        ),
        explanation=["line one", "line two"],
        scoring_policy_version="score_v0_1_0",
        notes=[],
    )


def test_head_sha_marker_roundtrip() -> None:
    sha = "abc123" * 6 + "abcdef"  # 40
    m = head_sha_comment_marker(sha)
    assert comment_body_includes_marker_for_sha("intro\n" + m, sha)


def test_append_head_sha_marker_truncates_long_body() -> None:
    sha = "d" * 40
    huge = "x" * 100_000
    out = append_head_sha_marker(huge, sha)
    assert len(out) <= 60_500
    assert comment_body_includes_marker_for_sha(out, sha)


def test_render_pr_feedback_markdown_contains_score_and_findings() -> None:
    ctx = _ctx()
    score = _score()
    findings = [
        Finding(
            finding_id="f1",
            rule_id="det.x",
            source="deterministic",
            severity=Severity.high,
            category="security",
            title="Secret?",
            description="d",
            file_path="app/k.py",
            line_start=2,
            line_end=2,
        ),
    ]
    md = render_pr_feedback_markdown(
        ctx=ctx,
        score=score,
        findings=findings,
        llm=LlmReviewResult(status="ok", summary="Looks fine overall."),
        rule_pack_version="v0_1_0",
    )
    assert "PR #3" in md
    assert "82/100" in md
    assert "v0_1_0" in md
    assert "Looks fine overall." in md
    assert "Secret?" in md
    assert "### Strengths" in md
    assert "### Risks" in md
    assert "### Next actions" in md
