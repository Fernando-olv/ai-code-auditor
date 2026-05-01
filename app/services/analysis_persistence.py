"""Orchestrate mapping domain outputs to Firestore via `AnalysisRepository`."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Literal

from app.domain.analysis_run import (
    build_analysis_run_document,
    finding_to_firestore_dict,
)
from app.domain.findings import Finding, RuleEngineResult
from app.domain.pr_context import NormalizedPrContext
from app.domain.scoring import PrScoreResult
from app.ports.analysis_store import AnalysisStore
from app.services.llm_reviewer import LlmReviewResult


def _ensure_finding_ids(
    findings: Sequence[Finding],
    *,
    rule_pack_version: str,
    llm_pack_version: str | None,
) -> list[Finding]:
    out: list[Finding] = []
    for f in findings:
        if f.finding_id:
            out.append(f)
            continue
        if f.source == "deterministic":
            pack = rule_pack_version
        else:
            pack = llm_pack_version or "llm_v0_1_0"
        out.append(f.with_finding_id(pack))
    return out


async def persist_analysis_run(
    store: AnalysisStore,
    *,
    ctx: NormalizedPrContext,
    findings: Sequence[Finding],
    score: PrScoreResult,
    rule_result: RuleEngineResult,
    llm: LlmReviewResult | None,
    llm_pack_version: str | None,
    status: Literal["pending", "completed", "failed"] = "completed",
    latency_ms: int | None,
    error_message: str | None = None,
    analysis_id: str | None = None,
) -> str:
    """Build Firestore payloads and persist. Returns the analysis id (new UUID if omitted)."""

    aid = analysis_id or str(uuid.uuid4())
    prepared = _ensure_finding_ids(
        list(findings),
        rule_pack_version=rule_result.rule_pack_version,
        llm_pack_version=llm_pack_version,
    )
    run_doc = build_analysis_run_document(
        analysis_id=aid,
        ctx=ctx,
        score=score,
        rule_pack_version=rule_result.rule_pack_version,
        deterministic_engine_notes=list(rule_result.engine_notes),
        llm=llm,
        llm_pack_version=llm_pack_version,
        status=status,
        latency_ms=latency_ms,
        error_message=error_message,
    )
    finding_rows = [finding_to_firestore_dict(f) for f in prepared]
    await store.persist_analysis(aid, run_doc, finding_rows)
    return aid
