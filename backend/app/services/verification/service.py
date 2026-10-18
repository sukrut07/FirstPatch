"""
FirstPatch AI — Isolated Verification Service (Phase 3)

Coordinates safe, isolated test execution for contribution verification:
- Enforces state machine transitions (QUEUED -> PREPARING -> RUNNING -> PASSED/FAILED/TIMED_OUT)
- Enforces concurrency ceiling (max 3 parallel verification jobs)
- Validates repository snapshot consistency
- Dispatches execution to container or mock driver
- Parses execution logs into structured test counts
- Ensures workspace cleanup in all cases
- Stores verifiable records indexed by commit SHA
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.schemas.verification import (
    ExecutionStatus,
    RuntimeProfile,
    VALID_TRANSITIONS,
    VerificationInfrastructureHealth,
    VerificationRunRecord,
    VerificationRunRequest,
    VerificationTestCounts,
)
from app.services.verification.parser import JestNpmOutputParser, PytestOutputParser
from app.services.verification.runner import (
    BaseExecutionDriver,
    DockerExecutionDriver,
    MAX_OUTPUT_BYTES,
)
from app.services.verification.store import VerificationRecordStore, get_verification_store

logger = logging.getLogger(__name__)

# Max parallel verification runs allowed to prevent resource exhaustion
MAX_CONCURRENT_RUNS = 3


class IsolatedVerificationService:
    """Core verification service managing test sandboxes and execution records."""

    def __init__(
        self,
        driver: Optional[BaseExecutionDriver] = None,
        store: Optional[VerificationRecordStore] = None,
    ):
        self._driver = driver or DockerExecutionDriver()
        self._store = store or get_verification_store()
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_RUNS)

    @property
    def driver(self) -> BaseExecutionDriver:
        return self._driver

    @property
    def store(self) -> VerificationRecordStore:
        return self._store

    def check_health(self) -> VerificationInfrastructureHealth:
        """Checks container infrastructure availability."""
        return self._driver.check_availability()

    def get_run(self, run_id: UUID) -> Optional[VerificationRunRecord]:
        """Retrieves a verification record by ID."""
        return self._store.get(run_id)

    def cancel_run(self, run_id: UUID) -> bool:
        """Attempts to cancel a running verification job."""
        record = self._store.get(run_id)
        if not record or record.is_finished:
            return False

        cancelled = self._driver.cancel(run_id)
        if cancelled or record.status in {ExecutionStatus.QUEUED, ExecutionStatus.PREPARING, ExecutionStatus.RUNNING}:
            now = datetime.now(timezone.utc)
            updated = record.model_copy(
                update={
                    "status": ExecutionStatus.CANCELLED,
                    "finished_at": now,
                    "error_summary": "Verification was cancelled by user request.",
                }
            )
            self._store.save(updated)
            return True
        return False

    async def execute_verification(
        self,
        request: VerificationRunRequest,
        source_snapshot_path: Optional[str] = None,
    ) -> VerificationRunRecord:
        """
        Executes a verification run asynchronously with state tracking and sandbox isolation.
        """
        record = VerificationRunRecord(
            session_id=request.session_id,
            owner=request.owner,
            repo=request.repo,
            commit_sha=request.commit_sha,
            runtime=request.runtime,
            test_target=request.test_target,
            status=ExecutionStatus.QUEUED,
        )
        self._store.save(record)

        # 1. Capability check
        health = self.check_health()
        if not health.runtime_available:
            return self._finalize_run(
                record,
                status=ExecutionStatus.UNAVAILABLE,
                error_summary=f"Isolated verification runtime is unavailable: {health.message}",
                warnings=["Verification skipped because no safe container sandbox is available."],
            )

        # 2. Check concurrency
        try:
            # Wait up to 5s for semaphore
            async with asyncio.timeout(5.0):
                await self._semaphore.acquire()
        except TimeoutError:
            return self._finalize_run(
                record,
                status=ExecutionStatus.BLOCKED,
                error_summary="Maximum concurrent verification jobs reached. Please retry shortly.",
            )

        workspace_path: Optional[str] = None
        start_mono = time.monotonic()
        final_record: Optional[VerificationRunRecord] = None

        try:
            # 3. Transition to PREPARING
            record = self._transition_state(record, ExecutionStatus.PREPARING)

            try:
                workspace_path = await asyncio.to_thread(
                    self._driver.prepare_workspace,
                    request.owner,
                    request.repo,
                    request.commit_sha,
                    source_snapshot_path,
                )
            except Exception as prep_exc:
                final_record = self._finalize_run(
                    record,
                    status=ExecutionStatus.BLOCKED,
                    error_summary=f"Failed to prepare isolated workspace: {str(prep_exc)}",
                )
            else:
                # 4. Transition to RUNNING
                record = self._transition_state(record, ExecutionStatus.RUNNING)

                # 5. Dispatch execution to driver in background thread
                exit_code, stdout, stderr, timed_out = await asyncio.to_thread(
                    self._driver.execute,
                    record.run_id,
                    request,
                    workspace_path,
                )

                # 6. Bound outputs to MAX_OUTPUT_BYTES
                bounded_stdout = self._bound_text(stdout)
                bounded_stderr = self._bound_text(stderr)

                # 7. Check timeout
                if timed_out:
                    final_record = self._finalize_run(
                        record,
                        status=ExecutionStatus.TIMED_OUT,
                        exit_code=exit_code,
                        stdout=bounded_stdout,
                        stderr=bounded_stderr,
                        error_summary=f"Execution timed out after {request.timeout_seconds}s limit.",
                    )
                else:
                    # 8. Parse runner output
                    if request.runtime == RuntimeProfile.PYTHON_PYTEST:
                        counts, error_summary = PytestOutputParser.parse(bounded_stdout, bounded_stderr)
                    else:
                        counts, error_summary = JestNpmOutputParser.parse(bounded_stdout, bounded_stderr)

                    # 9. Determine success: process must have exit_code 0 AND no failures/errors
                    if exit_code == 0 and counts.failed == 0 and counts.errors == 0:
                        final_status = ExecutionStatus.PASSED
                    else:
                        final_status = ExecutionStatus.FAILED
                        if not error_summary:
                            error_summary = f"Runner process exited with code {exit_code}."

                    final_record = self._finalize_run(
                        record,
                        status=final_status,
                        exit_code=exit_code,
                        counts=counts,
                        stdout=bounded_stdout,
                        stderr=bounded_stderr,
                        error_summary=error_summary,
                    )

        finally:
            self._semaphore.release()
            # 10. Perform cleanup unconditionally
            if workspace_path:
                cleaned, cleanup_err = await asyncio.to_thread(
                    self._driver.cleanup,
                    workspace_path,
                )
                current = self._store.get(record.run_id) or final_record
                if current:
                    updated = current.model_copy(
                        update={
                            "cleanup_performed": cleaned,
                            "cleanup_error": cleanup_err,
                            "duration_ms": int((time.monotonic() - start_mono) * 1000),
                        }
                    )
                    self._store.save(updated)
                    final_record = updated

        return final_record or self._store.get(record.run_id) or record

    def _transition_state(
        self, record: VerificationRunRecord, new_status: ExecutionStatus
    ) -> VerificationRunRecord:
        """Validates and applies a state machine transition."""
        allowed = VALID_TRANSITIONS.get(record.status, set())
        if new_status not in allowed:
            logger.warning(
                "Invalid verification transition attempted: %s -> %s for run %s",
                record.status,
                new_status,
                record.run_id,
            )
            return record

        updated = record.model_copy(update={"status": new_status})
        self._store.save(updated)
        return updated

    def _finalize_run(
        self,
        record: VerificationRunRecord,
        status: ExecutionStatus,
        exit_code: Optional[int] = None,
        counts: Optional[VerificationTestCounts] = None,
        stdout: str = "",
        stderr: str = "",
        error_summary: Optional[str] = None,
        warnings: Optional[list[str]] = None,
    ) -> VerificationRunRecord:
        now = datetime.now(timezone.utc)
        start_ts = record.started_at
        duration_ms = int((now - start_ts).total_seconds() * 1000)

        updated = record.model_copy(
            update={
                "status": status,
                "exit_code": exit_code,
                "counts": counts,
                "stdout": stdout,
                "stderr": stderr,
                "error_summary": error_summary,
                "finished_at": now,
                "duration_ms": duration_ms,
                "warnings": warnings or record.warnings,
            }
        )
        self._store.save(updated)
        return updated

    @staticmethod
    def _bound_text(text: str) -> str:
        if len(text) > MAX_OUTPUT_BYTES:
            marker = "\n[... OUTPUT TRUNCATED AT 50KB BOUNDARY ...]\n"
            return text[:MAX_OUTPUT_BYTES - len(marker)] + marker
        return text


# Global service instance
_default_service: Optional[IsolatedVerificationService] = None


def get_verification_service() -> IsolatedVerificationService:
    global _default_service
    if _default_service is None:
        _default_service = IsolatedVerificationService()
    return _default_service
