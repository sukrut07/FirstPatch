from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.app.services.verification_service import verification_service
from backend.app.services.setup_doctor_service import setup_doctor
from backend.app.services.flight_recorder_service import flight_recorder
from backend.app.database import get_db

router = APIRouter(prefix="/api/verification", tags=["Verification & Sandbox"])

class RunTestRequest(BaseModel):
    command: str
    workspace_id: Optional[str] = None
    repository_id: Optional[str] = "local"
    cwd: Optional[str] = None

class DiagnoseErrorRequest(BaseModel):
    error_log: str
    language: Optional[str] = "Python"

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
async def execute_verification_test(req: RunTestRequest):
    result = verification_service.run_safe_command(
        command_str=req.command,
        workspace_id=req.workspace_id,
        repository_id=req.repository_id or "local",
        cwd=req.cwd
    )

    # Log to Flight Recorder if associated with a workspace
    if req.workspace_id:
        flight_recorder.log_event(
            workspace_id=req.workspace_id,
            repository_id=req.repository_id or "local",
            event_type="VERIFY",
            summary=f"Ran verification command `{req.command}` -> {result['status']} (exit code {result['exit_code']}).",
            details=f"Duration: {result['duration_ms']}ms\nSTDOUT: {result['stdout'][:400]}\nSTDERR: {result['stderr'][:400]}",
            verification_status=result["status"]
        )

    return result

@router.post("/diagnose-error")
async def diagnose_setup_error(req: DiagnoseErrorRequest):
    return setup_doctor.diagnose_error(req.error_log, repo_language=req.language or "Python")
