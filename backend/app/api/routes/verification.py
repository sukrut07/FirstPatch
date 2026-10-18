"""
FirstPatch AI — Verification Routes (Phase 3)

Provides isolated verification API endpoints:
- GET  /api/verification/health -> Runtime sandbox capability status
- POST /api/verification/run    -> Submit an isolated verification run
- GET  /api/verification/runs/{run_id} -> Retrieve run record & bounded logs
- POST /api/verification/runs/{run_id}/cancel -> Cancel active run
- GET  /api/verification/{session_id} -> Contribution session verification status
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas import CheckStatus, VerificationCheck, VerificationStatus
from app.schemas.verification import (
    ExecutionStatus,
    VerificationInfrastructureHealth,
    VerificationRunRecord,
    VerificationRunRequest,
)
from app.services.verification import (
    IsolatedVerificationService,
    get_verification_service,
    get_verification_store,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["verification"])


@router.get("/health", response_model=VerificationInfrastructureHealth)
async def get_verification_health() -> VerificationInfrastructureHealth:
    """
    Check availability of the isolated execution sandbox infrastructure.
    Returns status and whether container sandboxing is safely active.
    """
    service = get_verification_service()
    return service.check_health()


@router.post("/run", response_model=VerificationRunRecord, status_code=status.HTTP_202_ACCEPTED)
async def submit_verification_run(
    request: VerificationRunRequest,
) -> VerificationRunRecord:
    """
    Submit an isolated verification run for a repository snapshot.
    Enforces allowlisted runtime profile and sanitized test targets.
    """
    service = get_verification_service()

    # Reject if runtime is unavailable
    health = service.check_health()
    if not health.runtime_available:
        # Return structured UNAVAILABLE record rather than failing silently
        record = VerificationRunRecord(
            session_id=request.session_id,
            owner=request.owner,
            repo=request.repo,
            commit_sha=request.commit_sha,
            runtime=request.runtime,
            test_target=request.test_target,
            status=ExecutionStatus.UNAVAILABLE,
            error_summary=f"Isolated verification runtime is unavailable: {health.message}",
            warnings=["No container sandbox is available on host. Host execution is prohibited."],
        )
        service.store.save(record)
        return record

    return await service.execute_verification(request)


@router.get("/runs/{run_id}", response_model=VerificationRunRecord)
async def get_verification_run(run_id: UUID) -> VerificationRunRecord:
    """Retrieve an existing verification run record by ID."""
    service = get_verification_service()
    record = service.get_run(run_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification run '{run_id}' was not found.",
        )
    return record


@router.post("/runs/{run_id}/cancel")
async def cancel_verification_run(run_id: UUID) -> dict[str, bool]:
    """Attempt to cancel an ongoing verification run."""
    service = get_verification_service()
    success = service.cancel_run(run_id)
    if not success:
        record = service.get_run(run_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification run '{run_id}' not found.",
            )
        return {"cancelled": False}
    return {"cancelled": True}


@router.get("/{session_id}", response_model=VerificationStatus)
async def get_verification_status(session_id: UUID) -> VerificationStatus:
    """
    Get verification status for a contribution session.
    Inspects whether actual verified execution records exist for the session.
    """
    store = get_verification_store()
    service = get_verification_service()
    health = service.check_health()

    records = store.get_for_session(session_id)
    latest_run = records[0] if records else None

    checks = []
    blockers = []

    if latest_run:
        # We have an actual test run for this session
        if latest_run.status == ExecutionStatus.PASSED:
            t_status = CheckStatus.PASSED
            detail = f"Verified in sandbox: {latest_run.counts.passed if latest_run.counts else 0} passed (Run ID: {latest_run.run_id})."
        elif latest_run.status == ExecutionStatus.FAILED:
            t_status = CheckStatus.FAILED
            detail = f"Sandbox execution failed: {latest_run.error_summary}"
            blockers.append("Tests failed in isolated execution.")
        elif latest_run.status == ExecutionStatus.TIMED_OUT:
            t_status = CheckStatus.FAILED
            detail = "Sandbox execution timed out."
            blockers.append("Tests timed out.")
        elif latest_run.status == ExecutionStatus.UNAVAILABLE:
            t_status = CheckStatus.UNAVAILABLE
            detail = f"Sandbox unavailable: {latest_run.error_summary}"
            blockers.append("Sandbox unavailable.")
        else:
            t_status = CheckStatus.NOT_RUN
            detail = f"Execution status: {latest_run.status.value}"

        checks.append(
            VerificationCheck(
                name="test_suite",
                description="Run repository test suite in isolated sandbox",
                status=t_status,
                result_detail=detail,
            )
        )
    else:
        # No test run yet
        test_check_status = (
            CheckStatus.NOT_RUN if health.runtime_available else CheckStatus.UNAVAILABLE
        )
        test_detail = (
            "No isolated test run has been performed for this session yet."
            if health.runtime_available
            else f"Isolated container runtime unavailable: {health.message}"
        )
        checks.append(
            VerificationCheck(
                name="test_suite",
                description="Run repository test suite in isolated sandbox",
                status=test_check_status,
                result_detail=test_detail,
            )
        )
        if not health.runtime_available:
            blockers.append("Isolated container runtime unavailable on host.")

    # Static checks
    checks.append(
        VerificationCheck(
            name="lint_check",
            description="Run repository linter to check code style",
            status=CheckStatus.NOT_RUN,
            result_detail="Linting check to run alongside test targets.",
        )
    )
    checks.append(
        VerificationCheck(
            name="contribution_checklist",
            description="Basic contribution readiness checklist",
            status=CheckStatus.PASSED if (latest_run and latest_run.status == ExecutionStatus.PASSED) else CheckStatus.NOT_RUN,
            result_detail=(
                "Checklist: (1) Branch up to date. (2) Relevant tests passing. (3) Follows CONTRIBUTING.md."
            ),
        )
    )

    owner = latest_run.owner if latest_run else "unknown"
    repo = latest_run.repo if latest_run else "unknown"
    overall_ready = bool(latest_run and latest_run.status == ExecutionStatus.PASSED and not blockers)

    return VerificationStatus(
        session_id=session_id,
        owner=owner,
        repo=repo,
        checks=checks,
        overall_ready=overall_ready,
        blockers=blockers,
    )
