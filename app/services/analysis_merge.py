"""Combine outputs from deterministic rules and LLM review."""

from __future__ import annotations

from app.domain.findings import Finding


def concat_findings(
    deterministic: list[Finding],
    llm: list[Finding],
) -> list[Finding]:
    """Return deterministic findings first, then LLM findings (stable UX ordering)."""

    return list(deterministic) + list(llm)
