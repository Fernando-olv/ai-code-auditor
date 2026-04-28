"""Contract for deterministic PR rules (domain-only, no service imports)."""

from __future__ import annotations

from typing import Protocol

from app.domain.findings import Finding, RuleEngineConfig
from app.domain.pr_context import NormalizedPrContext


class DeterministicRule(Protocol):
    """Single rule: inspect context and emit zero or more findings."""

    rule_id: str

    def evaluate(
        self,
        ctx: NormalizedPrContext,
        config: RuleEngineConfig,
    ) -> list[Finding]:
        """Return findings without requiring `finding_id`; engine assigns ids."""
