"""Mentor routes — contribution plans, diagnostics, and reality checker."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas import (
    ContributionPlan,
    DiagnosticRequest,
    DiagnosticResponse,
    PlanRequest,
)
from app.services.agent.reality_checker import RepositoryRealityChecker
from app.services.github.client import (
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    get_github_service,
)
from app.services.issue_matching.engine import _parse_github_issue
from app.services.mentor.ai_provider import get_ai_provider
from app.services.mentor.diagnostics import ComprehensiveDiagnosticsService
from app.services.mentor.planner import MentorService
from app.services.repository_analysis.analyzer import RepositoryAnalysisService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["mentor"])


class RealityCheckRequest(BaseModel):
    owner: str
    repo: str
    plan: ContributionPlan


@router.post("/plan", response_model=ContributionPlan)
async def generate_plan(body: PlanRequest) -> ContributionPlan:
    """
    Generate a contribution plan for a specific issue.
    Returns evidence-backed steps validated by the Repository Reality Checker.
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

    # Reality Checker verification: validate file paths and claims against collected repo evidence
    checker = RepositoryRealityChecker()
    report = checker.validate_plan(plan, repo_overview)
    final_plan = report.repaired_plan if report.repaired_plan else plan
    return final_plan


@router.post("/diagnose", response_model=DiagnosticResponse)
async def diagnose_setup(body: DiagnosticRequest) -> DiagnosticResponse:
    """
    Diagnose a setup or configuration error using pattern matching.
    Input is treated as untrusted data. Zero shell execution.
    """
    github = get_github_service()
    analyzer = RepositoryAnalysisService(github)

    try:
        repo_overview = await analyzer.analyze(body.owner, body.repo)
    except GitHubAPIError:
        repo_overview = None  # Proceed without repo context

    return ComprehensiveDiagnosticsService.diagnose(body, repo_overview)


@router.post("/reality-check")
async def reality_check(body: RealityCheckRequest) -> dict[str, Any]:
    """
    Explicitly validate a contribution plan against repository reality.
    Checks file existence, commit consistency, and test claims.
    """
    github = get_github_service()
    analyzer = RepositoryAnalysisService(github)

    try:
        repo_overview = await analyzer.analyze(body.owner, body.repo)
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    checker = RepositoryRealityChecker()
    report = checker.validate_plan(body.plan, repo_overview)
    return report.to_dict()


def _generate_diagnostic_findings(
    body: DiagnosticRequest,
    repo_overview: Any = None,
) -> list[Any]:
    """Backward-compatible helper for diagnostic findings."""
    return ComprehensiveDiagnosticsService.diagnose(body, repo_overview).findings
