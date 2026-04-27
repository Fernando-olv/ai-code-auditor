"""Normalized pull request context and deterministic file filtering."""

from __future__ import annotations

import fnmatch
from typing import Protocol

from pydantic import BaseModel, Field


class PullFileRow(Protocol):
    """Structural type for a GitHub pull file list row (avoids domain importing adapters)."""

    filename: str
    status: str
    sha: str
    additions: int
    deletions: int
    changes: int
    patch: str | None


class NormalizedChangedFile(BaseModel):
    """One changed file with optional unified diff patch."""

    path: str
    status: str
    sha: str
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: str | None = None


class NormalizedPrContext(BaseModel):
    """Stable contract for downstream rule and LLM analysis."""

    repository_full_name: str
    pr_number: int
    head_sha: str
    base_sha: str
    head_ref: str = ""
    base_ref: str = ""
    title: str = ""
    html_url: str | None = None
    author_login: str | None = None
    body: str | None = None
    files: list[NormalizedChangedFile] = Field(default_factory=list)
    partial_context: bool = False
    truncation_notes: list[str] = Field(default_factory=list)


class FileFilterConfig(BaseModel):
    """Caps and path rules for PR file lists."""

    max_files: int = 200
    max_patch_bytes_total: int = 512_000
    path_globs_deny: tuple[str, ...] = (
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "Pipfile.lock",
        "go.sum",
        "Cargo.lock",
        "*.min.js",
        "*.min.css",
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "*.webp",
        "*.ico",
        "*.pdf",
        "*.zip",
        "*.tar.gz",
    )


def split_repository_full_name(repository_full_name: str) -> tuple[str, str]:
    """Split `owner/name` into (`owner`, `repo`)."""

    parts = repository_full_name.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        msg = f"Invalid repository full_name: {repository_full_name!r}"
        raise ValueError(msg)
    return parts[0], parts[1]


def _path_matches_denylist(path: str, globs: tuple[str, ...]) -> bool:
    name = path.rsplit("/", maxsplit=1)[-1]
    for pattern in globs:
        if "/" in pattern:
            if fnmatch.fnmatchcase(path, pattern):
                return True
        else:
            if fnmatch.fnmatchcase(name, pattern) or fnmatch.fnmatchcase(path, pattern):
                return True
    return False


def filter_pull_files(
    files: list[PullFileRow],
    *,
    config: FileFilterConfig | None = None,
) -> tuple[list[NormalizedChangedFile], list[str]]:
    """Apply skip rules and size caps; return normalized files and human-readable notes."""

    cfg = config or FileFilterConfig()
    notes: list[str] = []
    out: list[NormalizedChangedFile] = []
    patch_bytes_total = 0

    for row in files:
        if row.patch is None:
            notes.append(f"skipped_no_patch:{row.filename}")
            continue
        if _path_matches_denylist(row.filename, cfg.path_globs_deny):
            notes.append(f"skipped_denylist:{row.filename}")
            continue

        patch_b = len(row.patch.encode("utf-8"))

        if len(out) >= cfg.max_files:
            notes.append("truncated_max_files")
            break

        if patch_bytes_total + patch_b > cfg.max_patch_bytes_total:
            notes.append("truncated_max_patch_bytes")
            break

        patch_bytes_total += patch_b
        out.append(
            NormalizedChangedFile(
                path=row.filename,
                status=row.status,
                sha=row.sha,
                additions=row.additions,
                deletions=row.deletions,
                changes=row.changes,
                patch=row.patch,
            ),
        )

    return out, notes
