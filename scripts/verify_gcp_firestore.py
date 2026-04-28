#!/usr/bin/env python3
"""Write/read a canary document in Firestore using Application Default Credentials.

Requires ``GOOGLE_CLOUD_PROJECT``. Intended for operators after Cloud Run / IAM setup.
Clears ``FIRESTORE_EMULATOR_HOST`` so the client targets real GCP.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime


def main() -> int:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project:
        print("error: GOOGLE_CLOUD_PROJECT is required", file=sys.stderr)
        return 1

    # Ensure we hit production / project Firestore, not a leftover emulator env.
    os.environ.pop("FIRESTORE_EMULATOR_HOST", None)

    from google.auth import default as google_auth_default
    from google.cloud import firestore

    google_auth_default()
    client = firestore.Client(project=project)
    doc_id = str(uuid.uuid4())
    ref = client.collection("ops_smoke").document(doc_id)
    payload = {"created_at": datetime.now(UTC), "source": "cloudrun_smoke"}
    ref.set(payload)
    snap = ref.get()
    if not snap.exists:
        print("error: document missing after write", file=sys.stderr)
        return 1
    data = snap.to_dict() or {}
    if data.get("source") != "cloudrun_smoke":
        print("error: unexpected document payload", file=sys.stderr)
        return 1
    ref.delete()
    print(f"ok: wrote and read ops_smoke/{doc_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
