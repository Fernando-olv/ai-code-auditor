"""Firestore client factory (GCP ADC or local emulator)."""

from __future__ import annotations

import os

from google.cloud import firestore

from app.core.config import Settings


def create_firestore_client(settings: Settings | None = None) -> firestore.Client:
    """Return a Firestore client.

    When ``FIRESTORE_EMULATOR_HOST`` is set (standard env var), the client library
    talks to the emulator. If ``google_cloud_project`` is empty in that mode, a
    placeholder project id is used so local tests can run without ADC.
    """

    cfg = settings or Settings()
    emulator = os.environ.get("FIRESTORE_EMULATOR_HOST")
    project = cfg.google_cloud_project or None
    if emulator and not project:
        project = "demo-ai-auditor"

    database = (cfg.firestore_database_id or "").strip()
    kwargs: dict[str, str] = {}
    if project:
        kwargs["project"] = project
    if database and database != "(default)":
        kwargs["database"] = database
    return firestore.Client(**kwargs)
