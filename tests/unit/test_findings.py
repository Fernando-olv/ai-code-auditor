import pytest
from pydantic import ValidationError

from app.domain.findings import (
    Finding,
    Severity,
    compute_finding_id,
)


def test_compute_finding_id_stable() -> None:
    a = compute_finding_id("v0_1_0", "r1", "app/x.py", 3, 3, "t")
    b = compute_finding_id("v0_1_0", "r1", "app/x.py", 3, 3, "t")
    assert a == b
    assert len(a) == 32


def test_compute_finding_id_changes_when_inputs_change() -> None:
    a = compute_finding_id("v0_1_0", "r1", "app/x.py", 3, 3, "t")
    c = compute_finding_id("v0_1_0", "r1", "app/x.py", 4, 4, "t")
    assert a != c


def test_finding_with_finding_id() -> None:
    f = Finding(
        rule_id="det.test",
        severity=Severity.low,
        category="test",
        title="T",
        description="D",
        file_path="a.py",
        line_start=2,
        line_end=2,
        confidence=1.0,
    )
    g = f.with_finding_id("v0_1_0")
    assert g.finding_id
    assert g.finding_id == compute_finding_id(
        "v0_1_0",
        "det.test",
        "a.py",
        2,
        2,
        "T",
    )


def test_finding_line_end_must_be_ge_start() -> None:
    with pytest.raises(ValidationError):
        Finding(
            rule_id="x",
            severity=Severity.low,
            category="c",
            title="t",
            description="d",
            file_path="f.py",
            line_start=5,
            line_end=3,
            confidence=1.0,
        )
