"""Replay a signed GitHub webhook payload against a running auditor instance.

Designed for local demos and smoke tests: reads a fixture from disk, signs it
with the configured webhook secret, and POSTs it to ``/webhooks/github``.
No GitHub account, tunnel, or PAT is required to exercise the receive path.

Examples (from repo root, with ``uvicorn main:app`` running locally):

    # default: pull_request opened against http://127.0.0.1:8000
    python scripts/replay_webhook.py

    # ping event (does not enqueue analysis, useful as a liveness check)
    python scripts/replay_webhook.py --event ping \
        --fixture tests/fixtures/github_webhooks/ping.json

    # point at Cloud Run
    python scripts/replay_webhook.py \
        --url https://ai-code-auditor-xxxx.run.app/webhooks/github
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "github_webhooks" / "pull_request_opened.json"
DEFAULT_URL = "http://127.0.0.1:8000/webhooks/github"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Webhook endpoint (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help=(
            f"Path to a JSON webhook payload (default: {DEFAULT_FIXTURE.relative_to(REPO_ROOT)})"
        ),
    )
    parser.add_argument(
        "--event",
        default="pull_request",
        help="X-GitHub-Event header value (default: pull_request)",
    )
    parser.add_argument(
        "--delivery",
        default="",
        help="X-GitHub-Delivery header value (default: random uuid4)",
    )
    parser.add_argument(
        "--secret",
        default=os.environ.get("GITHUB_WEBHOOK_SECRET", ""),
        help="Webhook secret (default: $GITHUB_WEBHOOK_SECRET)",
    )
    parser.add_argument("--timeout", type=float, default=15.0, help="Request timeout in seconds")
    return parser.parse_args(argv)


def sign_body(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.secret:
        print(
            "error: webhook secret missing. Pass --secret or set GITHUB_WEBHOOK_SECRET.",
            file=sys.stderr,
        )
        return 2

    if not args.fixture.exists():
        print(f"error: fixture not found: {args.fixture}", file=sys.stderr)
        return 2

    body = args.fixture.read_bytes()
    try:
        json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"error: fixture is not valid JSON: {exc}", file=sys.stderr)
        return 2

    delivery = args.delivery or f"local-{uuid.uuid4()}"
    signature = sign_body(body, args.secret)

    request = urllib.request.Request(
        args.url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ai-dev-auditor-replay/1.0",
            "X-GitHub-Event": args.event,
            "X-GitHub-Delivery": delivery,
            "X-Hub-Signature-256": signature,
        },
    )

    print(f"-> POST {args.url}")
    print(
        f"   event={args.event} delivery={delivery} fixture={args.fixture.name} bytes={len(body)}"
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            status = response.status
            payload = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        payload = exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        print(f"error: request failed: {exc.reason}", file=sys.stderr)
        return 1

    print(f"<- {status} {payload}")
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
