"""Run deterministic rules over a normalized PR context."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from app.domain.findings import Finding, RuleEngineConfig, RuleEngineResult
from app.domain.pr_context import NormalizedPrContext
from app.domain.rule_protocol import DeterministicRule

logger = logging.getLogger(__name__)

DEFAULT_RULE_PACK_VERSION = "v0_1_0"


class RuleEngine:
    """Executes an ordered list of rules and normalizes finding ids."""

    def __init__(
        self,
        rules: Sequence[DeterministicRule],
        *,
        rule_pack_version: str = DEFAULT_RULE_PACK_VERSION,
        config: RuleEngineConfig | None = None,
    ) -> None:
        self._rules = list(rules)
        self._rule_pack_version = rule_pack_version
        self._config = config or RuleEngineConfig()

    @property
    def rule_pack_version(self) -> str:
        return self._rule_pack_version

    def run(self, ctx: NormalizedPrContext) -> RuleEngineResult:
        findings: list[Finding] = []
        engine_notes: list[str] = []

        for rule in self._rules:
            try:
                batch = rule.evaluate(ctx, self._config)
            except Exception as exc:  # noqa: BLE001 — isolate rule failures
                rid = getattr(rule, "rule_id", type(rule).__name__)
                engine_notes.append(f"{rid}:error:{type(exc).__name__}")
                logger.exception(
                    "rule_engine_rule_failed",
                    extra={"rule_id": rid},
                )
                continue

            for finding in batch:
                findings.append(finding.with_finding_id(self._rule_pack_version))

        return RuleEngineResult(
            rule_pack_version=self._rule_pack_version,
            findings=findings,
            engine_notes=engine_notes,
        )


def default_rule_engine(config: RuleEngineConfig | None = None) -> RuleEngine:
    """Rule engine with the built-in deterministic pack for the current MVP."""

    from app.rules.registry import default_deterministic_rules

    rules = default_deterministic_rules(config)
    return RuleEngine(
        rules,
        rule_pack_version=DEFAULT_RULE_PACK_VERSION,
        config=config,
    )
