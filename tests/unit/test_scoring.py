import pytest

from app.domain.findings import Finding, Severity
from app.domain.pr_context import NormalizedPrContext
from app.domain.scoring import DimensionWeights, compute_pr_score
from app.services.scoring_service import default_scoring_config, score_pr


def _f(
    *,
    rule_id: str,
    severity: Severity,
    category: str,
    confidence: float = 1.0,
    title: str = "t",
    description: str = "d",
    file_path: str = "app/x.py",
) -> Finding:
    return Finding(
        rule_id=rule_id,
        source="deterministic",
        severity=severity,
        category=category,
        title=title,
        description=description,
        file_path=file_path,
        line_start=1,
        line_end=1,
        confidence=confidence,
    ).with_finding_id("v0_1_0")


def test_no_findings_all_dimensions_baseline() -> None:
    result = compute_pr_score([], None, default_scoring_config())
    assert result.final_score == 100
    assert result.subscores.security == 100
    assert result.subscores.maintainability == 100
    assert len(result.explanation) == 5


def test_single_high_security_finding_lowers_security_and_final() -> None:
    findings = [
        _f(
            rule_id="det.secret_pattern",
            severity=Severity.high,
            category="security",
        ),
    ]
    result = compute_pr_score(findings, None, default_scoring_config())
    assert result.subscores.security == 84
    assert result.subscores.maintainability == 100
    assert result.final_score == 97


def test_partial_context_applies_penalty() -> None:
    findings = [
        _f(
            rule_id="det.secret_pattern",
            severity=Severity.high,
            category="security",
        ),
    ]
    ctx = NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
        base_sha="b" * 40,
        partial_context=True,
    )
    result = compute_pr_score(findings, ctx, default_scoring_config())
    assert result.final_score == 92
    assert any("partial_context" in line for line in result.explanation)
    assert "partial_context_degradation" in result.notes


def test_truncation_notes_trigger_partial_degradation() -> None:
    ctx = NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
        base_sha="b" * 40,
        truncation_notes=["truncated_max_files"],
    )
    result = compute_pr_score([], ctx, default_scoring_config())
    assert result.final_score == 95
    assert "partial_context_degradation" in result.notes


def test_order_invariant_for_identical_findings() -> None:
    a = _f(
        rule_id="det.todo_fixme",
        severity=Severity.low,
        category="maintainability",
        title="a",
    )
    b = _f(
        rule_id="det.todo_fixme",
        severity=Severity.low,
        category="maintainability",
        title="b",
    )
    r1 = compute_pr_score([a, b], None, default_scoring_config())
    r2 = compute_pr_score([b, a], None, default_scoring_config())
    assert r1.final_score == r2.final_score
    assert r1.subscores == r2.subscores


def test_confidence_scales_penalty() -> None:
    findings = [
        _f(
            rule_id="det.secret_pattern",
            severity=Severity.high,
            category="security",
            confidence=0.5,
        ),
    ]
    result = compute_pr_score(findings, None, default_scoring_config())
    assert result.subscores.security == 92
    assert result.final_score == 98


def test_score_pr_delegates_to_compute() -> None:
    result = score_pr([], None, None)
    assert result.final_score == 100


def test_custom_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="weights"):
        DimensionWeights(
            maintainability=0.6,
            correctness_confidence=0.6,
            testing=0.0,
            security=0.0,
            readability=0.0,
        )
