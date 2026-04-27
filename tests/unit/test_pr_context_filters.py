import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.domain.pr_context import (
    FileFilterConfig,
    filter_pull_files,
    split_repository_full_name,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "github_api"


class _Row(BaseModel):
    filename: str
    status: str
    sha: str
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: str | None = None


def test_split_repository_full_name() -> None:
    assert split_repository_full_name("octo-org/octo-repo") == ("octo-org", "octo-repo")


@pytest.mark.parametrize(
    "bad",
    ["", "nope", "onlyone", "/starts-with-slash"],
)
def test_split_repository_full_name_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        split_repository_full_name(bad)


def test_filter_skips_no_patch_and_denylist() -> None:
    raw = [
        _Row.model_validate(x)
        for x in json.loads((FIXTURES_DIR / "files_mixed.json").read_text(encoding="utf-8"))
    ]
    kept, notes = filter_pull_files(raw)
    assert [f.path for f in kept] == ["src/app.py"]
    assert any("skipped_no_patch" in n for n in notes)
    assert any("skipped_denylist" in n for n in notes)


def test_filter_truncates_max_files() -> None:
    rows = [
        _Row(
            filename=f"f{i}.py",
            status="modified",
            sha=str(i),
            patch=f"patch{i}\n",
        )
        for i in range(5)
    ]
    cfg = FileFilterConfig(max_files=2)
    kept, notes = filter_pull_files(rows, config=cfg)
    assert len(kept) == 2
    assert "truncated_max_files" in notes


def test_filter_truncates_max_patch_bytes() -> None:
    rows = [
        _Row(
            filename="a.py",
            status="modified",
            sha="1",
            patch="x" * 100,
        ),
        _Row(
            filename="b.py",
            status="modified",
            sha="2",
            patch="y" * 100,
        ),
    ]
    cfg = FileFilterConfig(max_patch_bytes_total=150, max_files=10)
    kept, notes = filter_pull_files(rows, config=cfg)
    assert len(kept) == 1
    assert "truncated_max_patch_bytes" in notes
