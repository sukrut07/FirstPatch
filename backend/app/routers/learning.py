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

@router.get("/api/learning/glossary")
async def get_beginner_glossary():
    """Returns a curated open-source terminology glossary for beginner developers."""
    return {
        "glossary": [
            {"term": "Repository (Repo)", "definition": "A folder managed by Git containing all project files, history, commits, and branches."},
            {"term": "Fork", "definition": "A personal copy of someone else's GitHub repository that lives on your account, allowing you to experiment freely without affecting the original project."},
            {"term": "Branch", "definition": "An independent line of development. Always create a new branch for your feature or bug fix instead of working on 'main'."},
            {"term": "Clone", "definition": "Downloading a complete copy of a remote GitHub repository to your local computer."},
            {"term": "Upstream", "definition": "The original open-source repository you forked from. Keeping your local branch synced with upstream prevents merge conflicts."},
            {"term": "Commit", "definition": "A recorded snapshot of your changes with an explanatory message describing what you modified and why."},
            {"term": "Pull Request (PR)", "definition": "A proposal submitted to the upstream project maintainers asking them to review and merge your changes into the main codebase."},
            {"term": "Code Review", "definition": "Maintainers reading your PR line-by-line, asking questions, requesting adjustments, and ensuring the change follows project conventions."},
            {"term": "Continuous Integration (CI)", "definition": "Automated pipelines that run linters and unit tests on every PR to verify that the change doesn't break existing functionality."},
            {"term": "Virtual Environment", "definition": "An isolated Python workspace that prevents package version conflicts between different projects on your computer."},
            {"term": "Linter / Formatter", "definition": "Tools (e.g. Ruff, Black, ESLint, Prettier) that automatically enforce consistent code formatting and flag syntax mistakes."},
            {"term": "Regression", "definition": "A bug that unintentionally breaks previously working functionality after a new change is introduced."},
            {"term": "DCO / CLA", "definition": "Developer Certificate of Origin (Signed-off-by) or Contributor License Agreement certifying that you have the right to contribute your code to the open-source project."}
        ]
    }

@router.get("/api/learning/contribution-sequence")
async def get_contribution_sequence():
    """Returns the visual 18-step open-source contribution lifecycle for beginners."""
    return {
        "sequence": [
            {"step": 1, "title": "Discover Project", "desc": "Identify a reputable, active project matching your interests."},
            {"step": 2, "title": "Read Project Overview", "desc": "Understand the project mission, target audience, and main technologies."},
            {"step": 3, "title": "Understand Architecture", "desc": "Explore the component diagram, entry points, and module responsibilities."},
            {"step": 4, "title": "Read CONTRIBUTING.md", "desc": "Check project contribution rules, branch naming, and commit style."},
            {"step": 5, "title": "Find Suitable Issue", "desc": "Choose an issue matching your skill level and available time."},
            {"step": 6, "title": "Check Claim-Safety", "desc": "Verify that no other contributor is already actively working on the task."},
            {"step": 7, "title": "Fork Repository", "desc": "Create a personal GitHub copy of the project to stage your work."},
            {"step": 8, "title": "Create Working Branch", "desc": "Create a dedicated Git branch (e.g., `fix/config-keyerror`)."},
            {"step": 9, "title": "Set Up Environment", "desc": "Install dependencies in an isolated virtual environment."},
            {"step": 10, "title": "Map Affected Code", "desc": "Locate exact functions and classes responsible for the issue."},
            {"step": 11, "title": "Design Minimal Fix", "desc": "Plan the smallest clean change that resolves the bug."},
            {"step": 12, "title": "Implement Changes", "desc": "Write code following project conventions and style."},
            {"step": 13, "title": "Add or Update Tests", "desc": "Add regression unit tests in `tests/` covering your change."},
            {"step": 14, "title": "Run Verification Suite", "desc": "Execute tests locally to ensure 100% pass rate."},
            {"step": 15, "title": "Review Diff", "desc": "Audit git diff for accidental prints or credentials."},
            {"step": 16, "title": "Commit Changes", "desc": "Write clear conventional commit messages."},
            {"step": 17, "title": "Open Pull Request", "desc": "Submit PR linking the issue (`Fixes #123`) with test proof."},
            {"step": 18, "title": "Respond to Review", "desc": "Politely address maintainer feedback until merged."}
        ]
    }

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
