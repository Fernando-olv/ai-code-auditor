"""Load `ai/` prompt and memory files from the repository root."""

from __future__ import annotations

import os
from pathlib import Path


def _default_repo_root() -> Path:
    """`repo/app/services/prompt_loader.py` -> parents[2] == repo root."""

    return Path(__file__).resolve().parents[2]


def get_ai_repo_root() -> Path:
    """Return directory that contains the `ai/` folder (repo root by default)."""

    override = os.environ.get("AI_REPO_ROOT") or os.environ.get("AI_PROMPTS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return _default_repo_root()


def load_ai_text(*parts: str) -> str:
    """Read UTF-8 text from `ai/<parts>` under the resolved repo root."""

    path = get_ai_repo_root().joinpath("ai", *parts)
    return path.read_text(encoding="utf-8")


def load_review_system_prompt() -> str:
    """Main system prompt for the LLM reviewer."""

    return load_ai_text("prompts", "review_prompt.md")


def load_memory_snippets() -> tuple[str, str]:
    """Return (patterns_markdown, anti_patterns_markdown); empty strings if missing."""

    root = get_ai_repo_root() / "ai" / "memory"
    patterns = ""
    anti = ""
    p1 = root / "patterns.md"
    p2 = root / "anti_patterns.md"
    if p1.is_file():
        patterns = p1.read_text(encoding="utf-8")
    if p2.is_file():
        anti = p2.read_text(encoding="utf-8")
    return patterns, anti
