"""
FirstPatch AI — Phase 2 Repository Intelligence Main Service & Phase 1 Contract

This service provides the stable, typed contract for Phase 1 integration.
All operations are self-contained, deterministic, and can be tested without
live GitHub access or live model credentials.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.schemas.models import (
    GitHubIssue,
    IssueMatchRequest,
    IssueMatchResponse,
    PlanRequest,
)
from app.services.github.client import GitHubService, get_github_service
from app.services.issue_matching.engine import _parse_github_issue
from app.services.repository_analysis.analyzer import RepositoryAnalysisService
from app.services.repository_intelligence.code_structure import CodeStructureAnalyzer
from app.services.repository_intelligence.contribution_plan import (
    ContributionPlanService,
    PlanValidator,
)
from app.services.repository_intelligence.evidence_validator import EvidenceValidator
from app.services.repository_intelligence.issue_mapper import IssueToCodeMapper
from app.services.repository_intelligence.schemas import (
    ClaimRecord,
    CodeStructureReport,
    EvidenceBundle,
    EvidenceValidationResult,
    PlanValidationReport,
    RepositorySnapshot,
    SourceMappingResult,
    StructuredContributionPlan,
    TestDiscoveryReport,
)
from app.services.repository_intelligence.snapshot import RepositorySnapshotService
from app.services.repository_intelligence.test_discovery import TestDiscoveryService

logger = logging.getLogger(__name__)


class RepositoryIntelligenceService:
    """
    Unified entry point for Phase 2 capabilities.
    Exposes stable interfaces for Phase 1 orchestration and agent tooling.
    """

    def __init__(self, github: Optional[GitHubService] = None):
        self.github = github or get_github_service()
        self.snapshot_service = RepositorySnapshotService(self.github)
        self.code_analyzer = CodeStructureAnalyzer()
        self.evidence_validator = EvidenceValidator(self.snapshot_service)
        self.issue_mapper = IssueToCodeMapper(self.github)
        self.test_discovery = TestDiscoveryService(self.snapshot_service)
        self.plan_service = ContributionPlanService()
        self.plan_validator = PlanValidator()

    # 1. Snapshot and inventory
    async def get_repository_snapshot(
        self,
        repository_url: str,
        commit_sha: Optional[str] = None,
        recursive: bool = True,
    ) -> RepositorySnapshot:
        """Fetch and return an immutable, pinned repository snapshot."""
        return await self.snapshot_service.create_snapshot(
            repository_url=repository_url,
            commit_sha=commit_sha,
            recursive=recursive,
        )

    # 2. Source-code structure analysis
    async def analyze_code_structure(
        self,
        snapshot: RepositorySnapshot,
        target_files: Optional[list[str]] = None,
        max_files: int = 50,
    ) -> CodeStructureReport:
        """
        Extract functions, classes, imports, routes, and tests across snapshot files.
        """
        files_to_analyze = target_files or [
            f.path for f in snapshot.files if f.path.endswith((".py", ".js", ".ts", ".jsx", ".tsx"))
        ]
        files_to_analyze = files_to_analyze[:max_files]

        report_files = {}
        total_symbols = 0
        parse_warnings = []

        for file_path in files_to_analyze:
            content = await self.snapshot_service.get_file_content(snapshot, file_path)
            if content is not None:
                struct = self.code_analyzer.analyze_file(file_path, content, snapshot.commit_sha)
                report_files[file_path] = struct
                total_symbols += len(struct.symbols)
                if struct.parse_errors:
                    parse_warnings.extend(struct.parse_errors)

        return CodeStructureReport(
            snapshot_sha=snapshot.commit_sha,
            files=report_files,
            total_symbols=total_symbols,
            parse_warnings=parse_warnings,
        )

    # 3. Evidence validation
    async def validate_claim_evidence(
        self,
        snapshot: RepositorySnapshot,
        claim: ClaimRecord,
    ) -> EvidenceValidationResult:
        """Deterministically validate a claim against the pinned snapshot."""
        return await self.evidence_validator.validate_claim(snapshot, claim)

    async def build_evidence_bundle(
        self,
        snapshot: RepositorySnapshot,
        claims: list[ClaimRecord],
    ) -> EvidenceBundle:
        """Validate a list of claims and package them into an EvidenceBundle."""
        return await self.evidence_validator.validate_bundle(snapshot, claims)

    # 4. GitHub issues
    async def fetch_open_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
    ) -> list[GitHubIssue]:
        """Fetch issues with pull requests excluded."""
        raw_issues, _ = await self.github.get_issues(
            owner=owner,
            repo=repo,
            state=state,
            per_page=per_page,
            page=page,
        )
        return [_parse_github_issue(raw, owner, repo) for raw in raw_issues]

    # 5. Issue-to-code mapping
    def find_relevant_source(
        self,
        snapshot: RepositorySnapshot,
        issue: GitHubIssue,
        code_report: Optional[CodeStructureReport] = None,
    ) -> SourceMappingResult:
        """Map an issue to repository source files and symbols."""
        return self.issue_mapper.map_issue_to_source(issue, snapshot, code_report)

    async def rank_contribution_issues(
        self,
        request: IssueMatchRequest,
        snapshot: RepositorySnapshot,
        raw_issues: list[dict[str, Any]],
        code_report: Optional[CodeStructureReport] = None,
    ) -> IssueMatchResponse:
        """
        Rank candidate issues using 7-criterion deterministic scoring,
        grounded in snapshot source code.
        """
        # Build baseline overview for scoring compatibility
        analyzer = RepositoryAnalysisService(self.github)
        repo_overview = await analyzer.analyze(request.owner, request.repo)

        return self.issue_mapper.rank_issues_with_evidence(
            request=request,
            snapshot=snapshot,
            repo_overview=repo_overview,
            raw_issues=raw_issues,
            code_report=code_report,
        )

    # 6. Test discovery
    async def discover_test_configuration(
        self,
        snapshot: RepositorySnapshot,
        code_report: Optional[CodeStructureReport] = None,
    ) -> TestDiscoveryReport:
        """Statically inspect test configuration and files without executing code."""
        return await self.test_discovery.discover_tests(snapshot, code_report)

    # 7. Contribution plan generation and validation
    async def generate_contribution_plan(
        self,
        request: PlanRequest,
        snapshot: RepositorySnapshot,
        issue: GitHubIssue,
        code_report: Optional[CodeStructureReport] = None,
    ) -> StructuredContributionPlan:
        """Generate a 6-stage structured plan grounded in snapshot evidence."""
        source_mapping = self.find_relevant_source(snapshot, issue, code_report)
        test_report = await self.discover_test_configuration(snapshot, code_report)
        return self.plan_service.generate_structured_plan(
            request=request,
            snapshot=snapshot,
            issue=issue,
            source_mapping=source_mapping,
            test_report=test_report,
        )

    def validate_plan_evidence(
        self,
        plan: StructuredContributionPlan,
        snapshot: RepositorySnapshot,
        code_report: Optional[CodeStructureReport] = None,
    ) -> PlanValidationReport:
        """Verify that all files, symbols, and claims in a plan exist in reality."""
        return self.plan_validator.validate_plan(plan, snapshot, code_report)


# Singleton accessor
_repo_intelligence_service: Optional[RepositoryIntelligenceService] = None


def get_repository_intelligence_service() -> RepositoryIntelligenceService:
    global _repo_intelligence_service
    if _repo_intelligence_service is None:
        _repo_intelligence_service = RepositoryIntelligenceService()
    return _repo_intelligence_service
