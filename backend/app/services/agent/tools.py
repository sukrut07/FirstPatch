"""
FirstPatch AI — Agent Tools (Tools A through H)

Explicit, modular, and testable tool implementations:
Tool A: inspect_repository
Tool B: analyze_code_structure
Tool C: fetch_open_issues
Tool D: rank_contribution_issues
Tool E: build_evidence_bundle
Tool F: generate_contribution_plan
Tool G: diagnose_setup_error
Tool H: validate_plan_evidence
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.schemas import (
    ContributionPlan,
    DiagnosticRequest,
    DiagnosticResponse,
    EvidenceRef,
    GitHubIssue,
    IssueMatchRequest,
    IssueMatchResponse,
    PlanRequest,
    RepositoryOverview,
)
from app.services.agent.reality_checker import RealityCheckReport, RepositoryRealityChecker
from app.services.github.client import GitHubService
from app.services.issue_matching.engine import IssueMatchingEngine, _parse_github_issue
from app.services.mentor.planner import MentorService
from app.services.repository_analysis.analyzer import RepositoryAnalysisService
from app.services.repository_analysis.ast_analyzer import CodeStructureAnalyzer, CodeStructureResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool A: inspect_repository
# ---------------------------------------------------------------------------
class InspectRepositoryTool:
    """Tool A: Establish verified repository facts from metadata, tree, and files."""

    def __init__(self, github: GitHubService, analyzer: Optional[RepositoryAnalysisService] = None):
        self.github = github
        self.analyzer = analyzer or RepositoryAnalysisService(github)

    async def execute(self, owner: str, repo: str) -> RepositoryOverview:
        logger.info("Executing Tool A (inspect_repository) for %s/%s", owner, repo)
        return await self.analyzer.analyze(owner, repo)


# ---------------------------------------------------------------------------
# Tool B: analyze_code_structure
# ---------------------------------------------------------------------------
class AnalyzeCodeStructureTool:
    """Tool B: Identify functions, classes, imports, and relationships (Python AST or heuristics)."""

    def __init__(self, analyzer: Optional[CodeStructureAnalyzer] = None):
        self.analyzer = analyzer or CodeStructureAnalyzer()

    def execute(
        self,
        file_path: str,
        content: str,
        owner: str = "",
        repo: str = "",
        commit_sha: Optional[str] = None,
    ) -> CodeStructureResult:
        logger.info("Executing Tool B (analyze_code_structure) for %s", file_path)
        return self.analyzer.analyze_source(file_path, content, owner, repo, commit_sha)


# ---------------------------------------------------------------------------
# Tool C: fetch_open_issues
# ---------------------------------------------------------------------------
class FetchOpenIssuesTool:
    """Tool C: Retrieve open issues from GitHub (PRs excluded, bounded pagination)."""

    def __init__(self, github: GitHubService):
        self.github = github

    async def execute(
        self,
        owner: str,
        repo: str,
        per_page: int = 50,
        page: int = 1,
    ) -> tuple[list[dict[str, Any]], bool]:
        logger.info("Executing Tool C (fetch_open_issues) for %s/%s page %d", owner, repo, page)
        raw_issues, has_next = await self.github.get_issues(
            owner=owner,
            repo=repo,
            state="open",
            per_page=per_page,
            page=page,
        )
        # Filter out pull requests
        issues_only = [i for i in raw_issues if "pull_request" not in i]
        return issues_only, has_next


# ---------------------------------------------------------------------------
# Tool D: rank_contribution_issues
# ---------------------------------------------------------------------------
class RankContributionIssuesTool:
    """Tool D: Rank candidate issues using explainable 7-criterion scoring engine."""

    def __init__(self, github: GitHubService, engine: Optional[IssueMatchingEngine] = None):
        self.github = github
        self.engine = engine or IssueMatchingEngine(github)

    async def execute(
        self,
        request: IssueMatchRequest,
        repo_overview: RepositoryOverview,
        raw_issues: list[dict[str, Any]],
    ) -> IssueMatchResponse:
        logger.info("Executing Tool D (rank_contribution_issues) for %s/%s (%d raw issues)", request.owner, request.repo, len(raw_issues))
        return await self.engine.match_issues(request, repo_overview, raw_issues)


# ---------------------------------------------------------------------------
# Tool E: build_evidence_bundle
# ---------------------------------------------------------------------------
class BuildEvidenceBundleTool:
    """Tool E: Prepare bounded, relevant evidence context for AI model reasoning."""

    def execute(
        self,
        repo_overview: RepositoryOverview,
        issue: GitHubIssue,
        code_structures: Optional[list[CodeStructureResult]] = None,
        max_chars: int = 12000,
    ) -> dict[str, Any]:
        logger.info("Executing Tool E (build_evidence_bundle) for issue #%d", issue.number)
        sections: list[str] = []

        # Repository context
        sections.append(
            f"REPOSITORY: {repo_overview.full_name}\n"
            f"Primary Language: {repo_overview.primary_language or 'Unknown'}\n"
            f"Default Branch: {repo_overview.default_branch}\n"
            f"Commit SHA: {repo_overview.commit_sha or 'Not recorded'}\n"
            f"Config Files: {', '.join(repo_overview.config_files[:10]) or 'None detected'}\n"
            f"Test Locations: {', '.join(t.path for t in repo_overview.test_locations[:5]) or 'None detected'}\n"
            f"Directory Snapshot: {', '.join(repo_overview.directory_snapshot[:20])}"
        )

        # Issue context
        sections.append(
            f"ISSUE NUMBER: #{issue.number}\n"
            f"TITLE: {issue.title}\n"
            f"AUTHOR: {issue.author or 'Unknown'}\n"
            f"LABELS: {', '.join(l.name for l in issue.labels) or 'None'}\n"
            f"CREATED AT: {issue.created_at.isoformat()}\n"
            f"BODY EXCERPT:\n{(issue.body or 'No description provided')[:1500]}"
        )

        # AST and code structure
        if code_structures:
            struct_lines = ["CODE STRUCTURE DISCOVERIES:"]
            for cs in code_structures:
                struct_lines.append(f"File: {cs.file_path} (Language: {cs.language}, AST Parsed: {cs.is_ast_parsed})")
                for cls in cs.classes[:5]:
                    struct_lines.append(f"  Class: {cls.name} (methods: {', '.join(cls.methods[:5])})")
                for fn in cs.functions[:8]:
                    struct_lines.append(f"  Function: {fn.name}({', '.join(fn.args[:4])}) [lines {fn.start_line}-{fn.end_line}]")
                for imp in cs.imports[:6]:
                    struct_lines.append(f"  Import: {imp.module} -> {', '.join(imp.names[:4])}")
            sections.append("\n".join(struct_lines))

        raw_bundle = "\n\n---\n\n".join(sections)
        bounded_bundle = raw_bundle[:max_chars]

        evidence_refs = list(repo_overview.evidence_refs)
        if code_structures:
            for cs in code_structures:
                evidence_refs.extend(cs.evidence_refs)

        return {
            "evidence_text": bounded_bundle,
            "evidence_refs": evidence_refs,
            "total_chars": len(bounded_bundle),
            "is_truncated": len(raw_bundle) > max_chars,
        }


# ---------------------------------------------------------------------------
# Tool F: generate_contribution_plan
# ---------------------------------------------------------------------------
class GenerateContributionPlanTool:
    """Tool F: Generate structured, evidence-backed contribution plan."""

    def __init__(self, mentor: MentorService):
        self.mentor = mentor

    async def execute(
        self,
        request: PlanRequest,
        repo_overview: RepositoryOverview,
        issue: GitHubIssue,
        issue_raw: dict[str, Any],
    ) -> ContributionPlan:
        logger.info("Executing Tool F (generate_contribution_plan) for issue #%d", issue.number)
        return await self.mentor.generate_plan(request, repo_overview, issue, issue_raw)


# ---------------------------------------------------------------------------
# Tool G: diagnose_setup_error
# ---------------------------------------------------------------------------
class DiagnoseSetupErrorTool:
    """Tool G: Analyze error log against verified repo config without executing commands."""

    def execute(
        self,
        request: DiagnosticRequest,
        repo_overview: Optional[RepositoryOverview] = None,
    ) -> DiagnosticResponse:
        logger.info("Executing Tool G (diagnose_setup_error) for %s/%s", request.owner, request.repo)
        from app.services.mentor.diagnostics import ComprehensiveDiagnosticsService
        return ComprehensiveDiagnosticsService.diagnose(request, repo_overview)


# ---------------------------------------------------------------------------
# Tool H: validate_plan_evidence
# ---------------------------------------------------------------------------
class ValidatePlanEvidenceTool:
    """Tool H: Validate all claims in a plan against collected evidence (Repository Reality Checker)."""

    def __init__(self, checker: Optional[RepositoryRealityChecker] = None):
        self.checker = checker or RepositoryRealityChecker()

    def execute(
        self,
        plan: ContributionPlan,
        repo_overview: RepositoryOverview,
        known_symbols: Optional[dict[str, list[str]]] = None,
    ) -> RealityCheckReport:
        logger.info("Executing Tool H (validate_plan_evidence) for issue #%d", plan.issue_number)
        return self.checker.validate_plan(plan, repo_overview, known_symbols)
