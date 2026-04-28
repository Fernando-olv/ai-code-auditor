"""Low-confidence heuristics when full coverage data is unavailable."""

from __future__ import annotations

from app.domain.findings import Finding, RuleEngineConfig, Severity
from app.domain.pr_context import NormalizedPrContext


def _looks_test_path(path: str) -> bool:
    p = path.replace("\\", "/")
    if "/tests/" in p or p.startswith("tests/"):
        return True
    name = p.rsplit("/", maxsplit=1)[-1]
    if name.startswith("test_") and name.endswith(".py"):
        return True
    if name.endswith("_test.py"):
        return True
    return False


def _looks_application_py(path: str) -> bool:
    if not path.endswith(".py"):
        return False
    if _looks_test_path(path):
        return False
    p = path.replace("\\", "/")
    return p.startswith("app/") or "/services/" in p or "/domain/" in p or p.startswith("src/")


class NoTestWithCodeChangeRule:
    rule_id = "det.no_test_with_code_change"

    def evaluate(
        self,
        ctx: NormalizedPrContext,
        _config: RuleEngineConfig,
    ) -> list[Finding]:
        paths = [f.path for f in ctx.files]
        has_app_py = any(_looks_application_py(p) for p in paths)
        has_test = any(_looks_test_path(p) for p in paths)

        if not has_app_py or has_test:
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.low,
                category="testing",
                title="Application code changed without obvious test files",
                description=(
                    "Heuristic: changed paths look like application Python but no typical "
                    "test paths appeared in this PR snapshot. This can be a false positive "
                    "(tests elsewhere, non-Python tests, or generated code)."
                ),
                suggestion="Add or update tests next to the change when practical.",
                file_path=".",
                line_start=1,
                line_end=1,
                confidence=0.35,
            ),
        ]
