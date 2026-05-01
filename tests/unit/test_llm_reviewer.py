import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.domain.findings import Severity
from app.domain.pr_context import NormalizedChangedFile, NormalizedPrContext
from app.services.analysis_merge import concat_findings
from app.services.llm_reviewer import (
    LLM_RULE_PACK_VERSION_DEFAULT,
    build_reviewer_user_payload,
    run_llm_reviewer,
    run_llm_reviewer_from_settings,
)


class _MockLlm:
    def __init__(self, content: str) -> None:
        self._content = content

    async def complete_json(self, *, system: str, user: str) -> str:
        _ = system, user
        return self._content


def _minimal_ctx() -> NormalizedPrContext:
    return NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=7,
        head_sha="a" * 40,
        base_sha="b" * 40,
        files=[
            NormalizedChangedFile(
                path="app/main.py",
                status="modified",
                sha="s",
                patch="@@ -0,0 +1,1 @@\n+pass\n",
            ),
        ],
    )


@pytest.mark.asyncio
async def test_run_llm_reviewer_ok_maps_findings() -> None:
    fixture = (
        Path(__file__).resolve().parents[1] / "fixtures" / "llm_outputs" / "valid_reviewer.json"
    )
    content = fixture.read_text(encoding="utf-8")
    result = await run_llm_reviewer(_minimal_ctx(), _MockLlm(content))

    assert result.status == "ok"
    assert result.summary
    assert len(result.findings) == 1
    f = result.findings[0]
    assert f.source == "llm"
    assert f.severity == Severity.low
    assert f.finding_id
    assert f.rule_id == "llm.reviewer.maintainability"


@pytest.mark.asyncio
async def test_run_llm_reviewer_invalid_json_fails_safe() -> None:
    result = await run_llm_reviewer(_minimal_ctx(), _MockLlm("not-json"))
    assert result.status == "failed"
    assert result.findings == []
    assert any("llm_parse_or_request_failed" in n for n in result.notes)


@pytest.mark.asyncio
async def test_run_llm_reviewer_drops_unknown_file() -> None:
    bad = json.dumps(
        {
            "summary": "x",
            "findings": [
                {
                    "rule_id": "llm.reviewer",
                    "severity": "low",
                    "category": "c",
                    "file_path": "missing.py",
                    "line_start": 1,
                    "line_end": 1,
                    "title": "t",
                    "description": "d",
                    "confidence": 0.5,
                },
            ],
        },
    )
    result = await run_llm_reviewer(_minimal_ctx(), _MockLlm(bad))
    assert result.status == "ok"
    assert result.findings == []
    assert any("dropped_finding_unknown_file" in n for n in result.notes)


def test_build_reviewer_user_payload_truncation_note() -> None:
    big = "x" * 50_000
    ctx = NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
        base_sha="b" * 40,
        files=[
            NormalizedChangedFile(
                path="app/huge.py",
                status="modified",
                sha="s",
                patch=big,
            ),
        ],
    )
    user, notes = build_reviewer_user_payload(
        ctx,
        max_chars_per_file=1000,
        max_total_chars=500_000,
    )
    data = json.loads(user)
    assert len(data["files"][0]["patch"]) <= 1000
    assert any(n.startswith("truncated_patch:") for n in notes)


def test_concat_findings_order() -> None:
    from app.domain.findings import Finding

    d = Finding(
        rule_id="det.x",
        severity=Severity.low,
        category="c",
        title="d",
        description="e",
        file_path="a.py",
        line_start=1,
        line_end=1,
        confidence=1.0,
    ).with_finding_id("v0_1_0")
    llm_finding = Finding(
        rule_id="llm.x",
        source="llm",
        severity=Severity.medium,
        category="c",
        title="t",
        description="d",
        file_path="a.py",
        line_start=1,
        line_end=1,
        confidence=0.5,
    ).with_finding_id(LLM_RULE_PACK_VERSION_DEFAULT)
    merged = concat_findings([d], [llm_finding])
    assert merged[0].source == "deterministic"
    assert merged[1].source == "llm"


@pytest.mark.asyncio
async def test_run_llm_reviewer_from_settings_skips_without_key() -> None:
    settings = Settings.model_construct(llm_provider="openai", openai_api_key="")
    result = await run_llm_reviewer_from_settings(_minimal_ctx(), settings)
    assert result.status == "skipped"
    assert "openai_api_key" in "".join(result.notes).lower()


@pytest.mark.asyncio
async def test_run_llm_reviewer_from_settings_gemini_skips_without_key() -> None:
    settings = Settings.model_construct(llm_provider="gemini", gemini_api_key="")
    result = await run_llm_reviewer_from_settings(_minimal_ctx(), settings)
    assert result.status == "skipped"
    assert "gemini_api_key" in "".join(result.notes).lower()


@pytest.mark.asyncio
async def test_run_llm_reviewer_from_settings_gemini_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import llm_factory

    fixture = (
        Path(__file__).resolve().parents[1] / "fixtures" / "llm_outputs" / "valid_reviewer.json"
    )
    inner = fixture.read_text(encoding="utf-8")

    class FakeGemini:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = args, kwargs

        async def complete_json(self, *, system: str, user: str) -> str:
            _ = system, user
            return inner

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(llm_factory, "GeminiGenerativeClient", FakeGemini)

    settings = Settings.model_construct(
        llm_provider="gemini",
        gemini_api_key="x",
        gemini_model="gemini-2.0-flash",
        llm_max_chars_per_file=24_000,
        llm_max_user_payload_chars=120_000,
    )
    result = await run_llm_reviewer_from_settings(_minimal_ctx(), settings)
    assert result.status == "ok"
    assert result.findings


@pytest.mark.asyncio
async def test_finding_id_stable_across_runs() -> None:
    fixture = (
        Path(__file__).resolve().parents[1] / "fixtures" / "llm_outputs" / "valid_reviewer.json"
    )
    content = fixture.read_text(encoding="utf-8")
    ctx = _minimal_ctx()
    r1 = await run_llm_reviewer(ctx, _MockLlm(content))
    r2 = await run_llm_reviewer(ctx, _MockLlm(content))
    assert r1.findings[0].finding_id == r2.findings[0].finding_id
