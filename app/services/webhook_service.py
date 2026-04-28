"""Webhook verification and parsing services."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from app.domain.webhooks import PullRequestEvent

PR_ACTIONS_RUN_ANALYSIS = frozenset({"opened", "synchronize", "reopened"})


def pull_request_action_triggers_analysis(action: str) -> bool:
    """Return True when the webhook should enqueue a full PR analysis + feedback."""

    return action in PR_ACTIONS_RUN_ANALYSIS


def verify_github_signature(body: bytes, signature_256: str, secret: str) -> bool:
    """Verify GitHub `X-Hub-Signature-256` against the raw request body.

    GitHub formats this header as: "sha256=<hex_digest>".
    """

    if not secret:
        return False

    if not signature_256:
        return False

    prefix = "sha256="
    if not signature_256.startswith(prefix):
        return False

    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    provided = signature_256[len(prefix) :]
    return hmac.compare_digest(provided, expected)


def parse_pull_request_event(payload: dict[str, Any]) -> PullRequestEvent:
    """Extract the minimal PR event fields needed for later milestones."""

    repository = payload["repository"]
    pull_request = payload["pull_request"]
    head = pull_request["head"]

    return PullRequestEvent(
        action=payload["action"],
        repository_full_name=repository["full_name"],
        pr_number=pull_request["number"],
        head_sha=head["sha"],
        html_url=pull_request.get("html_url"),
    )
