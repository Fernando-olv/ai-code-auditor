"""Pydantic models for raw LLM reviewer JSON."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.domain.findings import Severity


class LlmReviewerRawFinding(BaseModel):
    """One finding object as returned by the model before mapping to `Finding`."""

    rule_id: str = Field(default="llm.reviewer", min_length=1, max_length=128)
    severity: Severity
    category: str = Field(default="general", max_length=128)
    file_path: str = Field(min_length=1, max_length=2048)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=512)
    description: str = Field(min_length=1, max_length=8000)
    suggestion: str = Field(default="", max_length=8000)
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)

    @field_validator("rule_id")
    @classmethod
    def rule_id_chars(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9._-]+", value):
            msg = "rule_id must match [a-z0-9._-]+"
            raise ValueError(msg)
        return value

    @field_validator("line_end")
    @classmethod
    def line_end_ge_start(cls, line_end: int, info: ValidationInfo) -> int:
        start = info.data.get("line_start")
        if start is not None and line_end < start:
            msg = "line_end must be >= line_start"
            raise ValueError(msg)
        return line_end


class LlmReviewerResponse(BaseModel):
    """Top-level JSON object from the reviewer model."""

    summary: str = Field(default="", max_length=8000)
    findings: list[LlmReviewerRawFinding] = Field(default_factory=list)


def _strip_json_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def parse_llm_reviewer_response(text: str) -> LlmReviewerResponse:
    """Parse model output into `LlmReviewerResponse` (raises on invalid JSON or shape)."""

    cleaned = _strip_json_fences(text)
    data: Any = json.loads(cleaned)
    if not isinstance(data, dict):
        msg = "LLM reviewer JSON must be an object"
        raise TypeError(msg)
    return LlmReviewerResponse.model_validate(data)
