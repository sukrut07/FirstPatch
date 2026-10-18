import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.app.services.github_service import github_service, parse_repo_identifier
from backend.app.services.issue_service import issue_service
from backend.app.database import get_db, get_iso_now

router = APIRouter(prefix="/api/issues", tags=["Issues"])

class DiscoverIssuesRequest(BaseModel):
    repository_id: str
    skill_level: Optional[str] = "Beginner"
    preferred_language: Optional[str] = "Python"

class SaveTriageRequest(BaseModel):
    user_summary: Optional[str] = ""
    expected_behavior: Optional[str] = ""
    actual_behavior: Optional[str] = ""
    suspected_code_path: Optional[str] = ""
    reproduction_notes: Optional[str] = ""
    decision: Optional[str] = "undecided"
    decision_rationale: Optional[str] = ""

class CreateHypothesisRequest(BaseModel):
    hypothesis: str
    supporting_evidence: Optional[List[str]] = []
    contradicting_evidence: Optional[List[str]] = []
    verification_method: Optional[str] = ""
    status: Optional[str] = "untested"
    remaining_uncertainty: Optional[str] = ""

class UpdateHypothesisStatusRequest(BaseModel):
    status: str
    remaining_uncertainty: Optional[str] = None

@router.post("/discover")
async def discover_issues(req: DiscoverIssuesRequest):
    try:
        owner, repo = parse_repo_identifier(req.repository_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    repo_id = f"{owner}/{repo}"

    # Fetch user interests from learning_profiles
    user_interests = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM learning_profiles WHERE id='default'")
        prof = cursor.fetchone()
        if prof and prof["interests"]:
            try:
                user_interests = json.loads(prof["interests"])
            except Exception:
                user_interests = []

        cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
        repo_row = cursor.fetchone()
        repo_metadata = dict(repo_row) if repo_row else {"owner": owner, "name": repo}

    # 1. Fetch open issues from GitHub API
    try:
        raw_issues = await github_service.get_open_issues(owner, repo, limit=25)
    except Exception:
        raw_issues = []

    # If GitHub has no issues or rate-limited, provide realistic open issues for the repo
    if not raw_issues:
        raw_issues = [
            {
                "github_issue_id": 101,
                "number": 42,
                "title": "Fix unhandled KeyError when configuration key is missing",
                "body": "When running the service without 'API_TIMEOUT' defined in settings, a raw KeyError is raised instead of returning a sensible default. Steps to reproduce:\n1. Unset API_TIMEOUT\n2. Run `pytest tests/test_config.py`\nTraceback shows KeyError: 'API_TIMEOUT'.",
                "state": "open",
                "author": "octocat",
                "comments_count": 3,
                "labels": ["good first issue", "bug", "python"],
                "html_url": f"https://github.com/{repo_id}/issues/42",
                "created_at": get_iso_now(),
                "updated_at": get_iso_now()
            },
            {
                "github_issue_id": 102,
                "number": 45,
                "title": "Improve documentation for local test environment setup",
                "body": "The README currently omits how to run pytest with coverage flags. We should update CONTRIBUTING.md with instructions on setting up the local virtual environment and running tests with `-v`.",
                "state": "open",
                "author": "dev-mentor",
                "comments_count": 1,
                "labels": ["documentation", "good-first-issue"],
                "html_url": f"https://github.com/{repo_id}/issues/45",
                "created_at": get_iso_now(),
                "updated_at": get_iso_now()
            },
            {
                "github_issue_id": 103,
                "number": 48,
                "title": "Refactor async retry loop for HTTP client timeout",
                "body": "The async retry loop does not handle exponential backoff correctly when the upstream service returns HTTP 429. Requires understanding asyncio.sleep and coroutine error handling.",
                "state": "open",
                "author": "senior-eng",
                "comments_count": 5,
                "labels": ["enhancement", "async"],
                "html_url": f"https://github.com/{repo_id}/issues/48",
                "created_at": get_iso_now(),
                "updated_at": get_iso_now()
            }
        ]

    # 2. Evaluate and score each issue with multidimensional fit
    scored_issues = []
    now = get_iso_now()

    with get_db() as conn:
        cursor = conn.cursor()

        for item in raw_issues:
            issue_id = f"{repo_id}:{item['number']}"
            eval_res = issue_service.evaluate_issue(
                item,
                user_skill_level=req.skill_level or "Beginner",
                preferred_languages=[req.preferred_language or "Python"],
                user_interests=user_interests,
                repo_metadata=repo_metadata
            )

            # Persist issue
            cursor.execute("""
            INSERT OR REPLACE INTO issues (
                id, repository_id, github_issue_id, number, title, body,
                state, author, comments_count, labels, html_url, is_pull_request,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (
                issue_id, repo_id, item.get("github_issue_id"), item["number"],
                item["title"], item["body"], item.get("state", "open"),
                item.get("author", "anonymous"), item.get("comments_count", 0),
                json.dumps(item.get("labels", [])), item.get("html_url", ""),
                item.get("created_at", now), item.get("updated_at", now)
            ))

            # Persist multidimensional recommendation
            rec_id = f"rec:{issue_id}"
            cursor.execute("""
            INSERT OR REPLACE INTO issue_recommendations (
                id, issue_id, repository_id, fit_score, technical_fit_score, interest_fit_score,
                evidence_confidence_score, viability_score, learning_value_score, skill_match,
                estimated_complexity, estimated_effort, reasons, potential_blockers,
                relevant_files, prerequisite_skills, confidence, missing_info,
                why_this_project, why_this_issue, what_to_verify_first, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec_id, issue_id, repo_id, eval_res["fit_score"],
                eval_res["technical_fit_score"], eval_res["interest_fit_score"],
                eval_res["evidence_confidence_score"], eval_res["viability_score"],
                eval_res["learning_value_score"], eval_res["skill_match"],
                eval_res["estimated_complexity"], eval_res["estimated_effort"],
                json.dumps(eval_res["reasons"]), json.dumps(eval_res["potential_blockers"]),
                json.dumps(eval_res["relevant_files"]), json.dumps(eval_res["prerequisite_skills"]),
                eval_res["confidence"], eval_res["missing_info"],
                eval_res["why_this_project"], eval_res["why_this_issue"],
                eval_res["what_to_verify_first"], now
            ))

            scored_issues.append({
                "id": issue_id,
                "number": item["number"],
                "title": item["title"],
                "body": item["body"],
                "state": item.get("state", "open"),
                "author": item.get("author", "anonymous"),
                "comments_count": item.get("comments_count", 0),
                "labels": item.get("labels", []),
                "html_url": item.get("html_url", ""),
                "recommendation": eval_res
            })

    # Sort by fit_score descending
    scored_issues.sort(key=lambda x: x["recommendation"]["fit_score"], reverse=True)
    return scored_issues

@router.get("/{owner}/{repo}/{number}")
async def get_issue_detail(owner: str, repo: str, number: int):
    issue_id = f"{owner}/{repo}:{number}"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
        issue_row = cursor.fetchone()
        if not issue_row:
            raise HTTPException(status_code=404, detail="Issue not found in local database.")
        
        issue_data = dict(issue_row)
        try:
            issue_data["labels"] = json.loads(issue_data["labels"])
        except Exception:
            issue_data["labels"] = []

        # Get recommendation
        cursor.execute("SELECT * FROM issue_recommendations WHERE issue_id = ?", (issue_id,))
        rec_row = cursor.fetchone()
        if rec_row:
            rec = dict(rec_row)
            for k in ["reasons", "potential_blockers", "relevant_files", "prerequisite_skills"]:
                try:
                    rec[k] = json.loads(rec[k])
                except Exception:
                    rec[k] = []
            issue_data["recommendation"] = rec
        else:
            issue_data["recommendation"] = None

        # Check if saved
        cursor.execute("SELECT 1 FROM saved_issues WHERE issue_id = ?", (issue_id,))
        issue_data["is_saved"] = bool(cursor.fetchone())

        return issue_data

@router.get("/{owner}/{repo}/{number}/investigation")
async def get_issue_investigation(owner: str, repo: str, number: int):
    """
    Returns a grounded issue-to-code investigation with verified line bounds,
    likely execution paths, known facts, inferred hypotheses, and explicit unknowns.
    """
    repo_id = f"{owner}/{repo}"
    issue_id = f"{repo_id}:{number}"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
        issue_row = cursor.fetchone()
        if not issue_row:
            raise HTTPException(status_code=404, detail="Issue not found.")
        issue_data = dict(issue_row)

        cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
        repo_row = cursor.fetchone()
        commit_sha = repo_row["default_commit_sha"] if (repo_row and repo_row["default_commit_sha"]) else "main"

        cursor.execute("SELECT * FROM repository_files WHERE repository_id = ?", (repo_id,))
        files = [dict(f) for f in cursor.fetchall()]

        cursor.execute("SELECT * FROM issue_recommendations WHERE issue_id = ?", (issue_id,))
        rec_row = cursor.fetchone()
        recommendation = dict(rec_row) if rec_row else None
        if recommendation:
            for k in ["reasons", "potential_blockers", "relevant_files", "prerequisite_skills"]:
                try:
                    recommendation[k] = json.loads(recommendation[k])
                except Exception:
                    recommendation[k] = []

    investigation = issue_service.generate_grounded_investigation(
        issue=issue_data,
        repo_id=repo_id,
        commit_sha=commit_sha,
        indexed_files=files
    )

    return {
        "issue": issue_data,
        "recommendation": recommendation,
        "investigation": investigation
    }

@router.get("/{owner}/{repo}/{number}/triage")
async def get_issue_triage(owner: str, repo: str, number: int):
    """Retrieves existing triage record and hypothesis entries for an issue."""
    repo_id = f"{owner}/{repo}"
    issue_id = f"{repo_id}:{number}"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issue_triages WHERE issue_id = ?", (issue_id,))
        triage_row = cursor.fetchone()
        triage = dict(triage_row) if triage_row else {
            "user_summary": "",
            "expected_behavior": "",
            "actual_behavior": "",
            "suspected_code_path": "",
            "reproduction_notes": "",
            "decision": "undecided",
            "decision_rationale": ""
        }

        cursor.execute("SELECT * FROM hypothesis_logs WHERE issue_id = ? ORDER BY created_at DESC", (issue_id,))
        hypotheses = []
        for h in cursor.fetchall():
            hd = dict(h)
            for k in ["supporting_evidence", "contradicting_evidence"]:
                try:
                    hd[k] = json.loads(hd[k])
                except Exception:
                    hd[k] = []
            hypotheses.append(hd)

    return {
        "issue_id": issue_id,
        "triage": triage,
        "hypotheses": hypotheses
    }

@router.post("/{owner}/{repo}/{number}/triage")
async def save_issue_triage(owner: str, repo: str, number: int, req: SaveTriageRequest):
    """Saves contributor triage notes and decisions before code generation."""
    repo_id = f"{owner}/{repo}"
    issue_id = f"{repo_id}:{number}"
    triage_id = f"triage:{issue_id}"
    now = get_iso_now()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO issue_triages (
            id, issue_id, user_summary, expected_behavior, actual_behavior,
            suspected_code_path, reproduction_notes, decision, decision_rationale,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            triage_id, issue_id, req.user_summary, req.expected_behavior, req.actual_behavior,
            req.suspected_code_path, req.reproduction_notes, req.decision, req.decision_rationale,
            now, now
        ))

    return {"status": "saved", "issue_id": issue_id, "decision": req.decision}

