"""One-pass LLM reviewer: build prompt, call model, validate, map to `Finding`."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.domain.findings import Finding
from app.domain.pr_context import NormalizedPrContext
from app.schemas.llm_review import (
    LlmReviewerRawFinding,
    LlmReviewerResponse,
    parse_llm_reviewer_response,
)
from app.services.llm_client import GeminiGenerativeClient, LlmClient, OpenAiCompatibleClient
from app.services.prompt_loader import load_memory_snippets, load_review_system_prompt

logger = logging.getLogger(__name__)

LLM_RULE_PACK_VERSION_DEFAULT = "llm_v0_1_0"
MAX_LLM_FINDINGS = 50


class LlmReviewResult(BaseModel):
    """Outcome of a single LLM review pass."""

    summary: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    status: Literal["ok", "failed", "skipped"] = "skipped"
    notes: list[str] = Field(default_factory=list)


def build_system_prompt() -> str:
    """Review instructions plus optional memory snippets."""

    base = load_review_system_prompt()
    patterns, anti = load_memory_snippets()
    if patterns.strip():
        base += "\n\n## Project memory: patterns\n" + patterns.strip()
    if anti.strip():
        base += "\n\n## Project memory: anti-patterns\n" + anti.strip()
    return base


def build_reviewer_user_payload(
    ctx: NormalizedPrContext,
    *,
    max_chars_per_file: int,
    max_total_chars: int,
) -> tuple[str, list[str]]:
    """JSON string for the user message plus truncation notes."""

    notes: list[str] = []
    files_payload: list[dict[str, Any]] = []
    total_est = 0

    for f in ctx.files:
        raw_patch = f.patch or ""
        truncated = raw_patch[:max_chars_per_file]
        if len(raw_patch) > max_chars_per_file:
            notes.append(f"truncated_patch:{f.path}")

        entry = {
            "path": f.path,
            "status": f.status,
            "additions": f.additions,
            "deletions": f.deletions,
            "changes": f.changes,
            "patch": truncated,
        }
        est = len(f.path) + len(truncated) + 64
        if total_est + est > max_total_chars:
            notes.append("truncated_user_payload_max_total_chars")
            break
        files_payload.append(entry)
        total_est += est

    payload = {
        "repository_full_name": ctx.repository_full_name,
        "pr_number": ctx.pr_number,
        "head_sha": ctx.head_sha,
        "base_sha": ctx.base_sha,
        "head_ref": ctx.head_ref,
        "base_ref": ctx.base_ref,
        "title": ctx.title,
        "author_login": ctx.author_login,
        "partial_context": ctx.partial_context,
        "truncation_notes": ctx.truncation_notes,
        "files": files_payload,
    }
    return json.dumps(payload, ensure_ascii=False), notes


def _raw_to_finding(raw: LlmReviewerRawFinding, *, llm_pack_version: str) -> Finding:
    line_start = max(1, raw.line_start)
    line_end = max(1, raw.line_end)
    if line_end < line_start:
        line_end = line_start
    finding = Finding(
        rule_id=raw.rule_id,
        source="llm",
        severity=raw.severity,
        category=raw.category,
        title=raw.title,
        description=raw.description,
        suggestion=raw.suggestion,
        file_path=raw.file_path,
        line_start=line_start,
        line_end=line_end,
        confidence=raw.confidence,
    )
    return finding.with_finding_id(llm_pack_version)


def _filter_and_map_findings(
    parsed: LlmReviewerResponse,
    ctx: NormalizedPrContext,
    *,
    llm_pack_version: str,
    notes: list[str],
) -> list[Finding]:
    allowed_paths = {f.path for f in ctx.files}
    out: list[Finding] = []
    for raw in parsed.findings[:MAX_LLM_FINDINGS]:
        if raw.file_path not in allowed_paths:
            notes.append(f"dropped_finding_unknown_file:{raw.file_path}")
            continue
        out.append(_raw_to_finding(raw, llm_pack_version=llm_pack_version))
    if len(parsed.findings) > MAX_LLM_FINDINGS:
        notes.append(f"capped_findings_at_{MAX_LLM_FINDINGS}")
    return out


async def run_llm_reviewer(
    ctx: NormalizedPrContext,
    client: LlmClient,
    *,
    system_prompt: str | None = None,
    llm_pack_version: str = LLM_RULE_PACK_VERSION_DEFAULT,
    max_chars_per_file: int = 24_000,
    max_user_payload_chars: int = 120_000,
) -> LlmReviewResult:
    """Call the model, validate JSON, and return normalized `Finding` rows."""

    notes: list[str] = []
    system = system_prompt if system_prompt is not None else build_system_prompt()
    user, build_notes = build_reviewer_user_payload(
        ctx,
        max_chars_per_file=max_chars_per_file,
        max_total_chars=max_user_payload_chars,
    )
    notes.extend(build_notes)

    try:
        content = await client.complete_json(system=system, user=user)
        parsed = parse_llm_reviewer_response(content)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"llm_parse_or_request_failed:{type(exc).__name__}:{exc}")
        logger.exception("llm_reviewer_failed")
        return LlmReviewResult(status="failed", findings=[], notes=notes)

    findings = _filter_and_map_findings(parsed, ctx, llm_pack_version=llm_pack_version, notes=notes)
    summary = parsed.summary.strip() or None
    return LlmReviewResult(
        summary=summary,
        findings=findings,
        status="ok",
        notes=notes,
    )


async def run_llm_reviewer_from_settings(
    ctx: NormalizedPrContext,
    settings: Settings,
) -> LlmReviewResult:
    """Convenience: skip when no API key for the selected provider; then run review."""

    http_llm: OpenAiCompatibleClient | GeminiGenerativeClient
    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            return LlmReviewResult(
                status="skipped",
                findings=[],
                notes=[
                    "gemini_api_key not configured (set GEMINI_API_KEY for LLM_PROVIDER=gemini)"
                ],
            )
        http_llm = GeminiGenerativeClient(
            settings.gemini_api_key,
            model=settings.gemini_model,
            max_output_tokens=settings.llm_max_output_tokens,
            use_json_mime_type=settings.llm_json_response_format,
        )
    else:
        if not settings.openai_api_key:
            return LlmReviewResult(
                status="skipped",
                findings=[],
                notes=[
                    "openai_api_key not configured (set OPENAI_API_KEY for LLM_PROVIDER=openai)"
                ],
            )
        http_llm = OpenAiCompatibleClient(
            settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.llm_model,
            max_output_tokens=settings.llm_max_output_tokens,
            use_json_response_format=settings.llm_json_response_format,
        )

    try:
        return await run_llm_reviewer(
            ctx,
            http_llm,
            max_chars_per_file=settings.llm_max_chars_per_file,
            max_user_payload_chars=settings.llm_max_user_payload_chars,
        )
    finally:
        await http_llm.aclose()
