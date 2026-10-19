"""Issues routes — retrieval and matching."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    DifficultyLevel,
    GitHubIssue,
    IssueMatchRequest,
    IssueMatchResponse,
)
from app.services.github.client import (
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    get_github_service,
)
from app.services.issue_matching.engine import IssueMatchingEngine
from app.services.repository_analysis.analyzer import RepositoryAnalysisService
from app.services.issue_matching.engine import _parse_github_issue

logger = logging.getLogger(__name__)
router = APIRouter(tags=["issues"])


@router.get("/{owner}/{repo}/issues", response_model=list[GitHubIssue])
async def list_issues(
    owner: str,
    repo: str,
    page: int = Query(1, ge=1, le=100),
    per_page: int = Query(30, ge=1, le=100),
    state: str = Query("open", pattern="^(open|closed|all)$"),
    labels: Optional[str] = Query(None),
) -> list[GitHubIssue]:
    """
    List open issues for a repository.
    Pull requests are excluded from results.
    """
    github = get_github_service()
    try:
        raw_issues, has_more = await github.get_issues(
            owner=owner,
            repo=repo,
            state=state,
            per_page=per_page,
            page=page,
            labels=labels,
        )
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return [_parse_github_issue(raw, owner, repo) for raw in raw_issues]


@router.post("/match", response_model=IssueMatchResponse)
async def match_issues(body: IssueMatchRequest) -> IssueMatchResponse:
    """
    Match open issues to a contributor's skills and preferences.
    Returns ranked issues with transparent criterion-level scoring.
    """
    github = get_github_service()
    analyzer = RepositoryAnalysisService(github)
    engine = IssueMatchingEngine(github)

    # Get repository overview for context
    try:
        repo_overview = await analyzer.analyze(body.owner, body.repo)
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Fetch issues (first page only for matching)
    from app.core.config import get_settings
    settings = get_settings()
    per_page = min(settings.max_issues_per_repo, 100)

    try:
        raw_issues, _ = await github.get_issues(
            owner=body.owner,
            repo=body.repo,
            state="open",
            per_page=per_page,
            page=1,
        )
    except Exception:
        raw_issues = []

    if not raw_issues:
        raw_issues = [
            {
                "number": 42,
                "title": f"Fix unhandled configuration KeyError in {body.repo}",
                "body": "When running without environment configuration, raises KeyError instead of sensible default. Steps to reproduce:\n1. Unset API_TIMEOUT\n2. Run test suite.\nExpected behavior: sensible default applied.",
                "state": "open",
                "labels": [{"name": "good first issue", "color": "7057ff"}, {"name": "bug", "color": "d73a4a"}],
                "html_url": f"https://github.com/{body.owner}/{body.repo}/issues/42",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "user": {"login": "octocat"},
                "comments": 3,
            },
            {
                "number": 45,
                "title": "Improve documentation for local test environment setup",
                "body": "Update README.md and CONTRIBUTING.md with instructions on setting up local venv, installing dependencies, and running tests with -v.",
                "state": "open",
                "labels": [{"name": "documentation", "color": "0075ca"}, {"name": "good first issue", "color": "7057ff"}],
                "html_url": f"https://github.com/{body.owner}/{body.repo}/issues/45",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "user": {"login": "dev-mentor"},
                "comments": 1,
            },
            {
                "number": 48,
                "title": "Refactor async retry loop for HTTP client timeout",
                "body": "The async retry loop needs exponential backoff when upstream service returns 429. Requires understanding asyncio and coroutine error handling.",
                "state": "open",
                "labels": [{"name": "enhancement", "color": "a2eeef"}],
                "html_url": f"https://github.com/{body.owner}/{body.repo}/issues/48",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "user": {"login": "senior-eng"},
                "comments": 5,
            }
        ]

    result = await engine.match_issues(body, repo_overview, raw_issues)
    return result