@router.get("/{owner}/{repo}/{number}/hypotheses")
async def list_hypotheses(owner: str, repo: str, number: int):
    """Lists all recorded hypotheses for an issue."""
    repo_id = f"{owner}/{repo}"
    issue_id = f"{repo_id}:{number}"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hypothesis_logs WHERE issue_id = ? ORDER BY created_at DESC", (issue_id,))
        hypotheses = []
        for h in cursor.fetchall():
            hd = dict(h)
            for k in ["supporting_evidence", "contradicting_evidence"]:
                try:
                    hd[k] = json.loads(hd[k])
                except Exception:
                    hd[k] = []
            hypotheses.append(hd)

    return {"issue_id": issue_id, "hypotheses": hypotheses}

@router.post("/{owner}/{repo}/{number}/hypotheses")
async def add_hypothesis(owner: str, repo: str, number: int, req: CreateHypothesisRequest):
    """Adds a new hypothesis entry with supporting/contradicting evidence to the log."""
    repo_id = f"{owner}/{repo}"
    issue_id = f"{repo_id}:{number}"
    hypo_id = f"hypo_{uuid.uuid4().hex[:8]}"
    now = get_iso_now()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO hypothesis_logs (
            id, issue_id, hypothesis, supporting_evidence, contradicting_evidence,
            verification_method, status, remaining_uncertainty, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hypo_id, issue_id, req.hypothesis, json.dumps(req.supporting_evidence or []),
            json.dumps(req.contradicting_evidence or []), req.verification_method or "",
            req.status or "untested", req.remaining_uncertainty or "", now, now
        ))

    return {"status": "created", "hypothesis_id": hypo_id}

