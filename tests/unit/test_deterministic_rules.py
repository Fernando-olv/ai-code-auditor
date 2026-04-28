import pytest

from app.domain.findings import RuleEngineConfig
from app.domain.pr_context import NormalizedChangedFile, NormalizedPrContext
from app.rules.coverage_heuristic_rules import NoTestWithCodeChangeRule
from app.rules.size_rules import LargeDiffRule
from app.rules.text_scan_rules import DebugPrintRule, SecretPatternRule, TodoFixmeRule


def _empty_config() -> RuleEngineConfig:
    return RuleEngineConfig()


@pytest.mark.parametrize(
    ("patch", "rule_id"),
    [
        ("@@ -0,0 +1,1 @@\n+# FIXME: x\n", "det.todo_fixme"),
        ("@@ -0,0 +1,1 @@\n+print('x')\n", "det.debug_print"),
        ('@@ -0,0 +1,1 @@\n+key = "AKIA0123456789012345"\n', "det.secret_pattern"),
    ],
)
def test_text_rules_match_added_lines(patch: str, rule_id: str) -> None:
    ctx = NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
        base_sha="b" * 40,
        files=[
            NormalizedChangedFile(
                path="app/x.py",
                status="modified",
                sha="s",
                patch=patch,
            ),
        ],
    )
    rules = {
        "det.todo_fixme": TodoFixmeRule(),
        "det.debug_print": DebugPrintRule(),
        "det.secret_pattern": SecretPatternRule(),
    }
    rule = rules[rule_id]
    out = rule.evaluate(ctx, _empty_config())
    assert len(out) >= 1
    assert out[0].rule_id == rule_id


def test_no_test_rule_low_confidence_when_only_app_py() -> None:
    ctx = NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
        base_sha="b" * 40,
        files=[
            NormalizedChangedFile(
                path="app/services/foo.py",
                status="modified",
                sha="s",
                patch="@@ -0,0 +1,1 @@\n+pass\n",
            ),
        ],
    )
    out = NoTestWithCodeChangeRule().evaluate(ctx, _empty_config())
    assert len(out) == 1
    assert out[0].confidence <= 0.5


def test_no_test_rule_silent_when_tests_present() -> None:
    ctx = NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
        base_sha="b" * 40,
        files=[
            NormalizedChangedFile(
                path="app/x.py",
                status="modified",
                sha="s",
                patch="@@ -0,0 +1,1 @@\n+pass\n",
            ),
            NormalizedChangedFile(
                path="tests/test_x.py",
                status="modified",
                sha="t",
                patch="@@ -0,0 +1,1 @@\n+pass\n",
            ),
        ],
    )
    out = NoTestWithCodeChangeRule().evaluate(ctx, _empty_config())
    assert out == []


def test_large_diff_rule_below_threshold_empty() -> None:
    ctx = NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
        base_sha="b" * 40,
        files=[
            NormalizedChangedFile(
                path="a.py",
                status="modified",
                sha="s",
                additions=1,
                deletions=0,
                changes=1,
                patch="@@ -0,0 +1,1 @@\n+x\n",
            ),
        ],
    )
    out = LargeDiffRule().evaluate(ctx, _empty_config())
    assert out == []
