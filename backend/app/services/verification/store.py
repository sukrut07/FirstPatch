"""
FirstPatch AI — Verification Record Store (Phase 3)

Thread-safe in-memory store for verification execution records, indexed by:
- run_id (primary key)
- (owner, repo, commit_sha) (for snapshot-bound reality checking)
- session_id (for contribution workflow association)
"""
from __future__ import annotations

import threading
from typing import Optional
from uuid import UUID

from app.schemas.verification import VerificationRunRecord


class VerificationRecordStore:
    """Thread-safe in-memory verification repository."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[UUID, VerificationRunRecord] = {}
        # Index: (owner.lower(), repo.lower(), commit_sha.lower()) -> list of run_ids
        self._commit_index: dict[tuple[str, str, str], list[UUID]] = {}
        # Index: session_id -> list of run_ids
        self._session_index: dict[UUID, list[UUID]] = {}

    def save(self, record: VerificationRunRecord) -> None:
        """Stores or updates a verification run record."""
        with self._lock:
            self._runs[record.run_id] = record

            # Update commit index
            commit_key = (
                record.owner.strip().lower(),
                record.repo.strip().lower(),
                record.commit_sha.strip().lower(),
            )
            if commit_key not in self._commit_index:
                self._commit_index[commit_key] = []
            if record.run_id not in self._commit_index[commit_key]:
                self._commit_index[commit_key].append(record.run_id)

            # Update session index if session_id is provided
            if record.session_id:
                if record.session_id not in self._session_index:
                    self._session_index[record.session_id] = []
                if record.run_id not in self._session_index[record.session_id]:
                    self._session_index[record.session_id].append(record.run_id)

    def get(self, run_id: UUID) -> Optional[VerificationRunRecord]:
        """Retrieves a verification record by its run ID."""
        with self._lock:
            return self._runs.get(run_id)

    def get_latest_for_commit(
        self, owner: str, repo: str, commit_sha: str
    ) -> Optional[VerificationRunRecord]:
        """
        Retrieves the most recent verification record matching the exact snapshot commit SHA.
        """
        commit_key = (
            owner.strip().lower(),
            repo.strip().lower(),
            commit_sha.strip().lower(),
        )
        with self._lock:
            run_ids = self._commit_index.get(commit_key, [])
            if not run_ids:
                return None
            # Return the run with the latest started_at timestamp
            runs = [self._runs[rid] for rid in run_ids if rid in self._runs]
            if not runs:
                return None
            runs.sort(key=lambda r: r.started_at, reverse=True)
            return runs[0]

    def get_for_session(self, session_id: UUID) -> list[VerificationRunRecord]:
        """Retrieves all verification records associated with a contribution session."""
        with self._lock:
            run_ids = self._session_index.get(session_id, [])
            runs = [self._runs[rid] for rid in run_ids if rid in self._runs]
            runs.sort(key=lambda r: r.started_at, reverse=True)
            return runs

    def list_runs(self, limit: int = 50) -> list[VerificationRunRecord]:
        """Returns recent verification runs up to the specified limit."""
        with self._lock:
            all_runs = list(self._runs.values())
            all_runs.sort(key=lambda r: r.started_at, reverse=True)
            return all_runs[:limit]

    def clear(self) -> None:
        """Utility for test isolation."""
        with self._lock:
            self._runs.clear()
            self._commit_index.clear()
            self._session_index.clear()


# Global singleton instance
_default_store = VerificationRecordStore()


def get_verification_store() -> VerificationRecordStore:
    return _default_store
