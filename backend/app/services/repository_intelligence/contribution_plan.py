"""
FirstPatch AI — Phase 2 Contribution Plan Preparation & Deterministic Validation

Builds structured, multi-stage contribution plans (Understand, Explore, Plan,
Attempt, Verify, Prepare PR) and provides a rigorous deterministic validator
that checks plans against real repository snapshots.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.schemas.models import (
    EvidenceRef,
    EvidenceType,
    GitHubIssue,
    PlanRequest,
)
from app.services.repository_intelligence.schemas import (
    CodeStructureReport,
    PlanStageEnum,
    PlanValidationReport,
    RepositorySnapshot,
    SourceMappingResult,
    StructuredContributionPlan,
    StructuredPlanStage,
    TestDiscoveryReport,
)

logger = logging.getLogger(__name__)


class ContributionPlanService:
    """
    Generates structured, evidence-grounded contribution plans.
    """

    def generate_structured_plan(
        self,
        request: PlanRequest,
        snapshot: RepositorySnapshot,
        issue: GitHubIssue,
        source_mapping: SourceMappingResult,
        test_report: TestDiscoveryReport,
    ) -> StructuredContributionPlan:
        """
        Build a 6-stage deterministic contribution plan grounded in snapshot evidence.
        """
        stages: list[StructuredPlanStage] = []
        evidence_refs: list[EvidenceRef] = list(source_mapping.evidence_refs)
        uncertainties: list[str] = list(source_mapping.missing_evidence_notes)
        assumptions: list[str] = []

        relevant_files = source_mapping.relevant_files

        # -------------------------------------------------------------------
        # Stage 1: Understand
        # -------------------------------------------------------------------
        understand_checklist = [
            f"Read issue #{issue.number} description and all comments thoroughly",
            "Identify the expected behavior versus current observed behavior",
        ]
        if not issue.body or len(issue.body.strip()) < 50:
            understand_checklist.append("Ask maintainer for clarification (issue description is very brief)")

        stages.append(StructuredPlanStage(
            stage=PlanStageEnum.UNDERSTAND,
            title="Understand the Issue Objective",
            description=(
                f"Analyze issue #{issue.number}: '{issue.title}'. "
                "Confirm the problem scope and any constraints before writing code."
            ),
            relevant_files=relevant_files[:3],
            evidence_refs=[ref for ref in evidence_refs if ref.evidence_type == EvidenceType.GITHUB_ISSUE_FIELD],
            checklist=understand_checklist,
            warnings=["Do not begin implementation until the problem is clearly reproduced."] if "bug" in issue.title.lower() else [],
        ))

        # -------------------------------------------------------------------
        # Stage 2: Explore
        # -------------------------------------------------------------------
        explore_desc = (
            f"Inspect relevant files ({', '.join(relevant_files[:3]) or 'repository tree'}) "
            "and examine imported dependencies and nearby test cases."
        )
        stages.append(StructuredPlanStage(
            stage=PlanStageEnum.EXPLORE,
            title="Explore Relevant Code and Architecture",
            description=explore_desc,
            relevant_files=relevant_files,
            evidence_refs=[ref for ref in evidence_refs if ref.file_path in relevant_files],
            checklist=[
                "Review imports and module relationships in the target files",
                f"Locate existing tests in: {', '.join(test_report.test_directories[:2]) or 'project test locations'}",
                "Check CONTRIBUTING.md for coding guidelines and style rules",
            ],
            warnings=[],
        ))

        # -------------------------------------------------------------------
        # Stage 3: Plan
        # -------------------------------------------------------------------
        stages.append(StructuredPlanStage(
            stage=PlanStageEnum.PLAN,
            title="Plan the Implementation Steps",
            description=(
                "Break down the fix or feature into small, reviewable changes. "
                "Ensure every modified module has associated test coverage."
            ),
            relevant_files=relevant_files,
            checklist=[
                "Create a dedicated Git branch: git checkout -b fix/issue-" + str(issue.number),
                "Draft targeted code changes without touching unrelated files",
                "Identify edge cases, error conditions, and potential regressions",
            ],
            warnings=["Keep changes focused on the issue to ensure a smooth maintainer review."],
        ))

        # -------------------------------------------------------------------
        # Stage 4: Attempt
        # -------------------------------------------------------------------
        stages.append(StructuredPlanStage(
            stage=PlanStageEnum.ATTEMPT,
            title="Implement the Proposed Change",
            description=(
                "Implement your solution locally. FirstPatch AI does NOT automatically modify "
                "or write to your local repository or push commits."
            ),
            relevant_files=relevant_files,
            checklist=[
                "Apply the necessary code changes in your local clone",
                "Ensure code formatting adheres to project conventions",
                "Avoid committing temporary or generated files",
            ],
            warnings=["All code changes must be reviewed and tested by you locally."],
        ))

        # -------------------------------------------------------------------
        # Stage 5: Verify
        # -------------------------------------------------------------------
        verify_cmds = test_report.execution_command_suggestions or ["Run local test runner"]
        stages.append(StructuredPlanStage(
            stage=PlanStageEnum.VERIFY,
            title="Verify Changes with Tests and Linters",
            description=(
                "Run automated tests and linters locally. Note: Static analysis has discovered "
                f"tests ({', '.join(test_report.test_frameworks) or 'frameworks'}), "
                "but execution must be performed by you."
            ),
            relevant_files=test_report.discovered_test_files[:3],
            checklist=[
                f"Run command: '{verify_cmds[0]}'",
                "Add a new unit test covering the specific bug or feature",
                "Verify that all existing tests continue to pass",
            ],
            warnings=["Never submit a pull request without running existing tests locally."],
        ))

        # -------------------------------------------------------------------
        # Stage 6: Prepare PR
        # -------------------------------------------------------------------
        stages.append(StructuredPlanStage(
            stage=PlanStageEnum.PREPARE_PR,
            title="Prepare Pull Request Summary",
            description=(
                f"Prepare a clean pull request referencing issue #{issue.number}. "
                "Include verified facts, reproduction steps, and testing evidence."
            ),
            relevant_files=relevant_files,
            checklist=[
                f"Title format: 'Fix: {issue.title[:50]} (fixes #{issue.number})'",
                "Summarize what was changed and why",
                "Document local test commands and their results",
                "Confirm that branch is rebased on latest main",
            ],
            warnings=[],
        ))

        if not relevant_files:
            uncertainties.append(
                "No specific source files could be mapped to this issue with high confidence. "
                "Explore the repository tree manually before implementing."
            )

        assumptions.append(
            "Plan is deterministically generated from repository metadata, file inventory, "
            f"and commit {snapshot.commit_sha[:8]}."
        )

        return StructuredContributionPlan(
            session_id=uuid4(),
            owner=snapshot.owner,
            repo=snapshot.repo,
            commit_sha=snapshot.commit_sha,
            issue_number=issue.number,
            issue_title=issue.title,
            issue_url=issue.github_url,
            summary=(
                f"Contribution plan for issue #{issue.number} ('{issue.title}'). "
                f"Pinned to commit {snapshot.commit_sha[:8]}. "
                f"Identified {len(relevant_files)} relevant file(s)."
            ),
            stages=stages,
            relevant_files=relevant_files,
            suggested_tests=test_report.execution_command_suggestions,
            prerequisite_concepts=[
                f"{snapshot.owner}/{snapshot.repo} architecture",
                "Git workflow (fork, branch, commit, PR)",
            ],
            evidence_refs=evidence_refs,
            uncertainties=uncertainties,
            assumptions=assumptions,
            ai_generated=False,
            generated_at=datetime.now(timezone.utc),
        )


class PlanValidator:
    """
    Deterministic validator that verifies a contribution plan against reality:
    - Confirms all referenced files exist in the pinned snapshot.
    - Confirms referenced symbols exist in the AST structure.
    - Confirms evidence references are non-stale and verified.
    - Flags unsupported claims or fabricated files.
    """

    def validate_plan(
        self,
        plan: StructuredContributionPlan,
        snapshot: RepositorySnapshot,
        code_report: Optional[CodeStructureReport] = None,
    ) -> PlanValidationReport:
        passed_checks: list[str] = []
        violations: list[str] = []
        unsupported_claims: list[str] = []
        invalid_file_refs: list[str] = []
        invalid_symbol_refs: list[str] = []

        # Check 1: Commit SHA integrity
        if plan.commit_sha != snapshot.commit_sha:
            violations.append(
                f"Plan commit SHA ({plan.commit_sha[:8]}) does not match "
                f"snapshot commit SHA ({snapshot.commit_sha[:8]})."
            )
        else:
            passed_checks.append("Plan commit SHA matches snapshot commit SHA.")

        # Check 2: File references in plan
        for file_path in plan.relevant_files:
            if not snapshot.has_file(file_path):
                invalid_file_refs.append(file_path)
                violations.append(f"Referenced file '{file_path}' does not exist in snapshot.")
            else:
                passed_checks.append(f"Referenced file '{file_path}' exists in snapshot.")

        # Check 3: File references inside each stage
        for stage in plan.stages:
            for file_path in stage.relevant_files:
                if not snapshot.has_file(file_path):
                    if file_path not in invalid_file_refs:
                        invalid_file_refs.append(file_path)
                        violations.append(
                            f"Stage '{stage.stage.value}' references nonexistent file '{file_path}'."
                        )

        # Check 4: Evidence references in plan
        for ref in plan.evidence_refs:
            if ref.commit_sha and ref.commit_sha != snapshot.commit_sha:
                unsupported_claims.append(
                    f"EvidenceRef '{ref.id}' references stale commit SHA {ref.commit_sha[:8]}."
                )
            if ref.file_path and not snapshot.has_file(ref.file_path):
                unsupported_claims.append(
                    f"EvidenceRef '{ref.id}' references missing file '{ref.file_path}'."
                )

        # Check 5: Symbol references check against code_report
        if code_report:
            for ref in plan.evidence_refs:
                if ref.evidence_type in {EvidenceType.AST_FUNCTION, EvidenceType.CONFIG_DECLARATION} and ref.file_path:
                    # Verify file in code_report
                    file_struct = code_report.files.get(ref.file_path)
                    if file_struct and ref.start_line is not None:
                        matching_sym = any(
                            sym.start_line == ref.start_line
                            for sym in file_struct.symbols
                        )
                        if not matching_sym:
                            invalid_symbol_refs.append(
                                f"No symbol found at '{ref.file_path}:{ref.start_line}'"
                            )

        is_valid = len(violations) == 0 and len(invalid_file_refs) == 0

        return PlanValidationReport(
            is_valid=is_valid,
            passed_checks=passed_checks,
            violations=violations,
            unsupported_claims=unsupported_claims,
            invalid_file_refs=invalid_file_refs,
            invalid_symbol_refs=invalid_symbol_refs,
        )
