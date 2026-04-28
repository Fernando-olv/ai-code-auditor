import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.findings import Severity
from app.schemas.llm_review import (
    LlmReviewerResponse,
    parse_llm_reviewer_response,
)


def test_parse_llm_reviewer_response_ok() -> None:
    raw = (
        '{"summary":"ok","findings":[{"rule_id":"llm.reviewer","severity":"high",'
        '"category":"security","file_path":"app/x.py","line_start":2,"line_end":3,'
        '"title":"t","description":"d","suggestion":"s","confidence":0.9}]}'
    )
    got = parse_llm_reviewer_response(raw)
    assert isinstance(got, LlmReviewerResponse)
    assert got.summary == "ok"
    assert len(got.findings) == 1
    assert got.findings[0].severity == Severity.high


def test_parse_strips_json_fences() -> None:
    text = '```json\n{"summary":"","findings":[]}\n```'
    got = parse_llm_reviewer_response(text)
    assert got.findings == []


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_llm_reviewer_response("not json {")


def test_parse_wrong_shape_raises() -> None:
    with pytest.raises(ValidationError):
        parse_llm_reviewer_response('{"summary":"x","findings":"nope"}')


def test_fixture_valid_reviewer_json() -> None:
    path = Path(__file__).resolve().parents[1] / "fixtures" / "llm_outputs" / "valid_reviewer.json"
    got = parse_llm_reviewer_response(path.read_text(encoding="utf-8"))
    assert got.summary
    assert got.findings[0].file_path == "app/main.py"
