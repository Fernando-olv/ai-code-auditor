from unittest.mock import MagicMock

import pytest
from google.cloud import firestore

from app.vendor.firestore import FirestoreAnalysisStore


@pytest.mark.asyncio
async def test_persist_analysis_batch_writes_parent_and_finding() -> None:
    client = MagicMock(spec=firestore.Client)
    batch = MagicMock()
    client.batch.return_value = batch

    runs_col = MagicMock()
    parent_doc = MagicMock()
    findings_col = MagicMock()
    finding_doc = MagicMock()

    client.collection.return_value = runs_col
    runs_col.document.return_value = parent_doc
    parent_doc.collection.return_value = findings_col
    findings_col.document.return_value = finding_doc

    store = FirestoreAnalysisStore(client)
    await store.persist_analysis(
        "run-1",
        {"analysis_id": "run-1"},
        [{"finding_id": "fid-1", "rule_id": "r1", "file_path": "a.py"}],
    )

    client.collection.assert_called_once_with("analysis_runs")
    runs_col.document.assert_called_once_with("run-1")
    assert batch.set.call_count == 2
    findings_col.document.assert_called_once_with("fid-1")
    batch.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_analysis_run_returns_none_when_missing() -> None:
    client = MagicMock(spec=firestore.Client)
    runs_col = MagicMock()
    parent_doc = MagicMock()
    snap = MagicMock()
    snap.exists = False

    client.collection.return_value = runs_col
    runs_col.document.return_value = parent_doc
    parent_doc.get.return_value = snap

    store = FirestoreAnalysisStore(client)
    out = await store.get_analysis_run("missing")
    assert out is None


@pytest.mark.asyncio
async def test_list_findings_sorted_by_path_and_finding_id() -> None:
    client = MagicMock(spec=firestore.Client)
    runs_col = MagicMock()
    parent_doc = MagicMock()
    findings_col = MagicMock()

    d1 = MagicMock()
    d1.to_dict.return_value = {"file_path": "z.py", "finding_id": "a"}
    d2 = MagicMock()
    d2.to_dict.return_value = {"file_path": "a.py", "finding_id": "b"}

    client.collection.return_value = runs_col
    runs_col.document.return_value = parent_doc
    parent_doc.collection.return_value = findings_col
    findings_col.stream.return_value = [d1, d2]

    store = FirestoreAnalysisStore(client)
    rows = await store.list_findings("run-1")
    assert [r["file_path"] for r in rows] == ["a.py", "z.py"]
