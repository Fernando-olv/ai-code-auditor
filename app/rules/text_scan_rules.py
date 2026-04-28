"""Text and regex heuristics over added diff lines."""

from __future__ import annotations

import re

from app.domain.findings import Finding, RuleEngineConfig, Severity
from app.domain.patch_utils import iter_added_lines
from app.domain.pr_context import NormalizedPrContext

_TODO_FIXME = re.compile(r"(?i)\b(todo|fixme)\b")
_DEBUG_PATTERNS = (
    re.compile(r"\bprint\s*\("),
    re.compile(r"\bpdb\.set_trace\s*\("),
    re.compile(r"\bbreakpoint\s*\("),
    re.compile(r"\bconsole\.log\s*\("),
)
_SECRET_PATTERNS = (
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key id pattern"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "PEM private key header"),
    (re.compile(r"ghp_[a-zA-Z0-9]{20,}"), "GitHub personal access token pattern"),
    (re.compile(r"gho_[a-zA-Z0-9]{20,}"), "GitHub OAuth token pattern"),
)


class TodoFixmeRule:
    rule_id = "det.todo_fixme"

    def evaluate(
        self,
        ctx: NormalizedPrContext,
        _config: RuleEngineConfig,
    ) -> list[Finding]:
        out: list[Finding] = []
        for f in ctx.files:
            if not f.patch:
                continue
            for line_no, text in iter_added_lines(f.patch):
                if _TODO_FIXME.search(text):
                    out.append(
                        Finding(
                            rule_id=self.rule_id,
                            severity=Severity.low,
                            category="maintainability",
                            title="TODO or FIXME introduced",
                            description=(
                                f"Added line contains TODO/FIXME marker at {f.path}:{line_no}."
                            ),
                            suggestion="Track in an issue tracker or resolve before merge.",
                            file_path=f.path,
                            line_start=line_no,
                            line_end=line_no,
                            confidence=0.75,
                        ),
                    )
        return out


class DebugPrintRule:
    rule_id = "det.debug_print"

    def evaluate(
        self,
        ctx: NormalizedPrContext,
        _config: RuleEngineConfig,
    ) -> list[Finding]:
        out: list[Finding] = []
        for f in ctx.files:
            if not f.patch:
                continue
            for line_no, text in iter_added_lines(f.patch):
                for pat in _DEBUG_PATTERNS:
                    if pat.search(text):
                        out.append(
                            Finding(
                                rule_id=self.rule_id,
                                severity=Severity.medium,
                                category="correctness",
                                title="Debug or console output in new code",
                                description=(
                                    f"Possible debug print or breakpoint at {f.path}:{line_no}. "
                                    "Verify it is intentional."
                                ),
                                suggestion="Remove debug prints and breakpoints before merging.",
                                file_path=f.path,
                                line_start=line_no,
                                line_end=line_no,
                                confidence=0.65,
                            ),
                        )
                        break
        return out


class SecretPatternRule:
    rule_id = "det.secret_pattern"

    def evaluate(
        self,
        ctx: NormalizedPrContext,
        _config: RuleEngineConfig,
    ) -> list[Finding]:
        out: list[Finding] = []
        for f in ctx.files:
            if not f.patch:
                continue
            for line_no, text in iter_added_lines(f.patch):
                for pattern, label in _SECRET_PATTERNS:
                    if pattern.search(text):
                        out.append(
                            Finding(
                                rule_id=self.rule_id,
                                severity=Severity.high,
                                category="security",
                                title="Possible secret in diff",
                                description=(
                                    f"Heuristic matched {label} on added line at "
                                    f"{f.path}:{line_no}. May be a false positive."
                                ),
                                suggestion="Rotate credentials if real; use secret scanning in CI.",
                                file_path=f.path,
                                line_start=line_no,
                                line_end=line_no,
                                confidence=0.55,
                            ),
                        )
                        break
        return out
