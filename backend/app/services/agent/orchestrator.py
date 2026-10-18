"""
FirstPatch AI — Agent Orchestrator

Controlled, modular agent orchestration pipeline coordinating Tools A through H:
Stage 1: Request validation
Stage 2: Repository snapshot
Stage 3: Deterministic repository & AST analysis
Stage 4: Evidence bundle collection
Stage 5: Issue context & deterministic ranking
Stage 6: Model reasoning via Gemma (with prompt framing as untrusted data)
Stage 7: Output validation & Reality Checker verification (bounded repair)
Stage 8: Result generation with explicit uncertainties and evidence provenance
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import uuid4

from app.schemas import (
    ContributionPlan,
    GitHubIssue,
    IssueMatchRequest,
    IssueMatchResponse,
    PlanRequest,
    RepositoryOverview,
)
from app.services.agent.reality_checker import RealityCheckReport, RepositoryRealityChecker
from app.services.agent.tools import (
    AnalyzeCodeStructureTool,
    BuildEvidenceBundleTool,
    FetchOpenIssuesTool,
    GenerateContributionPlanTool,
    InspectRepositoryTool,
    RankContributionIssuesTool,
    ValidatePlanEvidenceTool,
)
from app.services.github.client import (
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubService,
)
from app.services.issue_matching.engine import IssueMatchingEngine, _parse_github_issue
from app.services.mentor.ai_provider import BaseAIProvider, get_ai_provider
from app.services.mentor.planner import MentorService
from app.services.repository_analysis.analyzer import RepositoryAnalysisService
from app.services.repository_analysis.ast_analyzer import CodeStructureAnalyzer, CodeStructureResult

logger = logging.getLogger(__name__)


class AgentOrchestrationResult:
    """Encapsulates the output of a complete agent run."""

    def __init__(
        self,
        repository: RepositoryOverview,
        issue: GitHubIssue,
        plan: ContributionPlan,
        reality_report: RealityCheckReport,
        code_structures: list[CodeStructureResult],
        evidence_bundle: dict[str, Any],
        is_ai_enriched: bool,
    ):
        self.repository = repository
        self.issue = issue
        self.plan = plan
        self.reality_report = reality_report
        self.code_structures = code_structures
        self.evidence_bundle = evidence_bundle
        self.is_ai_enriched = is_ai_enriched


class FirstPatchAgentOrchestrator:
    """
    Coordinates multi-stage repository intelligence workflow using auditable tools.
    """

    def __init__(
        self,
        github: GitHubService,
        ai_provider: Optional[BaseAIProvider] = None,
        reality_checker: Optional[RepositoryRealityChecker] = None,
    ):
        self.github = github
        self.ai_provider = ai_provider or get_ai_provider()
        self.reality_checker = reality_checker or RepositoryRealityChecker()

        # Tools
        self.tool_inspect = InspectRepositoryTool(github)
        self.tool_ast = AnalyzeCodeStructureTool()
        self.tool_issues = FetchOpenIssuesTool(github)
        self.tool_rank = RankContributionIssuesTool(github)
        self.tool_bundle = BuildEvidenceBundleTool()
        self.tool_mentor = MentorService(github, self.ai_provider)
        self.tool_plan = GenerateContributionPlanTool(self.tool_mentor)
        self.tool_validate = ValidatePlanEvidenceTool(self.reality_checker)

    async def execute_plan_workflow(
        self,
        request: PlanRequest,
    ) -> AgentOrchestrationResult:
        """
        Executes Stages 1 through 8 to produce a verified contribution plan.
        """
        owner = request.owner
        repo = request.repo
        issue_number = request.issue_number

        logger.info("Starting Agent Pipeline for %s/%s Issue #%d", owner, repo, issue_number)

        # Stage 1 & 2: Repository Snapshot & Inspection
        repo_overview = await self.tool_inspect.execute(owner, repo)

        # Stage 3: Fetch Issue Context
        raw_issues, _ = await self.github.get_issues(
            owner=owner,
            repo=repo,
            state="all",
            per_page=100,
            page=1,
        )
        target_raw = next((i for i in raw_issues if i.get("number") == issue_number), None)
        if not target_raw:
            raise GitHubNotFoundError(f"Issue #{issue_number} not found in {owner}/{repo}")

        issue = _parse_github_issue(target_raw, owner, repo)

        # Stage 4: Deterministic AST & Structure Analysis
        # Identify candidates from directory snapshot and files mentioned in issue text
        candidates: list[str] = [
            f for f in repo_overview.directory_snapshot if f.endswith((".py", ".ts", ".js", ".go", ".rs"))
        ]
        import re
        issue_text = f"{issue.title} {issue.body or ''}"
        for fm in re.findall(r"[\w/\.-]+\.(?:py|js|ts|go|rs)", issue_text):
            if fm not in candidates:
                candidates.append(fm)

        code_structures: list[CodeStructureResult] = []
        for file_path in candidates[:10]:
            try:
                content = await self.github.get_file_content(owner, repo, file_path)
                if content:
                    struct = self.tool_ast.execute(
                        file_path=file_path,
                        content=content,
                        owner=owner,
                        repo=repo,
                        commit_sha=repo_overview.commit_sha,
                    )
                    code_structures.append(struct)
            except Exception as exc:
                logger.debug("Could not fetch/parse %s: %s", file_path, exc)

        # Stage 5: Build Evidence Bundle
        evidence_bundle = self.tool_bundle.execute(
            repo_overview=repo_overview,
            issue=issue,
            code_structures=code_structures,
        )

        # Stage 6: Generate Contribution Plan (AI reasoning or deterministic fallback)
        plan = await self.tool_plan.execute(
            request=request,
            repo_overview=repo_overview,
            issue=issue,
            issue_raw=target_raw,
        )

        # Enrich plan with verified files from code structures matching candidates
        for cs in code_structures:
            if cs.file_path not in plan.relevant_files:
                if any(cand in cs.file_path or cs.file_path.endswith(cand) for cand in candidates):
                    plan.relevant_files.append(cs.file_path)
            for ev in cs.evidence_refs:
                if ev not in plan.evidence_refs:
                    plan.evidence_refs.append(ev)

        # Build known symbols index for reality checker
        known_symbols: dict[str, list[str]] = {}
        for cs in code_structures:
            syms = [fn.name for fn in cs.functions] + [cl.name for cl in cs.classes]
            known_symbols[cs.file_path] = syms

        # Stage 7: Reality Checker Validation & Bounded Repair
        reality_report = self.tool_validate.execute(
            plan=plan,
            repo_overview=repo_overview,
            known_symbols=known_symbols,
        )

        final_plan = reality_report.repaired_plan if reality_report.repaired_plan else plan

        # Stage 8: Result
        return AgentOrchestrationResult(
            repository=repo_overview,
            issue=issue,
            plan=final_plan,
            reality_report=reality_report,
            code_structures=code_structures,
            evidence_bundle=evidence_bundle,
            is_ai_enriched=final_plan.ai_generated,
        )
