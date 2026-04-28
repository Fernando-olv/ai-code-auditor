from typing import Any

from google.cloud import firestore as gc_firestore

from app.domain.analysis_run import (
    build_analysis_run_document,
    build_summary_field,
    compute_partial_review,
    finding_to_firestore_dict,
)
from app.domain.findings import Finding, Severity
from app.domain.pr_context import NormalizedPrContext
from app.domain.scoring import PrScoreResult, Subscores
from app.services.llm_reviewer import LlmReviewResult


def _ctx(**overrides: Any) -> NormalizedPrContext:
    data: dict[str, Any] = {
        "repository_full_name": "org/repo",
        "pr_number": 42,
        "head_sha": "h" * 40,
        "base_sha": "b" * 40,
    }
    data.update(overrides)
    return NormalizedPrContext.model_validate(data)


def _score(**overrides: Any) -> PrScoreResult:
    defaults: dict[str, Any] = {
        "final_score": 88,
        "subscores": Subscores(
            maintainability=90,
            correctness_confidence=88,
            testing=85,
            security=92,
            readability=87,
        ),
        "scoring_policy_version": "score_v0_1_0",
        "explanation": ["line1", "line2"],
        "notes": [],
    }
    defaults.update(overrides)
    return PrScoreResult.model_validate(defaults)


def test_build_summary_prefers_llm_summary() -> None:
    score = _score(explanation=["from_score"])
    llm = LlmReviewResult(summary="  hello  ", status="ok")
    assert build_summary_field(score, llm) == "hello"


def test_build_summary_falls_back_to_score_explanation() -> None:
    score = _score(explanation=["alpha", "beta"])
    assert build_summary_field(score, None) == "alpha\nbeta"


def test_compute_partial_review_llm_not_ok() -> None:
    ctx = _ctx()
    score = _score()
    llm = LlmReviewResult(status="failed")
    assert compute_partial_review(ctx, score, llm) is True


def test_finding_to_firestore_dict_shape() -> None:
    f = Finding(
        finding_id="abc",
        rule_id="det.x",
        source="deterministic",
        severity=Severity.low,
        category="c",
        title="t",
        description="d",
        file_path="p.py",
        line_start=1,
        line_end=2,
        confidence=0.5,
    )
    d = finding_to_firestore_dict(f)
    assert d["finding_id"] == "abc"
    assert d["severity"] == "low"
    assert d["confidence"] == 0.5


def test_build_analysis_run_document_core_fields() -> None:
    ctx = _ctx(author_login="alice", partial_context=False)
    score = _score()
    doc = build_analysis_run_document(
        analysis_id="aid",
        ctx=ctx,
        score=score,
        rule_pack_version="v0_1_0",
        deterministic_engine_notes=["n1"],
        llm=None,
        llm_pack_version=None,
        status="completed",
        latency_ms=123,
        error_message=None,
    )
    assert doc["analysis_id"] == "aid"
    assert doc["repo"] == "org/repo"
    assert doc["pr_number"] == 42
    assert doc["author"] == "alice"
    assert doc["status"] == "completed"
    assert doc["rule_pack_version"] == "v0_1_0"
    assert doc["latency_ms"] == 123
    assert doc["final_score"] == 88
    assert doc["subscores"] == score.subscores.model_dump()
    assert doc["created_at"] is gc_firestore.SERVER_TIMESTAMP
    assert doc["completed_at"] is gc_firestore.SERVER_TIMESTAMP
    assert "llm_pack_version" not in doc
