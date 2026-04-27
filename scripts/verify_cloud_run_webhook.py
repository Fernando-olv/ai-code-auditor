"""Sign a minimal ping body with the current Secret Manager value and POST to Cloud Run.

Usage (from repo root, with gcloud auth):
  python scripts/verify_cloud_run_webhook.py
"""

from __future__ import annotations

import hashlib
import hmac
import shutil
import subprocess
import urllib.error
import urllib.request

from app.core.config import Settings
from app.services.webhook_service import verify_github_signature


def gcloud() -> str:
    return shutil.which("gcloud") or (
        r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    )


def main() -> int:
    project = "ai-auditor-494202"
    url = "https://ai-code-auditor-715782179680.us-central1.run.app/webhooks/github"
    body = b"{}"

    raw = subprocess.check_output(
        [
            gcloud(),
            "secrets",
            "versions",
            "access",
            "latest",
            "--secret=github-webhook-secret",
            f"--project={project}",
        ],
        text=False,
    )
    secret_model = Settings(github_webhook_secret=raw.decode("utf-8"))
    normalized = secret_model.github_webhook_secret

    print("secret_bytes", len(raw), "after_model_strip", len(normalized))

    sig = "sha256=" + hmac.new(normalized.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert verify_github_signature(body, sig, normalized)

    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": "verify-cloud-run",
            "X-Hub-Signature-256": sig,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("status", resp.status, "body", resp.read().decode())
    except urllib.error.HTTPError as exc:
        print("status", exc.code, "body", exc.read().decode())
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
