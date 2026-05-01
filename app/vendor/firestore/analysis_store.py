"""Firestore-backed :class:`AnalysisStore` implementation."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from google.cloud import firestore

from app.core.config import Settings
from app.domain.analysis_run import ANALYSIS_RUNS_COLLECTION, FINDINGS_SUBCOLLECTION
from app.vendor.firestore.client_factory import create_firestore_client


def _finding_doc_id(payload: dict[str, Any]) -> str:
    fid = payload.get("finding_id")
    if isinstance(fid, str) and fid.strip():
        return fid.strip()
    return uuid.uuid4().hex


class FirestoreAnalysisStore:
    """Thin Firestore adapter; sync client calls run in ``asyncio.to_thread``."""

    def __init__(self, client: firestore.Client) -> None:
        self._client = client

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> FirestoreAnalysisStore:
        return cls(create_firestore_client(settings))

    async def persist_analysis(
        self,
        analysis_id: str,
        run_payload: dict[str, Any],
        findings: list[dict[str, Any]],
    ) -> None:
        """Atomically write parent run document and all findings (single batch, MVP cap)."""

        def _persist() -> None:
            batch = self._client.batch()
            parent = self._client.collection(ANALYSIS_RUNS_COLLECTION).document(analysis_id)
            batch.set(parent, run_payload)
            sub = parent.collection(FINDINGS_SUBCOLLECTION)
            for finding in findings:
                doc_id = _finding_doc_id(finding)
                batch.set(sub.document(doc_id), finding)
            batch.commit()

        await asyncio.to_thread(_persist)

    async def get_analysis_run(self, analysis_id: str) -> dict[str, Any] | None:
        def _get() -> dict[str, Any] | None:
            snap = self._client.collection(ANALYSIS_RUNS_COLLECTION).document(analysis_id).get()
            if not snap.exists:
                return None
            data = snap.to_dict()
            return dict(data) if data is not None else None

        return await asyncio.to_thread(_get)

    async def list_findings(self, analysis_id: str) -> list[dict[str, Any]]:
        def _list() -> list[dict[str, Any]]:
            coll = (
                self._client.collection(ANALYSIS_RUNS_COLLECTION)
                .document(analysis_id)
                .collection(FINDINGS_SUBCOLLECTION)
            )
            rows: list[dict[str, Any]] = []
            for doc in coll.stream():
                row = doc.to_dict()
                if row is None:
                    continue
                rows.append(dict(row))
            rows.sort(
                key=lambda r: (
                    str(r.get("file_path") or ""),
                    str(r.get("finding_id") or ""),
                ),
            )
            return rows

        return await asyncio.to_thread(_list)
