import pytest

from app.domain.findings import Finding, RuleEngineResult, Severity
from app.domain.pr_context import NormalizedPrContext
from app.domain.scoring import PrScoreResult, Subscores
from app.services.analysis_persistence import persist_analysis_run
from app.services.llm_reviewer import LlmReviewResult


class RecordingRepo:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict, list[dict]]] = []

    async def persist_analysis(
        self,
        analysis_id: str,
        run_payload: dict,
        findings: list[dict],
    ) -> None:
        self.calls.append((analysis_id, run_payload, findings))


def _minimal_ctx() -> NormalizedPrContext:
    return NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="h" * 40,
        base_sha="b" * 40,
    )


def _minimal_score() -> PrScoreResult:
    return PrScoreResult(
        final_score=100,
        subscores=Subscores(
            maintainability=100,
            correctness_confidence=100,
            testing=100,
            security=100,
            readability=100,
        ),
        scoring_policy_version="score_v0_1_0",
    )


@pytest.mark.asyncio
async def test_persist_analysis_run_assigns_finding_id_and_persists() -> None:
    repo = RecordingRepo()
    ctx = _minimal_ctx()
    findings = [
        Finding(
            rule_id="det.x",
            source="deterministic",
            severity=Severity.low,
            category="c",
            title="t",
            description="d",
            file_path="app/a.py",
            line_start=1,
            line_end=1,
        ),
    ]
    rule_result = RuleEngineResult(rule_pack_version="v0_1_0", findings=[], engine_notes=[])

    aid = await persist_analysis_run(
        repo,  # type: ignore[arg-type]
        ctx=ctx,
        findings=findings,
        score=_minimal_score(),
        rule_result=rule_result,
        llm=None,
        llm_pack_version=None,
        latency_ms=9,
        analysis_id="fixed-id",
    )

    assert aid == "fixed-id"
    assert len(repo.calls) == 1
    _run_id, run_payload, finding_rows = repo.calls[0]
    assert run_payload["analysis_id"] == "fixed-id"
    assert len(finding_rows) == 1
    assert len(finding_rows[0]["finding_id"]) == 32


@pytest.mark.asyncio
async def test_persist_analysis_run_uses_llm_pack_for_llm_findings() -> None:
    repo = RecordingRepo()
    ctx = _minimal_ctx()
    findings = [
        Finding(
            rule_id="llm.finding",
            source="llm",
            severity=Severity.medium,
            category="c",
            title="t",
            description="d",
            file_path="b.py",
            line_start=2,
            line_end=2,
        ),
    ]
    rule_result = RuleEngineResult(rule_pack_version="v0_1_0", findings=[], engine_notes=[])

    await persist_analysis_run(
        repo,  # type: ignore[arg-type]
        ctx=ctx,
        findings=findings,
        score=_minimal_score(),
        rule_result=rule_result,
        llm=LlmReviewResult(status="ok", summary="s"),
        llm_pack_version="llm_v0_1_0",
        latency_ms=None,
        analysis_id=None,
    )

    assert len(repo.calls) == 1
    aid, run_payload, finding_rows = repo.calls[0]
    assert len(aid) == 36  # UUID string
    assert run_payload["llm_pack_version"] == "llm_v0_1_0"
    assert finding_rows[0]["source"] == "llm"
    assert len(finding_rows[0]["finding_id"]) == 32
