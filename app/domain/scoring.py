"""Deterministic PR scoring from findings (Milestone 5)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.domain.findings import Finding, Severity
from app.domain.pr_context import NormalizedPrContext


class ScoreDimension(StrEnum):
    maintainability = "maintainability"
    correctness_confidence = "correctness_confidence"
    testing = "testing"
    security = "security"
    readability = "readability"


DIMENSIONS: tuple[ScoreDimension, ...] = (
    ScoreDimension.maintainability,
    ScoreDimension.correctness_confidence,
    ScoreDimension.testing,
    ScoreDimension.security,
    ScoreDimension.readability,
)


class Subscores(BaseModel):
    """Integer 0–100 subscores per MVP dimension."""

    maintainability: int = Field(ge=0, le=100)
    correctness_confidence: int = Field(ge=0, le=100)
    testing: int = Field(ge=0, le=100)
    security: int = Field(ge=0, le=100)
    readability: int = Field(ge=0, le=100)


class DimensionWeights(BaseModel):
    """Weights for blending subscores into `final_score` (must sum to 1.0)."""

    maintainability: float = 0.2
    correctness_confidence: float = 0.2
    testing: float = 0.2
    security: float = 0.2
    readability: float = 0.2

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> DimensionWeights:
        total = (
            self.maintainability
            + self.correctness_confidence
            + self.testing
            + self.security
            + self.readability
        )
        if abs(total - 1.0) > 1e-6:
            msg = "dimension weights must sum to 1.0"
            raise ValueError(msg)
        return self


class ScoringConfig(BaseModel):
    """Tunable scoring policy (no environment reads)."""

    scoring_policy_version: str = "score_v0_1_0"
    baseline: int = Field(default=100, ge=0, le=100)
    penalty_low: float = 3.0
    penalty_medium: float = 8.0
    penalty_high: float = 16.0
    partial_context_penalty: int = Field(default=5, ge=0, le=50)
    default_dimension: ScoreDimension = ScoreDimension.maintainability
    weights: DimensionWeights = Field(default_factory=DimensionWeights)
    rule_prefix_routes: tuple[tuple[str, ScoreDimension], ...] = (
        ("det.secret_", ScoreDimension.security),
        ("det.large_diff", ScoreDimension.maintainability),
        ("det.todo_fixme", ScoreDimension.maintainability),
        ("det.debug_print", ScoreDimension.correctness_confidence),
        ("det.no_test", ScoreDimension.testing),
        ("llm.reviewer", ScoreDimension.readability),
    )
    category_keyword_routes: tuple[tuple[str, ScoreDimension], ...] = (
        ("security", ScoreDimension.security),
        ("secret", ScoreDimension.security),
        ("test", ScoreDimension.testing),
        ("correctness", ScoreDimension.correctness_confidence),
        ("readability", ScoreDimension.readability),
        ("maintainability", ScoreDimension.maintainability),
    )


class PrScoreResult(BaseModel):
    """Outcome of deterministic scoring for one PR snapshot."""

    final_score: int = Field(ge=0, le=100)
    subscores: Subscores
    explanation: list[str] = Field(default_factory=list)
    scoring_policy_version: str
    notes: list[str] = Field(default_factory=list)


def _severity_penalty_base(severity: Severity, config: ScoringConfig) -> float:
    if severity == Severity.low:
        return config.penalty_low
    if severity == Severity.medium:
        return config.penalty_medium
    return config.penalty_high


def _finding_penalty(finding: Finding, config: ScoringConfig) -> float:
    return _severity_penalty_base(finding.severity, config) * float(finding.confidence)


def _route_dimension(finding: Finding, config: ScoringConfig) -> ScoreDimension:
    rid = finding.rule_id
    for prefix, dim in config.rule_prefix_routes:
        if rid.startswith(prefix):
            return dim
    cat = finding.category.lower()
    for needle, dim in config.category_keyword_routes:
        if needle in cat:
            return dim
    return config.default_dimension


def _sorted_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (f.finding_id, f.rule_id, f.file_path, f.title),
    )


def _partial_degradation(ctx: NormalizedPrContext | None) -> bool:
    if ctx is None:
        return False
    if ctx.partial_context:
        return True
    return any("truncated" in n for n in ctx.truncation_notes)


def compute_pr_score(
    findings: list[Finding],
    ctx: NormalizedPrContext | None = None,
    config: ScoringConfig | None = None,
) -> PrScoreResult:
    """Compute subscores and final score from findings (order-invariant)."""

    cfg = config or ScoringConfig()
    notes: list[str] = []
    explanation: list[str] = []

    penalties: dict[ScoreDimension, float] = {d: 0.0 for d in DIMENSIONS}
    counts: dict[ScoreDimension, int] = {d: 0 for d in DIMENSIONS}
    high_counts: dict[ScoreDimension, int] = {d: 0 for d in DIMENSIONS}

    for finding in _sorted_findings(list(findings)):
        dim = _route_dimension(finding, cfg)
        penalties[dim] += _finding_penalty(finding, cfg)
        counts[dim] += 1
        if finding.severity == Severity.high:
            high_counts[dim] += 1

    sub: dict[str, int] = {}
    for dim in DIMENSIONS:
        raw_pen = penalties[dim]
        score = int(round(max(0.0, min(100.0, float(cfg.baseline) - raw_pen))))
        sub[dim.value] = score
        if counts[dim] > 0:
            explanation.append(
                f"{dim.value}: score {score} (penalty {raw_pen:.1f} from {counts[dim]} "
                f"finding(s), {high_counts[dim]} high)",
            )
        else:
            explanation.append(f"{dim.value}: score {score} (no findings routed here)")

    subscores = Subscores.model_validate(sub)

    w = cfg.weights
    blended = (
        w.maintainability * subscores.maintainability
        + w.correctness_confidence * subscores.correctness_confidence
        + w.testing * subscores.testing
        + w.security * subscores.security
        + w.readability * subscores.readability
    )
    final = int(round(blended))
    final = max(0, min(100, final))

    if _partial_degradation(ctx):
        before = final
        final = max(0, final - cfg.partial_context_penalty)
        explanation.append(
            f"partial_context: applied penalty {cfg.partial_context_penalty} "
            f"(before {before}, after {final})",
        )
        notes.append("partial_context_degradation")

    return PrScoreResult(
        final_score=final,
        subscores=subscores,
        explanation=explanation,
        scoring_policy_version=cfg.scoring_policy_version,
        notes=notes,
    )
