"""DTOs and helpers for persisting an analysis run to Firestore."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from google.cloud import firestore as gc_firestore

from app.domain.findings import Finding
from app.domain.pr_context import NormalizedPrContext
from app.domain.scoring import PrScoreResult


class LlmSnapshot(Protocol):
    """Minimal shape for optional LLM outcome without importing services from domain."""

    summary: str | None
    notes: list[str]
    status: str


ANALYSIS_RUNS_COLLECTION = "analysis_runs"
FINDINGS_SUBCOLLECTION = "findings"

MAX_SUMMARY_CHARS = 8000
MAX_NOTES_CHARS = 4000


def _truncate_notes(notes: list[str], max_chars: int) -> list[str]:
    if not notes:
        return []
    joined = "\n".join(notes)
    if len(joined) <= max_chars:
        return notes
    return [joined[: max_chars - 20] + "\n...[truncated]"]


def build_summary_field(score: PrScoreResult, llm: LlmSnapshot | None) -> str | None:
    """Single `summary` string for Firestore (LLM summary preferred)."""

    if llm and llm.summary and llm.summary.strip():
        return llm.summary.strip()[:MAX_SUMMARY_CHARS]
    if score.explanation:
        return "\n".join(score.explanation)[:MAX_SUMMARY_CHARS]
    return None


def compute_partial_review(
    ctx: NormalizedPrContext,
    score: PrScoreResult,
    llm: LlmSnapshot | None,
) -> bool:
    """Whether the run should be flagged as partial / reduced confidence."""

    if ctx.partial_context:
        return True
    if any("truncated" in n for n in ctx.truncation_notes):
        return True
    if score.notes:
        return True
    if llm is not None and llm.status != "ok":
        return True
    return False


def finding_to_firestore_dict(finding: Finding) -> dict[str, Any]:
    """Serialize a `Finding` for the `findings` subcollection."""

    return {
        "finding_id": finding.finding_id,
        "rule_id": finding.rule_id,
        "source": finding.source,
        "severity": str(finding.severity),
        "category": finding.category,
        "title": finding.title,
        "description": finding.description,
        "suggestion": finding.suggestion,
        "file_path": finding.file_path,
        "line_start": finding.line_start,
        "line_end": finding.line_end,
        "confidence": finding.confidence,
    }


def build_analysis_run_document(
    *,
    analysis_id: str,
    ctx: NormalizedPrContext,
    score: PrScoreResult,
    rule_pack_version: str,
    deterministic_engine_notes: list[str],
    llm: LlmSnapshot | None,
    llm_pack_version: str | None,
    status: Literal["pending", "completed", "failed"],
    latency_ms: int | None,
    error_message: str | None,
) -> dict[str, Any]:
    """Parent `analysis_runs/{analysis_id}` payload (includes server timestamps)."""

    summary = build_summary_field(score, llm)
    partial = compute_partial_review(ctx, score, llm)

    doc: dict[str, Any] = {
        "analysis_id": analysis_id,
        "repo": ctx.repository_full_name,
        "pr_number": ctx.pr_number,
        "head_sha": ctx.head_sha,
        "author": ctx.author_login,
        "status": status,
        "rule_pack_version": rule_pack_version,
        "scoring_policy_version": score.scoring_policy_version,
        "created_at": gc_firestore.SERVER_TIMESTAMP,
        "completed_at": gc_firestore.SERVER_TIMESTAMP,
        "latency_ms": latency_ms,
        "final_score": score.final_score,
        "subscores": score.subscores.model_dump(),
        "summary": summary,
        "partial_review": partial,
        "error_message": error_message,
        "deterministic_engine_notes": _truncate_notes(deterministic_engine_notes, MAX_NOTES_CHARS),
    }
    if llm is not None:
        doc["llm_notes"] = _truncate_notes(llm.notes, MAX_NOTES_CHARS)
    if llm_pack_version:
        doc["llm_pack_version"] = llm_pack_version
    return doc
