"""Rules based on aggregate diff size."""

from __future__ import annotations

from app.domain.findings import Finding, RuleEngineConfig, Severity
from app.domain.pr_context import NormalizedPrContext


class LargeDiffRule:
    rule_id = "det.large_diff"

    def evaluate(
        self,
        ctx: NormalizedPrContext,
        config: RuleEngineConfig,
    ) -> list[Finding]:
        total_lines = sum(f.additions + f.deletions for f in ctx.files)
        n_files = len(ctx.files)
        patch_bytes = sum(len((f.patch or "").encode("utf-8")) for f in ctx.files)

        if (
            total_lines <= config.large_diff_total_lines_threshold
            and n_files <= config.large_diff_file_count_threshold
            and patch_bytes <= config.large_diff_patch_bytes_threshold
        ):
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.medium,
                category="size",
                title="Large pull request diff",
                description=(
                    f"This change set is large (lines changed ~{total_lines}, "
                    f"files {n_files}, patch ~{patch_bytes} bytes). "
                    "Review confidence may be lower; consider splitting the PR."
                ),
                suggestion="Split into smaller PRs or reduce scope where possible.",
                file_path=".",
                line_start=1,
                line_end=1,
                confidence=0.85,
            ),
        ]
