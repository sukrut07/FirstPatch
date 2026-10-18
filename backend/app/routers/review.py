from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.app.services.review_simulator_service import review_simulator
from backend.app.services.flight_recorder_service import flight_recorder

router = APIRouter(prefix="/api/review", tags=["PR Review Simulator"])

class AnalyzeDiffRequest(BaseModel):
    diff: str
    workspace_id: Optional[str] = None
    repository_id: Optional[str] = "local"

@router.post("/analyze-diff")
async def analyze_diff(req: AnalyzeDiffRequest):
    result = review_simulator.analyze_diff(req.diff, workspace_id=req.workspace_id)

    if req.workspace_id:
        flight_recorder.log_event(
            workspace_id=req.workspace_id,
            repository_id=req.repository_id or "local",
            event_type="PR_REVIEW",
            summary=f"PR Review Simulator analyzed diff: {result['findings_count']} findings, status: {result['overall_status']}.",
            verification_status="REVIEWED"
        )

    return result
