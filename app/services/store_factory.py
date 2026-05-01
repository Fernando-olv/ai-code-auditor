"""Construct an :class:`AnalysisStore` from :class:`Settings`.

Returns ``None`` when persistence is not configured (no Firestore project and no
emulator). Callers treat ``None`` as "skip persistence" without crashing.
"""

from __future__ import annotations

import os

from app.core.config import Settings
from app.ports.analysis_store import AnalysisStore
from app.vendor.firestore import FirestoreAnalysisStore


def persistence_enabled(settings: Settings) -> bool:
    """True when a Firestore client can be constructed for this process."""

    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        return True
    return bool(settings.google_cloud_project.strip())


def build_analysis_store(settings: Settings) -> AnalysisStore | None:
    """Return a Firestore-backed store, or ``None`` when not configured."""

    if not persistence_enabled(settings):
        return None
    return FirestoreAnalysisStore.from_settings(settings)
