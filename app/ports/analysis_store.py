"""Storage port: persistence contract for analysis runs and their findings."""

from __future__ import annotations

from typing import Any, Protocol


class AnalysisStore(Protocol):
    """Contract every vendor adapter (Firestore, in-memory, ...) must satisfy.

    The MVP keeps the surface intentionally small: persist a single run with its
    findings atomically, and read it back. Future adapters (Postgres, DynamoDB)
    can implement the same contract without rippling changes through services.
    """

    async def persist_analysis(
        self,
        analysis_id: str,
        run_payload: dict[str, Any],
        findings: list[dict[str, Any]],
    ) -> None:
        """Atomically write the run document and all its findings."""

    async def get_analysis_run(self, analysis_id: str) -> dict[str, Any] | None:
        """Return the run document or ``None`` when not found."""

    async def list_findings(self, analysis_id: str) -> list[dict[str, Any]]:
        """Return the findings for ``analysis_id``, deterministically ordered."""
