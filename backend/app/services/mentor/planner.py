"""
FirstPatch AI — Mentor / Contribution Plan Service

Generates evidence-backed contribution plans.
Uses deterministic logic first; AI enrichment is optional.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.schemas import (
    ContributionPlan,
    DifficultyLevel,
    EvidenceRef,
    EvidenceStatus,
    EvidenceType,
    GitHubIssue,
    ImplementationStep,
    PlanRequest,
    RepositoryOverview,
)
from app.services.github.client import GitHubService

logger = logging.getLogger(__name__)


class MentorService:
    """
    Generates contribution plans backed by repository evidence.

    Design:
    - Deterministic baseline: always available
    - AI enrichment: optional, labelled when used
    - All file references must be verified against the repository tree
    - Uncertainties and assumptions are always listed
    """

    def __init__(self, github: GitHubService, ai_provider: Any = None):
        self.github = github
        self.ai_provider = ai_provider

    async def generate_plan(
        self,
        request: PlanRequest,
        repo_overview: RepositoryOverview,
        issue: GitHubIssue,
        issue_raw: dict[str, Any],
    ) -> ContributionPlan:
        """
        Generate a contribution plan for an issue.
        """
        owner = request.owner
        repo = request.repo
        evidence_refs: list[EvidenceRef] = []
        uncertainties: list[str] = []
        assumptions: list[str] = []

        # --- Issue evidence ---
        issue_evidence = EvidenceRef(
            owner=owner,
            repo=repo,
            evidence_type=EvidenceType.GITHUB_ISSUE_FIELD,
            github_url=issue.github_url,
            excerpt=f"#{issue.number}: {issue.title[:100]}",
            status=EvidenceStatus.VERIFIED,
        )
        evidence_refs.append(issue_evidence)

        # --- Identify relevant files from repo tree ---
        relevant_files = await self._identify_relevant_files(
            owner, repo, repo_overview, issue, evidence_refs, uncertainties
        )

        # --- Build deterministic implementation steps ---
        steps = _build_implementation_steps(
            issue=issue,
            repo=repo_overview,
            relevant_files=relevant_files,
            experience_level=request.experience_level,
        )

        # --- Suggest tests ---
        suggested_tests = _suggest_tests(repo_overview, relevant_files)

        # --- Prerequisites ---
        prerequisite_concepts = _infer_prerequisite_concepts(
            repo_overview, issue, request.experience_level
        )

        # --- Uncertainties ---
        if not relevant_files:
            uncertainties.append(
                "Could not identify specific files related to this issue. "
                "Browse the repository structure to find the relevant code."
            )
        if not repo_overview.test_locations:
            uncertainties.append(
                "No test directories were detected. "
                "Check if the project has tests in an unconventional location."
            )
        if not repo_overview.readme_summary:
            uncertainties.append(
                "No README found. Development setup instructions may be unavailable."
            )

        assumptions.append(
            "This plan is based on publicly available repository metadata and issue text. "
            "It has not been validated against the actual codebase."
        )
        if not request.contributor_skills:
            assumptions.append(
                "No contributor skills were provided. "
                "Prerequisites were estimated from repository analysis alone."
            )

        # --- Summary ---
        summary = _generate_summary(issue, repo_overview, relevant_files)

        return ContributionPlan(
            session_id=uuid4(),
            owner=owner,
            repo=repo,
            issue_number=issue.number,
            issue_title=issue.title,
            issue_url=issue.github_url,
            summary=summary,
            relevant_files=relevant_files,
            implementation_steps=steps,
            suggested_tests=suggested_tests,
            prerequisite_concepts=prerequisite_concepts,
            evidence_refs=evidence_refs,
            uncertainties=uncertainties,
            assumptions=assumptions,
            ai_generated=False,
            generated_at=datetime.now(timezone.utc),
        )

    async def _identify_relevant_files(
        self,
        owner: str,
        repo: str,
        repo_overview: RepositoryOverview,
        issue: GitHubIssue,
        evidence_refs: list[EvidenceRef],
        uncertainties: list[str],
    ) -> list[str]:
        """
        Identify files likely relevant to the issue using keyword matching
        against the repository's directory snapshot.

        This is a heuristic — files are only listed if they actually exist
        in the repo tree.
        """
        issue_text = f"{issue.title} {issue.body or ''}".lower()
        directory_snapshot = repo_overview.directory_snapshot
        all_known_paths = list(directory_snapshot)  # Top-level only

        if not all_known_paths:
            uncertainties.append(
                "Repository directory structure is unavailable. "
                "Cannot identify relevant files heuristically."
            )
            return []

        # Extract meaningful keywords from issue text
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "is", "it", "in", "on", "at", "to", "for",
            "of", "and", "or", "but", "not", "with", "this", "that", "have",
            "has", "be", "are", "was", "were", "will", "would", "could",
            "should", "when", "where", "how", "what", "why", "which", "who",
        }
        words = re.findall(r"\b[a-z][a-z_]{2,}\b", issue_text)
        keywords = [w for w in words if w not in stop_words and len(w) > 3]

        # Count keyword matches per known path
        matched: list[tuple[str, int]] = []
        for path in all_known_paths:
            path_lower = path.lower()
            matches = sum(1 for kw in keywords if kw in path_lower)
            if matches > 0:
                matched.append((path, matches))

        # Sort by match count
        matched.sort(key=lambda x: x[1], reverse=True)
        relevant = [p for p, _ in matched[:5]]

        if relevant:
            for path in relevant:
                evidence_refs.append(EvidenceRef(
                    owner=owner,
                    repo=repo,
                    file_path=path,
                    github_url=f"https://github.com/{owner}/{repo}/tree/{repo_overview.default_branch}/{path}",
                    evidence_type=EvidenceType.DIRECTORY_STRUCTURE,
                    excerpt=f"Path '{path}' matched keywords from issue text",
                    status=EvidenceStatus.VERIFIED,
                    confidence_note="Keyword match — review manually to confirm relevance",
                ))
        else:
            uncertainties.append(
                "No directory paths matched keywords from the issue text. "
                "File identification was not possible from available metadata."
            )

        return relevant


import re  # noqa: E402 (needed for the method above)


def _build_implementation_steps(
    issue: GitHubIssue,
    repo: RepositoryOverview,
    relevant_files: list[str],
    experience_level: DifficultyLevel,
) -> list[ImplementationStep]:
    """Build a deterministic, ordered set of implementation steps."""
    steps: list[ImplementationStep] = []
    order = 1

    # Step 1: Understand the issue
    steps.append(ImplementationStep(
        order=order,
        description="Read the full issue and all comments carefully",
        rationale=(
            "Understanding the exact problem and any prior discussion prevents "
            "duplicating work or building the wrong fix."
        ),
        relevant_files=[],
    ))
    order += 1

    # Step 2: Set up the project
    has_contributing = "CONTRIBUTING.md" in (repo.config_files or [])
    steps.append(ImplementationStep(
        order=order,
        description=(
            f"Follow {'CONTRIBUTING.md' if has_contributing else 'the README'} "
            "to fork, clone, and set up your development environment"
        ),
        rationale="A working local setup is required before you can implement and test any change.",
        relevant_files=["CONTRIBUTING.md"] if has_contributing else ["README.md"],
    ))
    order += 1

    # Step 3: Create a branch
    steps.append(ImplementationStep(
        order=order,
        description=f"Create a new branch: git checkout -b fix/issue-{issue.number}",
        rationale="Working on a dedicated branch keeps your changes isolated and makes the PR review cleaner.",
        relevant_files=[],
    ))
    order += 1

    # Step 4: Locate relevant code
    if relevant_files:
        steps.append(ImplementationStep(
            order=order,
            description=(
                f"Locate and read the relevant source files: "
                f"{', '.join(relevant_files[:3])}"
            ),
            rationale=(
                "These paths were identified by matching keywords from the issue. "
                "Verify their relevance by reading the code."
            ),
            relevant_files=relevant_files[:5],
            is_verified=False,
        ))
        order += 1

    # Step 5: Reproduce the problem
    if issue.body and (
        "bug" in issue.title.lower() or
        any("bug" in l.name.lower() for l in issue.labels)
    ):
        steps.append(ImplementationStep(
            order=order,
            description="Reproduce the reported problem before making any changes",
            rationale=(
                "Reproducing the bug confirms you understand the problem and gives "
                "you a baseline to verify your fix."
            ),
            relevant_files=[],
        ))
        order += 1

    # Step 6: Implement the fix
    steps.append(ImplementationStep(
        order=order,
        description="Implement the fix or feature as described in the issue",
        rationale=(
            "Focus on a minimal, targeted change. "
            "Avoid unrelated refactoring in the same PR."
        ),
        relevant_files=relevant_files[:3],
    ))
    order += 1

    # Step 7: Write or update tests
    if repo.test_locations:
        test_paths = [t.path for t in repo.test_locations[:2]]
        steps.append(ImplementationStep(
            order=order,
            description=f"Add or update tests in: {', '.join(test_paths)}",
            rationale=(
                "Tests demonstrate that your fix works and prevent future regressions. "
                "Many maintainers require tests before accepting a PR."
            ),
            relevant_files=test_paths,
        ))
        order += 1
    else:
        steps.append(ImplementationStep(
            order=order,
            description="Consider adding tests for your change (test directory location unknown)",
            rationale="Tests help maintainers trust your change and prevent regressions.",
            relevant_files=[],
        ))
        order += 1

    # Step 8: Verify locally
    steps.append(ImplementationStep(
        order=order,
        description="Run the test suite and verify that all existing tests still pass",
        rationale="A PR that breaks existing tests is unlikely to be merged.",
        relevant_files=[],
    ))
    order += 1

    # Step 9: Prepare the PR
    steps.append(ImplementationStep(
        order=order,
        description=(
            "Push your branch and open a pull request referencing the issue "
            f"(e.g., 'Fixes #{issue.number}')"
        ),
        rationale=(
            "A clear PR description referencing the issue helps maintainers "
            "understand your change and closes the issue automatically on merge."
        ),
        relevant_files=[],
    ))

    return steps


def _suggest_tests(
    repo: RepositoryOverview, relevant_files: list[str]
) -> list[str]:
    """Suggest concrete test actions based on the repository's test setup."""
    suggestions: list[str] = []

    for loc in repo.test_locations[:3]:
        framework = loc.framework or "test runner"
        suggestions.append(
            f"Run existing tests in '{loc.path}' using {framework} to ensure nothing is broken."
        )

    if not suggestions:
        suggestions.append(
            "No test directories detected. "
            "Check the README for how to run tests in this project."
        )

    if relevant_files:
        suggestions.append(
            f"Consider adding a test case that directly exercises the changed code in: "
            f"{', '.join(relevant_files[:2])}"
        )

    return suggestions


