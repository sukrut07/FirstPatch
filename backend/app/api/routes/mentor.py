"""Mentor routes — contribution plans and diagnostics."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas import (
    ContributionPlan,
    DiagnosticRequest,
    DiagnosticResponse,
    DiagnosticFinding,
    PlanRequest,
)
from app.services.github.client import (
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    get_github_service,
)
from app.services.issue_matching.engine import _parse_github_issue
from app.services.mentor.ai_provider import get_ai_provider
from app.services.mentor.planner import MentorService
from app.services.repository_analysis.analyzer import RepositoryAnalysisService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["mentor"])


@router.post("/plan", response_model=ContributionPlan)
async def generate_plan(body: PlanRequest) -> ContributionPlan:
    """
    Generate a contribution plan for a specific issue.
    Returns evidence-backed steps with explicit uncertainties.
    """
    github = get_github_service()
    analyzer = RepositoryAnalysisService(github)
    ai_provider = get_ai_provider()
    mentor = MentorService(github=github, ai_provider=ai_provider)

    # Fetch repository analysis
    try:
        repo_overview = await analyzer.analyze(body.owner, body.repo)
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Fetch the specific issue
    try:
        raw_issues, _ = await github.get_issues(
            owner=body.owner,
            repo=body.repo,
            state="all",
            per_page=100,
            page=1,
        )
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch issues: {exc}")

    # Find the target issue
    issue_raw = next(
        (i for i in raw_issues if i.get("number") == body.issue_number),
        None,
    )
    if issue_raw is None:
        raise HTTPException(
            status_code=404,
            detail=f"Issue #{body.issue_number} not found in {body.owner}/{body.repo}",
        )

    issue = _parse_github_issue(issue_raw, body.owner, body.repo)
    plan = await mentor.generate_plan(body, repo_overview, issue, issue_raw)
    return plan


@router.post("/diagnose", response_model=DiagnosticResponse)
async def diagnose_setup(body: DiagnosticRequest) -> DiagnosticResponse:
    """
    Diagnose a setup or configuration error.

    Input is treated as untrusted user data.
    Returns safe diagnostic steps — does NOT execute any commands.
    """
    github = get_github_service()
    analyzer = RepositoryAnalysisService(github)

    # Fetch repository context
    try:
        repo_overview = await analyzer.analyze(body.owner, body.repo)
    except GitHubAPIError:
        repo_overview = None  # Proceed without repo context

    findings = _generate_diagnostic_findings(body, repo_overview)

    return DiagnosticResponse(
        owner=body.owner,
        repo=body.repo,
        findings=findings,
        ai_generated=False,
    )


def _generate_diagnostic_findings(
    body: DiagnosticRequest,
    repo_overview,
) -> list[DiagnosticFinding]:
    """
    Generate deterministic diagnostic findings from error patterns.
    Does not execute commands or access the filesystem.
    """
    from app.schemas import DiagnosticFinding

    findings: list[DiagnosticFinding] = []
    error_lower = body.error_description.lower()
    output_lower = (body.command_output or "").lower()
    combined = error_lower + " " + output_lower

    # Pattern: Dependency not found
    if any(kw in combined for kw in ["modulenotfounderror", "no module named", "cannot find module", "module not found"]):
        findings.append(DiagnosticFinding(
            likely_cause="A required dependency is not installed",
            supporting_evidence=[
                "Error output contains module-not-found indicators",
                f"Repository uses: {', '.join(c for c in (repo_overview.config_files if repo_overview else []) if 'requirements' in c.lower() or 'package.json' in c.lower())[:3] or 'config files not detected'}",
            ],
            safe_diagnostic_steps=[
                "Run: pip install -r requirements.txt (Python) or npm install (Node.js)",
                "Verify your virtual environment is activated",
                "Check that you are in the correct directory",
            ],
            suggested_fix="Install dependencies as documented in the README or CONTRIBUTING.md",
            verification_steps=[
                "Run the failed command again after installing dependencies",
                "Verify the module is importable: python -c 'import <module_name>'",
            ],
            confidence="high",
        ))

    # Pattern: Port in use
    if any(kw in combined for kw in ["address already in use", "eaddrinuse", "port"]):
        findings.append(DiagnosticFinding(
            likely_cause="A required network port is already in use by another process",
            supporting_evidence=["Error output contains port conflict indicators"],
            safe_diagnostic_steps=[
                "Run: lsof -i :<port_number> (macOS/Linux) or netstat -ano | findstr :<port> (Windows)",
                "Stop the conflicting process or change the port in the application config",
            ],
            suggested_fix="Identify and stop the process using the required port",
            verification_steps=["Start the application again after resolving the port conflict"],
            confidence="high",
        ))

    # Pattern: Permission denied
    if any(kw in combined for kw in ["permission denied", "eacces", "access denied"]):
        findings.append(DiagnosticFinding(
            likely_cause="Insufficient filesystem permissions",
            supporting_evidence=["Error output contains permission-denied indicators"],
            safe_diagnostic_steps=[
                "Check file ownership: ls -la <file> (macOS/Linux)",
                "Do NOT use sudo to install packages globally unless the project requires it",
                "Consider using a virtual environment for Python or nvm for Node.js",
            ],
            suggested_fix="Fix file permissions or use a local user environment",
            verification_steps=["Run the command without elevated privileges after fixing permissions"],
            confidence="medium",
        ))

    # Generic fallback
    if not findings:
        findings.append(DiagnosticFinding(
            likely_cause="Setup issue detected but specific pattern not recognized",
            supporting_evidence=["Error details provided in the request"],
            safe_diagnostic_steps=[
                "Read the full error message carefully",
                "Search for the exact error message in the repository's issue tracker",
                "Check the README and CONTRIBUTING.md for known setup requirements",
                "Search the repository's issues for similar reports",
            ],
            suggested_fix=(
                "Follow the project's setup documentation step by step. "
                "If stuck, open an issue in the repository asking for setup help."
            ),
            verification_steps=["Restart the setup process from the beginning with a fresh environment"],
            confidence="low",
        ))

    return findings