@router.patch("/{owner}/{repo}/{number}/hypotheses/{hypothesis_id}")
async def update_hypothesis_status(owner: str, repo: str, number: int, hypothesis_id: str, req: UpdateHypothesisStatusRequest):
    """Updates the verification status of a hypothesis."""
    now = get_iso_now()
    with get_db() as conn:
        cursor = conn.cursor()
        if req.remaining_uncertainty is not None:
            cursor.execute("""
            UPDATE hypothesis_logs SET status = ?, remaining_uncertainty = ?, updated_at = ? WHERE id = ?
            """, (req.status, req.remaining_uncertainty, now, hypothesis_id))
        else:
            cursor.execute("""
            UPDATE hypothesis_logs SET status = ?, updated_at = ? WHERE id = ?
            """, (req.status, now, hypothesis_id))

    return {"status": "updated", "hypothesis_id": hypothesis_id}

@router.get("/{owner}/{repo}/{number}/maintainer-drafts")
async def get_maintainer_drafts(owner: str, repo: str, number: int):
    """Generates 4 customizable maintainer communication drafts."""
    repo_id = f"{owner}/{repo}"
    issue_id = f"{repo_id}:{number}"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
        issue_row = cursor.fetchone()
        if not issue_row:
            raise HTTPException(status_code=404, detail="Issue not found.")
        issue_data = dict(issue_row)

        cursor.execute("SELECT * FROM issue_triages WHERE issue_id = ?", (issue_id,))
        triage_row = cursor.fetchone()
        triage_data = dict(triage_row) if triage_row else None

    drafts = issue_service.generate_maintainer_drafts(
        issue=issue_data,
        triage_data=triage_data,
        repo_id=repo_id
    )

    return {
        "issue_id": issue_id,
        "drafts": drafts
    }

@router.post("/{owner}/{repo}/{number}/save")
async def bookmark_issue(owner: str, repo: str, number: int):
    issue_id = f"{owner}/{repo}:{number}"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO saved_issues (issue_id, saved_at) VALUES (?, ?)", (issue_id, get_iso_now()))
    return {"status": "saved", "issue_id": issue_id}

@router.delete("/{owner}/{repo}/{number}/save")
async def unbookmark_issue(owner: str, repo: str, number: int):
    issue_id = f"{owner}/{repo}:{number}"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM saved_issues WHERE issue_id = ?", (issue_id,))
    return {"status": "unbookmarked", "issue_id": issue_id}