def _infer_prerequisite_concepts(
    repo: RepositoryOverview,
    issue: GitHubIssue,
    experience_level: DifficultyLevel,
) -> list[str]:
    """Infer prerequisite concepts the contributor should understand."""
    concepts: list[str] = []

    if repo.primary_language:
        concepts.append(f"{repo.primary_language} fundamentals")

    for fw in repo.detected_frameworks[:3]:
        concepts.append(f"{fw.name} basics")

    # Git workflow
    concepts.append("Git: fork → branch → commit → push → PR workflow")

    # Test running
    if repo.test_locations:
        concepts.append("Running and understanding automated tests")

    # Reading code
    concepts.append("Reading and navigating an unfamiliar codebase")

    return concepts


def _generate_summary(
    issue: GitHubIssue,
    repo: RepositoryOverview,
    relevant_files: list[str],
) -> str:
    """Generate a brief, honest plan summary."""
    lang = repo.primary_language or "the repository's language"
    file_note = (
        f"Relevant files may include: {', '.join(relevant_files[:3])}."
        if relevant_files
        else "Specific files could not be identified from available metadata."
    )
    return (
        f"This plan guides you through contributing a fix for issue #{issue.number}: "
        f"'{issue.title}'. "
        f"The repository primarily uses {lang}. "
        f"{file_note} "
        f"All steps are based on repository analysis and have not been verified "
        f"by running the actual code."
    )
