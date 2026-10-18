import uuid
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.app.database import get_db, get_iso_now
from backend.app.services.flight_recorder_service import flight_recorder

router = APIRouter(prefix="/api/contributions", tags=["Contributions"])

class CreateContributionRequest(BaseModel):
    repository_id: str
    issue_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    steps: Optional[List[Dict[str, Any]]] = None

class UpdateStepRequest(BaseModel):
    status: str  # pending, in_progress, completed, skipped
    user_notes: Optional[str] = None

@router.post("")
async def create_contribution_workspace(req: CreateContributionRequest):
    ws_id = str(uuid.uuid4())
    now = get_iso_now()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO contribution_workspaces (
            id, repository_id, issue_id, title, description, status,
            definition_of_done, draft_pr_title, draft_pr_body, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, '', ?, ?)
        """, (
            ws_id, req.repository_id, req.issue_id, req.title, req.description,
            "All guided contribution steps completed and local tests verified.",
            f"fix: {req.title}", now, now
        ))

        # Default contribution steps if none supplied
        step_templates = req.steps or [
            {"title": "1. Understand Codebase & Trace Relevant Functions", "description": "Inspect grounded files and check function definitions.", "expected_result": "Problem isolated."},
            {"title": "2. Reproduce Behavior Locally", "description": "Run existing test suite or reproduce reported error.", "expected_result": "Reproduce expected error."},
            {"title": "3. Implement Scoped Fix", "description": "Apply minimal changes following repo conventions.", "expected_result": "Code changes made."},
            {"title": "4. Verify with Local Tests", "description": "Execute local verification suite to ensure tests pass.", "expected_result": "All tests pass with exit code 0."},
            {"title": "5. Prepare Pull Request", "description": "Generate Flight Recorder verified PR draft and review checklist.", "expected_result": "Ready for maintainer review."}
        ]

        for idx, s in enumerate(step_templates, start=1):
            step_id = str(uuid.uuid4())
            cursor.execute("""
            INSERT INTO contribution_steps (
                id, workspace_id, step_index, title, description, status,
                expected_result, verification_method, created_at
            ) VALUES (?, ?, ?, ?, ?, 'pending', ?, 'automated_or_manual', ?)
            """, (
                step_id, ws_id, idx, s.get("title", f"Step {idx}"),
                s.get("description", ""), s.get("expected_result", ""), now
            ))

    # Log initial flight recorder event
    flight_recorder.log_event(
        workspace_id=ws_id,
        repository_id=req.repository_id,
        event_type="PLAN",
        summary=f"Created contribution workspace for '{req.title}' with {len(step_templates)} steps."
    )

    return {
        "status": "created",
        "workspace_id": ws_id,
        "title": req.title,
        "repository_id": req.repository_id
    }

@router.get("")
async def list_contributions():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT w.*,
               (SELECT COUNT(*) FROM contribution_steps WHERE workspace_id = w.id) as total_steps,
               (SELECT COUNT(*) FROM contribution_steps WHERE workspace_id = w.id AND status = 'completed') as completed_steps
        FROM contribution_workspaces w
        ORDER BY w.updated_at DESC
        """)
        workspaces = [dict(r) for r in cursor.fetchall()]
        return workspaces

@router.get("/{contribution_id}")
async def get_contribution(contribution_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contribution_workspaces WHERE id = ?", (contribution_id,))
        ws = cursor.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Contribution workspace not found.")
        data = dict(ws)

        # Get steps
        cursor.execute("""
        SELECT * FROM contribution_steps
        WHERE workspace_id = ?
        ORDER BY step_index ASC
        """, (contribution_id,))
        data["steps"] = [dict(r) for r in cursor.fetchall()]

        # Get verification runs
        cursor.execute("""
        SELECT * FROM verification_runs
        WHERE workspace_id = ?
        ORDER BY created_at DESC
        LIMIT 10
        """, (contribution_id,))
        data["verification_runs"] = [dict(r) for r in cursor.fetchall()]

        # Get Flight Recorder events
        data["timeline"] = flight_recorder.get_timeline(contribution_id)

        return data

@router.patch("/{contribution_id}/steps/{step_id}")
async def update_step_status(contribution_id: str, step_id: str, req: UpdateStepRequest):
    now = get_iso_now()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contribution_steps WHERE id = ? AND workspace_id = ?", (step_id, contribution_id))
        step = cursor.fetchone()
        if not step:
            raise HTTPException(status_code=404, detail="Step not found in this workspace.")

        step_dict = dict(step)
        completed_at = now if req.status == "completed" else None

        cursor.execute("""
        UPDATE contribution_steps
        SET status = ?, user_notes = COALESCE(?, user_notes), completed_at = ?
        WHERE id = ?
        """, (req.status, req.user_notes, completed_at, step_id))

        cursor.execute("UPDATE contribution_workspaces SET updated_at = ? WHERE id = ?", (now, contribution_id))

    # Log to flight recorder
    flight_recorder.log_event(
        workspace_id=contribution_id,
        repository_id=step_dict.get("workspace_id", "local"),
        event_type="ATTEMPT" if req.status == "in_progress" else "VERIFY",
        summary=f"Step '{step_dict['title']}' updated to '{req.status}'.",
        details=req.user_notes or ""
    )

    return {"status": "updated", "step_id": step_id, "new_status": req.status}

@router.get("/{contribution_id}/timeline")
async def get_contribution_timeline(contribution_id: str):
    return flight_recorder.get_timeline(contribution_id)

@router.get("/{contribution_id}/report")
async def get_contribution_pr_report(contribution_id: str):
    return flight_recorder.generate_pr_draft(contribution_id)
