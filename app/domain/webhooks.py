"""Domain models for webhook events."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PullRequestEvent(BaseModel):
    action: str
    repository_full_name: str = Field(..., examples=["octo-org/octo-repo"])
    pr_number: int = Field(..., ge=1)
    head_sha: str = Field(..., min_length=7)
    html_url: str | None = None
