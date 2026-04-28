"""GitHub PR-facing markdown from score, findings, and optional LLM outcome."""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.domain.findings import Finding, Severity
from app.domain.pr_context import NormalizedPrContext
from app.domain.scoring import PrScoreResult, Subscores
from app.services.llm_reviewer import LlmReviewResult

# HTML comment marker for idempotent issue comments (hidden in GitHub UI).
MARKER_PREFIX = "<!-- ai-dev-auditor:head_sha="
MARKER_SUFFIX = " -->"

# GitHub issue comment body limit is ~65536 UTF-16 code units; stay safely under.
MAX_COMMENT_BODY_CHARS = 60_000

_DEFAULT_MAX_FINDINGS = 25

_SEVERITY_RANK: dict[str, int] = {
    str(Severity.high): 0,
    str(Severity.medium): 1,
    str(Severity.low): 2,
}


def head_sha_comment_marker(head_sha: str) -> str:
    """Stable marker embedded at end of comment body for duplicate detection."""

    return f"{MARKER_PREFIX}{head_sha}{MARKER_SUFFIX}"


def comment_body_includes_marker_for_sha(body: str, head_sha: str) -> bool:
    return head_sha_comment_marker(head_sha) in body


def append_head_sha_marker(body: str, head_sha: str) -> str:
    """Append marker; trim main body if needed so total length fits GitHub limits."""

    marker = head_sha_comment_marker(head_sha)
    max_main = max(0, MAX_COMMENT_BODY_CHARS - len(marker) - 1)
    trimmed = body.rstrip()
    if len(trimmed) > max_main:
        trimmed = trimmed[: max_main - 20].rstrip() + "\n\n…(truncated for GitHub length limit)"
    return f"{trimmed}\n{marker}"


def _sort_findings(findings: Sequence[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (_SEVERITY_RANK.get(str(f.severity), 9), f.file_path, f.finding_id),
    )


def _strengths_section(score: PrScoreResult, findings: Sequence[Finding]) -> list[str]:
    lines: list[str] = []
    if not findings:
        lines.append("Clean snapshot: no rule or LLM findings on the analyzed diff.")
    subs: Subscores = score.subscores
    for name, val in subs.model_dump().items():
        if val >= 88:
            lines.append(f"Strong **{name.replace('_', ' ')}** ({val}/100).")
    if score.final_score >= 90 and not any(f.severity == Severity.high for f in findings):
        hi = score.final_score
        lines.append(f"High overall score ({hi}/100) with no **high** severity items.")
    if not lines:
        lines.append("Baseline review completed; see risks and findings for focus areas.")
    return lines


def _risks_section(findings: Sequence[Finding], *, cap: int = 8) -> list[str]:
    risky = [f for f in findings if f.severity in (Severity.high, Severity.medium)]
    risky = _sort_findings(risky)[:cap]
    if not risky:
        return ["No **high** or **medium** severity findings in this pass."]
    out: list[str] = []
    for f in risky:
        loc = f"{f.file_path}:{f.line_start}"
        out.append(f"- **{f.severity}** — {f.title} (`{loc}`)")
    return out


def _next_actions_section(
    score: PrScoreResult,
    findings: Sequence[Finding],
    llm: LlmReviewResult | None,
) -> list[str]:
    highs = [f for f in findings if f.severity == Severity.high]
    if highs:
        msg = (
            f"Address **{len(highs)}** high-severity finding(s), "
            "then push an update to re-run analysis."
        )
        return [msg]
    if score.final_score < 70:
        msg = "Review subscores and findings; consider incremental refactors before merging."
        return [msg]
    if llm and llm.summary:
        first = re.split(r"(?<=[.!?])\s+", llm.summary.strip(), maxsplit=1)[0]
        if len(first) > 200:
            first = first[:197] + "…"
        return [first]
    return ["Resolve or dismiss findings as appropriate; keep tests and security checks green."]


def render_pr_feedback_markdown(
    *,
    ctx: NormalizedPrContext,
    score: PrScoreResult,
    findings: Sequence[Finding],
    llm: LlmReviewResult | None = None,
    rule_pack_version: str,
    max_findings_shown: int = _DEFAULT_MAX_FINDINGS,
) -> str:
    """Build markdown for a single issue comment (marker appended separately)."""

    title = f"## AI Dev Auditor — PR #{ctx.pr_number}"
    repo_line = f"**Repo:** `{ctx.repository_full_name}`  ·  **Head:** `{ctx.head_sha[:7]}`"
    if ctx.partial_context or ctx.truncation_notes:
        repo_line += "  ·  _(partial / truncated context — scores may be conservative)_"

    sub = score.subscores.model_dump()
    sub_line = " · ".join(f"{k.replace('_', ' ')} **{v}**" for k, v in sub.items())

    score_block = "\n".join(
        [
            "### Score",
            f"- **Final:** {score.final_score}/100",
            f"- **Subscores:** {sub_line}",
            f"- **Policy:** `{score.scoring_policy_version}` · **Rules:** `{rule_pack_version}`",
        ],
    )

    expl = "\n".join(f"- {line}" for line in score.explanation[:8])
    if len(score.explanation) > 8:
        expl += f"\n- _…{len(score.explanation) - 8} more line(s)_"
    explain_block = "### Score notes\n" + (expl if expl.strip() else "- _(none)_")

    strengths = "\n".join(f"- {s}" for s in _strengths_section(score, findings))
    risks = "\n".join(_risks_section(findings))
    next_actions = "\n".join(f"- {s}" for s in _next_actions_section(score, findings, llm))

    llm_block = ""
    if llm is not None:
        llm_block = f"### LLM review\n- **Status:** `{llm.status}`\n"
        if llm.summary:
            llm_block += f"\n{llm.summary.strip()}\n"

    sorted_f = _sort_findings(findings)[:max_findings_shown]
    finding_lines: list[str] = []
    for f in sorted_f:
        sev = str(f.severity)
        src = f.source
        finding_lines.append(
            f"- **{sev}** ({src}) `{f.file_path}:{f.line_start}` — {f.title}",
        )
    if len(findings) > max_findings_shown:
        finding_lines.append(
            f"\n_Showing {max_findings_shown} of {len(findings)} findings._",
        )
    findings_block = "### Findings\n" + ("\n".join(finding_lines) if finding_lines else "- None.")

    parts = [
        title,
        "",
        repo_line,
        "",
        score_block,
        "",
        explain_block,
        "",
        "### Strengths",
        strengths,
        "",
        "### Risks",
        risks,
        "",
        "### Next actions",
        next_actions,
        "",
    ]
    if llm_block:
        parts.extend([llm_block, ""])
    parts.append(findings_block)
    return "\n".join(parts).strip()
