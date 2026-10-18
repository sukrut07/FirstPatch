from __future__ import annotations

import os
import sys
from uuid import UUID
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.app.services.verification_service import verification_service
from backend.app.services.setup_doctor_service import setup_doctor
from backend.app.services.flight_recorder_service import flight_recorder
from backend.app.database import get_db

try:
    from app.schemas import CheckStatus, VerificationCheck, VerificationStatus
    from app.schemas.verification import (
        ExecutionStatus,
        VerificationInfrastructureHealth,
        VerificationRunRecord,
        VerificationRunRequest,
        RuntimeProfile,
    )
    from app.services.verification import (
        IsolatedVerificationService,
        get_verification_service,
        get_verification_store,
    )
    HAS_ISOLATED_VERIFICATION = True
except Exception:
    HAS_ISOLATED_VERIFICATION = False

router = APIRouter(prefix="/api/verification", tags=["Verification & Sandbox"])

class RunTestRequest(BaseModel):
    command: str
    workspace_id: Optional[str] = None
    repository_id: Optional[str] = "local"
    cwd: Optional[str] = None

class DiagnoseErrorRequest(BaseModel):
    error_log: str
    language: Optional[str] = "Python"

@router.get("/health")
async def get_verification_health():
    """
    Check availability of the isolated execution sandbox infrastructure.
    Returns status and whether container sandboxing is safely active.
    """
    if HAS_ISOLATED_VERIFICATION:
        service = get_verification_service()
        return service.check_health()
    return {
        "runtime_available": False,
        "isolation_level": "none",
        "supported_profiles": [],
        "host_execution_permitted": False,
        "message": "Isolated container runtime is not configured"
    }

@router.get("/tests")
async def discover_tests_for_repo(owner: str, repo: str):
    repo_id = f"{owner}/{repo}"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM repository_files WHERE repository_id = ?", (repo_id,))
        file_paths = [r["path"] for r in cursor.fetchall()]

    tests = verification_service.discover_tests(file_paths)
    return {
        "repository_id": repo_id,
        "discovered_commands": tests
    }

@router.post("/run")
async def execute_or_submit_verification(payload: Dict[str, Any], response: Response):
    """
    Unified verification run endpoint:
    - If `command` is present: executes safe pre-flight runner and logs to Flight Recorder (returns 200).
    - If `owner`/`repo` is present: executes isolated container verification sandbox (returns 202).
    """
    if "command" in payload:
        command = payload["command"]
        workspace_id = payload.get("workspace_id")
        repository_id = payload.get("repository_id") or "local"
        cwd = payload.get("cwd")

        result = verification_service.run_safe_command(
            command_str=command,
            workspace_id=workspace_id,
            repository_id=repository_id,
            cwd=cwd
        )

        if workspace_id:
            flight_recorder.log_event(
                workspace_id=workspace_id,
                repository_id=repository_id,
                event_type="VERIFY",
                summary=f"Ran verification command `{command}` -> {result['status']} (exit code {result['exit_code']}).",
                details=f"Duration: {result['duration_ms']}ms\nSTDOUT: {result['stdout'][:400]}\nSTDERR: {result['stderr'][:400]}",
                verification_status=result["status"]
            )
        response.status_code = status.HTTP_200_OK
        return result

    if HAS_ISOLATED_VERIFICATION and "owner" in payload and "repo" in payload:
        response.status_code = status.HTTP_202_ACCEPTED
        try:
            req = VerificationRunRequest(**payload)
        except Exception as e:
            raise HTTPException(status_code=422, detail=str(e))

        service = get_verification_service()
        health = service.check_health()
        if not health.runtime_available:
            record = VerificationRunRecord(
                session_id=req.session_id,
                owner=req.owner,
                repo=req.repo,
                commit_sha=req.commit_sha,
                runtime=req.runtime,
                test_target=req.test_target,
                status=ExecutionStatus.UNAVAILABLE,
                error_summary=f"Isolated verification runtime is unavailable: {health.message}",
                warnings=["No container sandbox is available on host. Host execution is prohibited."],
            )
            service.store.save(record)
            return record

        return await service.execute_verification(req)

    raise HTTPException(status_code=422, detail="Invalid verification request payload")

@router.get("/runs/{run_id}")
async def get_verification_run(run_id: UUID):
    """Retrieve an existing verification run record by ID."""
    if not HAS_ISOLATED_VERIFICATION:
        raise HTTPException(status_code=404, detail="Isolated verification not enabled")
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
    if not HAS_ISOLATED_VERIFICATION:
        raise HTTPException(status_code=404, detail="Isolated verification not enabled")
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

@router.post("/diagnose-error")
async def diagnose_setup_error(req: DiagnoseErrorRequest):
    return setup_doctor.diagnose_error(req.error_log, repo_language=req.language or "Python")

@router.get("/{session_id}")
async def get_verification_status(session_id: UUID):
    """
    Get verification status for a contribution session.
    Inspects whether actual verified execution records exist for the session.
    """
    if not HAS_ISOLATED_VERIFICATION:
        raise HTTPException(status_code=404, detail="Isolated verification not enabled")
    store = get_verification_store()
    service = get_verification_service()
    health = service.check_health()

    records = store.get_for_session(session_id)
    latest_run = records[0] if records else None

    checks = []
    blockers = []

    if latest_run:
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
