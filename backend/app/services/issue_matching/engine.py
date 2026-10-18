"""
Issue Matching Engine — Deterministic, transparent, evidence-backed ranking.

Design principles:
- Rules are explicit and documented.
- Scores are heuristic, not statistically validated probabilities.
- Every criterion shows its evidence and explanation.
- Missing information is acknowledged, not fabricated.
- AI enrichment is optional and clearly labelled.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.schemas import (
    DifficultyLevel,
    EvidenceRef,
    EvidenceStatus,
    EvidenceType,
    GitHubIssue,
    IssueLabel,
    IssueMatchCriterion,
    IssueMatchRequest,
    IssueMatchResponse,
    MatchedIssue,
    RepositoryOverview,
)
from app.services.github.client import GitHubService

logger = logging.getLogger(__name__)

# Staleness threshold: issues not updated in 180 days are flagged
_STALE_DAYS = 180

# Weights for criteria (must sum to 1.0)
_WEIGHTS: dict[str, float] = {
    "issue_is_open": 0.25,          # Hard requirement
    "has_clear_description": 0.20,  # Can the contributor understand what to do?
    "not_stale": 0.15,              # Recently active
    "has_reproduction_or_steps": 0.15,  # Can they reproduce the problem?
    "has_good_first_issue_label": 0.10,  # Label is a hint, not a guarantee
    "language_match": 0.10,         # Skills alignment
    "has_tests_nearby": 0.05,       # Tests available for guidance
}


class IssueMatchingEngine:
    """
    Ranks issues by transparency criteria.

    Scoring is deterministic. AI enrichment may add explanatory text
    but must not change scores.
    """

    def __init__(self, github: GitHubService):
        self.github = github

    async def match_issues(
        self,
        request: IssueMatchRequest,
        repo_overview: RepositoryOverview,
        raw_issues: list[dict[str, Any]],
    ) -> IssueMatchResponse:
        """
        Score and rank issues against the contributor's profile.
        """
        warnings: list[str] = []

        if not raw_issues:
            return IssueMatchResponse(
                owner=request.owner,
                repo=request.repo,
                matched_issues=[],
                total_issues_considered=0,
                scoring_explanation=_SCORING_EXPLANATION,
                warnings=["No open issues found in this repository."],
            )

        matched: list[MatchedIssue] = []

        for raw in raw_issues:
            issue = _parse_github_issue(raw, request.owner, request.repo)
            if issue.is_pull_request:
                continue  # Already filtered at API level, but double-check

            matched_issue = _score_issue(issue, request, repo_overview)
            matched.append(matched_issue)

        # Sort: highest score first, then most recently updated
        matched.sort(
            key=lambda m: (m.total_score, m.issue.updated_at.timestamp()),
            reverse=True,
        )

        if not matched:
            warnings.append(
                "All retrieved items were pull requests, not issues. "
                "The repository may label PRs as issues."
            )

        return IssueMatchResponse(
            owner=request.owner,
            repo=request.repo,
            matched_issues=matched,
            total_issues_considered=len(raw_issues),
            scoring_explanation=_SCORING_EXPLANATION,
            warnings=warnings,
        )


def _score_issue(
    issue: GitHubIssue,
    request: IssueMatchRequest,
    repo: RepositoryOverview,
) -> MatchedIssue:
    """Apply all scoring criteria to a single issue."""
    criteria: list[IssueMatchCriterion] = []

    # ---- Criterion 1: Issue is open ----
    is_open = issue.state == "open"
    criteria.append(IssueMatchCriterion(
        name="issue_is_open",
        passed=is_open,
        score=1.0 if is_open else 0.0,
        explanation=(
            "The issue is currently open and has not been closed."
            if is_open
            else "This issue is closed and may no longer need a contribution."
        ),
        evidence=EvidenceRef(
            owner=request.owner,
            repo=request.repo,
            file_path=None,
            github_url=issue.github_url,
            evidence_type=EvidenceType.GITHUB_ISSUE_FIELD,
            excerpt=f"state={issue.state!r}",
            status=EvidenceStatus.VERIFIED,
        ),
    ))

    # ---- Criterion 2: Has clear description ----
    body = issue.body or ""
    description_score, description_note = _score_description(body)
    criteria.append(IssueMatchCriterion(
        name="has_clear_description",
        passed=description_score >= 0.5,
        score=description_score,
        explanation=description_note,
        evidence=EvidenceRef(
            owner=request.owner,
            repo=request.repo,
            github_url=issue.github_url,
            evidence_type=EvidenceType.GITHUB_ISSUE_FIELD,
            excerpt=body[:200] if body else "(empty)",
            status=EvidenceStatus.VERIFIED,
        ),
    ))

    # ---- Criterion 3: Not stale ----
    now = datetime.now(timezone.utc)
    last_updated = issue.updated_at
    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)
    days_since_update = (now - last_updated).days
    not_stale = days_since_update < _STALE_DAYS
    staleness_score = max(0.0, 1.0 - days_since_update / _STALE_DAYS)
    criteria.append(IssueMatchCriterion(
        name="not_stale",
        passed=not_stale,
        score=round(staleness_score, 2),
        explanation=(
            f"Issue was last updated {days_since_update} days ago. "
            + ("This is recent and suggests active attention."
               if not_stale
               else f"No activity in {days_since_update} days — may be stale or deprioritized.")
        ),
        evidence=EvidenceRef(
            owner=request.owner,
            repo=request.repo,
            github_url=issue.github_url,
            evidence_type=EvidenceType.GITHUB_ISSUE_FIELD,
            excerpt=f"updated_at={issue.updated_at.isoformat()}",
            status=EvidenceStatus.VERIFIED,
        ),
    ))

    # ---- Criterion 4: Has reproduction steps or expected behavior ----
    has_steps = _has_reproduction_steps(body)
    criteria.append(IssueMatchCriterion(
        name="has_reproduction_or_steps",
        passed=has_steps,
        score=1.0 if has_steps else 0.3,
        explanation=(
            "The issue description contains steps to reproduce, expected behavior, "
            "or code snippets — making it easier to understand and verify a fix."
            if has_steps
            else "No clear reproduction steps found. You may need to ask the maintainer for clarification."
        ),
        missing_data=not has_steps,
    ))

    # ---- Criterion 5: Good first issue label ----
    has_gfi = issue.is_good_first_issue
    gfi_note = (
        "Has a 'good first issue' label. This is a hint from maintainers, "
        "not a guarantee of difficulty."
        if has_gfi
        else "No 'good first issue' label. Check the issue complexity yourself."
    )
    criteria.append(IssueMatchCriterion(
        name="has_good_first_issue_label",
        passed=has_gfi,
        score=1.0 if has_gfi else 0.3,
        explanation=gfi_note,
        evidence=EvidenceRef(
            owner=request.owner,
            repo=request.repo,
            github_url=issue.github_url,
            evidence_type=EvidenceType.GITHUB_ISSUE_FIELD,
            excerpt=f"labels={[l.name for l in issue.labels]}",
            status=EvidenceStatus.VERIFIED,
        ),
    ))

    # ---- Criterion 6: Language match ----
    lang_score, lang_note = _score_language_match(
        repo.primary_language,
        repo.detected_languages,
        request.preferred_languages,
        request.skills,
    )
    criteria.append(IssueMatchCriterion(
        name="language_match",
        passed=lang_score >= 0.5,
        score=round(lang_score, 2),
        explanation=lang_note,
        missing_data=lang_score == 0.5 and not request.preferred_languages,
    ))

    # ---- Criterion 7: Tests available nearby ----
    has_tests = len(repo.test_locations) > 0
    criteria.append(IssueMatchCriterion(
        name="has_tests_nearby",
        passed=has_tests,
        score=1.0 if has_tests else 0.3,
        explanation=(
            f"Tests found at: {', '.join(t.path for t in repo.test_locations[:3])}. "
            "You can run them to verify your fix."
            if has_tests
            else "No test directories detected. Verifying your fix may be harder."
        ),
        missing_data=not has_tests,
    ))

    # ---- Calculate weighted total ----
    total = sum(
        _WEIGHTS.get(c.name, 0.0) * c.score for c in criteria
    )
    total = round(min(total, 1.0), 3)

    # ---- Estimate difficulty ----
    difficulty, difficulty_explanation = _estimate_difficulty(
        issue, has_gfi, has_steps, repo, request.experience_level
    )

    # ---- Identify prerequisites ----
    prerequisites = _identify_prerequisites(repo, issue, request)

    # ---- Identify risks ----
    risks = _identify_risks(issue, not_stale, has_steps)

    return MatchedIssue(
        issue=issue,
        total_score=total,
        difficulty=difficulty,
        difficulty_explanation=difficulty_explanation,
        criteria=criteria,
        prerequisites=prerequisites,
        risks=risks,
    )


def _score_description(body: str) -> tuple[float, str]:
    """Score the clarity of an issue description."""
    if not body or len(body.strip()) < 20:
        return 0.1, "Issue has no meaningful description."
    if len(body.strip()) < 100:
        return 0.4, "Issue description is very brief — may lack important context."
    return 0.9, f"Issue has a description ({len(body)} chars)."


def _has_reproduction_steps(body: str) -> bool:
    """Detect if the body contains reproduction steps or code."""
    patterns = [
        r"steps to reproduce",
        r"to reproduce",
        r"expected behavior",
        r"actual behavior",
        r"```",          # code block
        r"traceback",
        r"error:",
        r"exception:",
        r"how to",
    ]
    lower = body.lower()
    return any(re.search(p, lower) for p in patterns)


def _score_language_match(
    primary_language: Optional[str],
    detected_languages: dict[str, float],
    preferred_languages: list[str],
    skills: list[str],
) -> tuple[float, str]:
    """Score how well the repository's languages match the contributor's."""
    if not preferred_languages and not skills:
        return 0.5, "No language preferences provided — cannot assess language fit."

    all_prefs = {l.lower() for l in preferred_languages + skills}
    repo_langs = {l.lower() for l in detected_languages.keys()}
    if primary_language:
        repo_langs.add(primary_language.lower())

    matches = all_prefs & repo_langs
    if not matches:
        return 0.2, (
            f"No overlap between your preferred languages "
            f"({', '.join(preferred_languages) or 'none specified'}) "
            f"and repository languages ({', '.join(sorted(repo_langs))})."
        )
    return 1.0, (
        f"Your skills match repository languages: {', '.join(sorted(matches))}."
    )


def _estimate_difficulty(
    issue: GitHubIssue,
    has_gfi_label: bool,
    has_steps: bool,
    repo: RepositoryOverview,
    experience_level: DifficultyLevel,
) -> tuple[DifficultyLevel, str]:
    """
    Heuristically estimate issue difficulty.

    This is an estimate based on available signals, not a guarantee.
    """
    signals: list[str] = []

    if has_gfi_label:
        signals.append("maintainer-applied 'good first issue' label")
    if has_steps:
        signals.append("contains reproduction steps or code")
    if issue.comment_count > 20:
        signals.append(f"has {issue.comment_count} comments (may be complex discussion)")
    if issue.body and len(issue.body) > 2000:
        signals.append("long description (may indicate complexity)")

    if has_gfi_label and has_steps and issue.comment_count < 10:
        return (
            DifficultyLevel.BEGINNER,
            f"Estimated beginner-friendly based on: {', '.join(signals)}. "
            "This is a heuristic — verify by reading the full issue.",
        )
    if issue.comment_count > 20 or (issue.body and len(issue.body) > 2000):
        return (
            DifficultyLevel.INTERMEDIATE,
            f"May require intermediate knowledge. Signals: {', '.join(signals) or 'limited info'}.",
        )
    return (
        DifficultyLevel.UNKNOWN,
        f"Difficulty cannot be reliably estimated. Available signals: "
        f"{', '.join(signals) or 'none'}. Read the issue carefully.",
    )


def _identify_prerequisites(
    repo: RepositoryOverview,
    issue: GitHubIssue,
    request: IssueMatchRequest,
) -> list[str]:
    """Suggest prerequisite knowledge based on repo analysis."""
    prereqs: list[str] = []

    if repo.primary_language:
        prereqs.append(f"Working knowledge of {repo.primary_language}")

    framework_names = [f.name for f in repo.detected_frameworks]
    for fw in framework_names[:3]:
        prereqs.append(f"Basic familiarity with {fw}")

    if repo.test_locations:
        frameworks = list({t.framework for t in repo.test_locations if t.framework})
        if frameworks:
            prereqs.append(f"Running tests with {', '.join(frameworks[:2])}")

    if "docker" in (repo.primary_language or "").lower() or any(
        "Docker" in f.name for f in repo.detected_frameworks
    ):
        prereqs.append("Docker basics for running the development environment")

    prereqs.append("Git: forking, branching, and creating pull requests")

    return list(dict.fromkeys(prereqs))  # Deduplicate while preserving order


def _identify_risks(
    issue: GitHubIssue,
    is_recent: bool,
    has_steps: bool,
) -> list[str]:
    """Identify potential risks for a contributor."""
    risks: list[str] = []

    if not is_recent:
        risks.append(
            "Issue has not been updated recently — it may be stale, "
            "already fixed in a branch, or deprioritized."
        )
    if not has_steps:
        risks.append(
            "No reproduction steps — you may need to investigate the problem yourself "
            "or ask the maintainer for clarification before starting."
        )
    if issue.comment_count > 30:
        risks.append(
            f"Issue has {issue.comment_count} comments — read the full discussion "
            "before starting to avoid duplicating work."
        )

    risks.append(
        "No contribution is guaranteed to be accepted. Read CONTRIBUTING.md "
        "and discuss your approach with maintainers before investing significant time."
    )

    return risks


def _parse_github_issue(raw: dict[str, Any], owner: str, repo: str) -> GitHubIssue:
    """Parse a raw GitHub API issue dict into a GitHubIssue schema."""
    labels = [
        IssueLabel(
            name=lbl.get("name", ""),
            color=lbl.get("color"),
            description=lbl.get("description"),
        )
        for lbl in raw.get("labels", [])
    ]

    return GitHubIssue(
        number=raw["number"],
        title=raw.get("title", "(no title)"),
        state=raw.get("state", "unknown"),
        body=raw.get("body"),
        labels=labels,
        created_at=_parse_dt(raw.get("created_at")) or datetime.now(timezone.utc),
        updated_at=_parse_dt(raw.get("updated_at")) or datetime.now(timezone.utc),
        closed_at=_parse_dt(raw.get("closed_at")),
        author=raw.get("user", {}).get("login"),
        comment_count=raw.get("comments", 0),
        github_url=raw.get("html_url", f"https://github.com/{owner}/{repo}/issues/{raw['number']}"),
        is_pull_request="pull_request" in raw,
    )


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


_SCORING_EXPLANATION = (
    "Issues are ranked by a weighted heuristic score across 7 criteria: "
    "open status (25%), description clarity (20%), recency (15%), "
    "reproduction steps (15%), good-first-issue label (10%), "
    "language match (10%), and test availability (5%). "
    "Scores are heuristic estimates, not statistically validated probabilities. "
    "Always read the full issue before starting a contribution."
)
