"""Round-trip tests against the Firestore emulator (opt-in)."""

from __future__ import annotations

import os
import uuid

import pytest

from app.domain.findings import Finding, RuleEngineResult, Severity
from app.domain.pr_context import NormalizedPrContext
from app.repositories.analysis_repository import AnalysisRepository
from app.services.analysis_persistence import persist_analysis_run
from app.services.scoring_service import score_pr

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_persist_get_list_roundtrip_on_emulator() -> None:
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("Set FIRESTORE_EMULATOR_HOST to run Firestore integration tests")

    repo = AnalysisRepository.from_settings()
    ctx = NormalizedPrContext(
        repository_full_name="org/integration",
        pr_number=7,
        head_sha="c" * 40,
        base_sha="d" * 40,
    )
    rule_result = RuleEngineResult(rule_pack_version="v0_1_0", findings=[], engine_notes=["note"])
    score = score_pr([], ctx)
    findings = [
        Finding(
            rule_id="det.x",
            source="deterministic",
            severity=Severity.low,
            category="c",
            title="title-a",
            description="d",
            file_path="z.py",
            line_start=1,
            line_end=1,
        ).with_finding_id("v0_1_0"),
        Finding(
            rule_id="det.y",
            source="deterministic",
            severity=Severity.low,
            category="c",
            title="title-b",
            description="d",
            file_path="a.py",
            line_start=1,
            line_end=1,
        ).with_finding_id("v0_1_0"),
    ]
    aid = str(uuid.uuid4())
    await persist_analysis_run(
        repo,
        ctx=ctx,
        findings=findings,
        score=score,
        rule_result=rule_result,
        llm=None,
        llm_pack_version=None,
        latency_ms=1,
        analysis_id=aid,
    )

    loaded = await repo.get_analysis_run(aid)
    assert loaded is not None
    assert loaded.get("analysis_id") == aid
    assert loaded.get("repo") == "org/integration"
    assert loaded.get("pr_number") == 7

    rows = await repo.list_findings(aid)
    assert len(rows) == 2
    assert [r.get("file_path") for r in rows] == ["a.py", "z.py"]
