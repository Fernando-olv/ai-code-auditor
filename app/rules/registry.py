"""Default deterministic rule list."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.findings import RuleEngineConfig
from app.domain.rule_protocol import DeterministicRule
from app.rules.coverage_heuristic_rules import NoTestWithCodeChangeRule
from app.rules.size_rules import LargeDiffRule
from app.rules.text_scan_rules import DebugPrintRule, SecretPatternRule, TodoFixmeRule


def default_deterministic_rules(
    _config: RuleEngineConfig | None = None,
) -> Sequence[DeterministicRule]:
    """Ordered built-in rules for `v0_1_0`."""

    _ = _config
    return [
        LargeDiffRule(),
        TodoFixmeRule(),
        DebugPrintRule(),
        SecretPatternRule(),
        NoTestWithCodeChangeRule(),
    ]
