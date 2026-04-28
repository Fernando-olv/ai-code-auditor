from app.domain.findings import RuleEngineConfig, Severity
from app.domain.pr_context import NormalizedChangedFile, NormalizedPrContext
from app.services.rule_engine import RuleEngine, default_rule_engine


def _ctx_with_patch(path: str, patch: str) -> NormalizedPrContext:
    return NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
        base_sha="b" * 40,
        files=[
            NormalizedChangedFile(
                path=path,
                status="modified",
                sha="x",
                additions=2,
                deletions=1,
                changes=3,
                patch=patch,
            ),
        ],
    )


def test_default_rule_engine_assigns_finding_ids() -> None:
    patch = """@@ -0,0 +1,1 @@
+# TODO: fix this
"""
    ctx = _ctx_with_patch("app/main.py", patch)
    engine = default_rule_engine()
    result = engine.run(ctx)

    assert result.rule_pack_version == "v0_1_0"
    todo_findings = [f for f in result.findings if f.rule_id == "det.todo_fixme"]
    assert len(todo_findings) == 1
    assert todo_findings[0].finding_id
    assert todo_findings[0].line_start == 1


def test_rule_engine_isolates_rule_failure() -> None:
    class BadRule:
        rule_id = "det.bad"

        def evaluate(self, ctx, config):  # noqa: ANN001
            raise RuntimeError("boom")

    engine = RuleEngine([BadRule()], rule_pack_version="v0_test")
    ctx = _ctx_with_patch("app/x.py", "@@ -0,0 +1,1 @@\n+ok\n")
    result = engine.run(ctx)
    assert result.findings == []
    assert any("det.bad" in n for n in result.engine_notes)


def test_large_diff_rule_fires() -> None:
    files = [
        NormalizedChangedFile(
            path=f"f{i}.py",
            status="modified",
            sha=str(i),
            additions=200,
            deletions=0,
            changes=200,
            patch="x" * 100,
        )
        for i in range(5)
    ]
    ctx = NormalizedPrContext(
        repository_full_name="o/r",
        pr_number=1,
        head_sha="a" * 40,
        base_sha="b" * 40,
        files=files,
    )
    config = RuleEngineConfig(
        large_diff_total_lines_threshold=100,
        large_diff_file_count_threshold=50,
        large_diff_patch_bytes_threshold=1_000_000,
    )
    engine = default_rule_engine(config)
    result = engine.run(ctx)
    large = [f for f in result.findings if f.rule_id == "det.large_diff"]
    assert len(large) == 1
    assert large[0].severity == Severity.medium
