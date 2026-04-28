"""Structured findings for deterministic rules and future LLM output."""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

FindingSource = Literal["deterministic", "llm"]


class Severity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


def compute_finding_id(
    rule_pack_version: str,
    rule_id: str,
    file_path: str,
    line_start: int,
    line_end: int,
    title: str,
) -> str:
    """Stable id for dedupe and persistence (first 32 hex chars of SHA-256)."""

    payload = "|".join(
        (
            rule_pack_version,
            rule_id,
            file_path,
            str(line_start),
            str(line_end),
            title,
        ),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest[:32]


class Finding(BaseModel):
    """One issue aligned with Firestore `findings` and agents reviewer output."""

    finding_id: str = ""
    rule_id: str
    source: FindingSource = "deterministic"
    severity: Severity
    category: str
    title: str
    description: str
    suggestion: str = ""
    file_path: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)

    @field_validator("line_end")
    @classmethod
    def line_end_ge_start(cls, line_end: int, info: ValidationInfo) -> int:
        start = info.data.get("line_start")
        if start is not None and line_end < start:
            msg = "line_end must be >= line_start"
            raise ValueError(msg)
        return line_end

    def with_finding_id(self, rule_pack_version: str) -> Finding:
        """Return a copy with `finding_id` set from stable hash inputs."""

        fid = compute_finding_id(
            rule_pack_version,
            self.rule_id,
            self.file_path,
            self.line_start,
            self.line_end,
            self.title,
        )
        return self.model_copy(update={"finding_id": fid})


class RuleEngineResult(BaseModel):
    """Output of running the deterministic rule pack on a PR snapshot."""

    rule_pack_version: str
    findings: list[Finding] = Field(default_factory=list)
    engine_notes: list[str] = Field(default_factory=list)


class RuleEngineConfig(BaseModel):
    """Tunable thresholds; keep defaults conservative for MVP."""

    large_diff_total_lines_threshold: int = 500
    large_diff_file_count_threshold: int = 25
    large_diff_patch_bytes_threshold: int = 200_000
