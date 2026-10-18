import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.app.database import get_db, get_iso_now

router = APIRouter(tags=["Learning & Settings"])

class UpdateProfileRequest(BaseModel):
    skill_level: Optional[str] = "Beginner"
    preferred_languages: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    learning_goals: Optional[str] = None

@router.get("/api/learning/profile")
async def get_learning_profile():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM learning_profiles WHERE id = 'default'")
        row = cursor.fetchone()
        if not row:
            return {
                "id": "default",
                "skill_level": "Beginner",
                "preferred_languages": ["Python", "TypeScript"],
                "interests": ["Web", "DevTools"],
                "learning_goals": "Make my first verified open source contribution",
                "completed_drills_count": 0
            }
        item = dict(row)
        try:
            item["preferred_languages"] = json.loads(item["preferred_languages"])
        except Exception:
            item["preferred_languages"] = []
        try:
            item["interests"] = json.loads(item["interests"])
        except Exception:
            item["interests"] = []
        return item

@router.patch("/api/learning/profile")
async def update_learning_profile(req: UpdateProfileRequest):
    now = get_iso_now()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE learning_profiles
        SET skill_level = COALESCE(?, skill_level),
            preferred_languages = COALESCE(?, preferred_languages),
            interests = COALESCE(?, interests),
            learning_goals = COALESCE(?, learning_goals),
            updated_at = ?
        WHERE id = 'default'
        """, (
            req.skill_level,
            json.dumps(req.preferred_languages) if req.preferred_languages is not None else None,
            json.dumps(req.interests) if req.interests is not None else None,
            req.learning_goals,
            now
        ))
    return {"status": "updated"}

@router.get("/api/settings/privacy")
async def get_privacy_settings():
    return {
        "local_inference_default": True,
        "external_network_requests": [
            "GitHub REST API (public metadata & open issues)",
            "Local Ollama API (http://127.0.0.1:11434)"
        ],
        "telemetry_enabled": False,
        "storage_mode": "Local SQLite (WAL mode)",
        "security_sandbox": "Subprocess with timeout, environment sanitation & resource bounds"
    }

@router.post("/api/settings/reset-database")
async def reset_database():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM verification_runs")
        cursor.execute("DELETE FROM contribution_events")
        cursor.execute("DELETE FROM contribution_steps")
        cursor.execute("DELETE FROM contribution_workspaces")
        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM conversations")
        cursor.execute("DELETE FROM evidence_records")
        cursor.execute("DELETE FROM code_chunks")
        cursor.execute("DELETE FROM repository_files")
        cursor.execute("DELETE FROM repository_snapshots")
        cursor.execute("DELETE FROM issue_recommendations")
        cursor.execute("DELETE FROM issues")
        cursor.execute("DELETE FROM saved_issues")
        cursor.execute("DELETE FROM saved_repositories")
        cursor.execute("DELETE FROM repositories")
    return {"status": "reset_successful", "message": "All local repository indexes and workspaces cleared."}
