"""
FirstPatch AI — Reality Checker Verification Adapter (Phase 3)

Integrates isolated test verification with the Repository Reality Checker:
- Evaluates whether plan test claims are backed by authentic execution records
- Binds verification records strictly to repository snapshot commit SHAs
- Distinguishes:
  1. Tests discovered but not executed
  2. Tests verified and passed in isolated sandbox
  3. Tests executed and failed
  4. Tests timed out or blocked during preparation
  5. Verification records that are stale (commit SHA mismatch)
  6. Verification infrastructure unavailable
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas import ContributionPlan, ImplementationStep, RepositoryOverview
from app.schemas.verification import ExecutionStatus, VerificationRunRecord
from app.services.verification.store import VerificationRecordStore, get_verification_store


class PlanTestVerificationStatus(str, Enum):
    """Categorization of test verification for contribution plans."""
    TESTS_VERIFIED_PASSED = "tests_verified_passed"
    TESTS_FAILED = "tests_failed"
    TESTS_TIMED_OUT = "tests_timed_out"
    TESTS_PREPARATION_BLOCKED = "tests_preparation_blocked"
    TESTS_STALE_RECORD = "tests_stale_record"
    TESTS_DISCOVERED_NOT_EXECUTED = "tests_discovered_not_executed"
    TESTS_UNAVAILABLE = "tests_unavailable"
    NO_TESTS_FOUND = "no_tests_found"


class PlanVerificationAssessment(BaseModel):
    """Structured assessment linking plan claims to verification evidence."""
    status: PlanTestVerificationStatus
    is_backed_by_evidence: bool = False
    matched_run_id: Optional[UUID] = None
    snapshot_commit_sha: Optional[str] = None
    record_commit_sha: Optional[str] = None
    passed_count: int = 0
    failed_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    recommended_action: str


class VerificationRealityAdapter:
    """
    Adapter between Reality Checker and Isolated Verification Service.
    Enforces that test claims are backed by genuine test execution results.
    """

    def __init__(self, store: Optional[VerificationRecordStore] = None):
        self._store = store or get_verification_store()

    def assess_plan_test_claims(
        self,
        plan: ContributionPlan,
        repo_overview: RepositoryOverview,
        explicit_record: Optional[VerificationRunRecord] = None,
    ) -> PlanVerificationAssessment:
        """
        Assesses test execution claims in a contribution plan against genuine verification records.
        """
        snapshot_sha = (repo_overview.commit_sha or "").strip().lower()

        # Step 1: Look up verification record
        record = explicit_record
        if not record and snapshot_sha:
            record = self._store.get_latest_for_commit(
                owner=plan.owner, repo=plan.repo, commit_sha=snapshot_sha
            )
        if not record and plan.session_id:
            runs = self._store.get_for_session(plan.session_id)
            if runs:
                record = runs[0]

        # Step 2: If a verification record exists, validate commit SHA match
        if record:
            rec_sha = record.commit_sha.strip().lower()
            if snapshot_sha and rec_sha != snapshot_sha:
                return PlanVerificationAssessment(
                    status=PlanTestVerificationStatus.TESTS_STALE_RECORD,
                    is_backed_by_evidence=False,
                    matched_run_id=record.run_id,
                    snapshot_commit_sha=snapshot_sha,
                    record_commit_sha=rec_sha,
                    warnings=[
                        f"Test execution record belongs to commit {rec_sha[:8]}, but current repository snapshot is {snapshot_sha[:8]}. Verification is stale."
                    ],
                    recommended_action="Re-run isolated verification against the current repository snapshot.",
                )

            # Map execution status
            if record.status == ExecutionStatus.PASSED:
                passed_cnt = record.counts.passed if record.counts else 0
                return PlanVerificationAssessment(
                    status=PlanTestVerificationStatus.TESTS_VERIFIED_PASSED,
                    is_backed_by_evidence=True,
                    matched_run_id=record.run_id,
                    snapshot_commit_sha=snapshot_sha,
                    record_commit_sha=rec_sha,
                    passed_count=passed_cnt,
                    warnings=[],
                    recommended_action="Verification passed. Contribution changes can proceed against verified test baseline.",
                )

            elif record.status == ExecutionStatus.FAILED:
                failed_cnt = record.counts.failed if record.counts else 0
                return PlanVerificationAssessment(
                    status=PlanTestVerificationStatus.TESTS_FAILED,
                    is_backed_by_evidence=False,
                    matched_run_id=record.run_id,
                    snapshot_commit_sha=snapshot_sha,
                    record_commit_sha=rec_sha,
                    failed_count=failed_cnt,
                    warnings=[
                        f"Isolated test execution failed: {record.error_summary or 'One or more tests failed.'}"
                    ],
                    recommended_action="Inspect failure logs and fix baseline or contribution regressions before proceeding.",
                )

            elif record.status == ExecutionStatus.TIMED_OUT:
                return PlanVerificationAssessment(
                    status=PlanTestVerificationStatus.TESTS_TIMED_OUT,
                    is_backed_by_evidence=False,
                    matched_run_id=record.run_id,
                    snapshot_commit_sha=snapshot_sha,
                    record_commit_sha=rec_sha,
                    warnings=["Isolated test run timed out before completion."],
                    recommended_action="Refine test target or increase timeout limits if permitted.",
                )

            elif record.status == ExecutionStatus.BLOCKED:
                return PlanVerificationAssessment(
                    status=PlanTestVerificationStatus.TESTS_PREPARATION_BLOCKED,
                    is_backed_by_evidence=False,
                    matched_run_id=record.run_id,
                    snapshot_commit_sha=snapshot_sha,
                    record_commit_sha=rec_sha,
                    warnings=[f"Test execution was blocked: {record.error_summary}"],
                    recommended_action="Resolve repository workspace preparation requirements.",
                )

            elif record.status == ExecutionStatus.UNAVAILABLE:
                return PlanVerificationAssessment(
                    status=PlanTestVerificationStatus.TESTS_UNAVAILABLE,
                    is_backed_by_evidence=False,
                    matched_run_id=record.run_id,
                    snapshot_commit_sha=snapshot_sha,
                    record_commit_sha=rec_sha,
                    warnings=["Execution sandbox infrastructure is unavailable on host."],
                    recommended_action="Run tests locally or deploy FirstPatch AI with container runtime enabled.",
                )

        # Step 3: No record found — determine if tests were discovered
        has_tests = bool(repo_overview.test_locations or repo_overview.test_command)
        if has_tests:
            return PlanVerificationAssessment(
                status=PlanTestVerificationStatus.TESTS_DISCOVERED_NOT_EXECUTED,
                is_backed_by_evidence=False,
                snapshot_commit_sha=snapshot_sha,
                warnings=[
                    "Tests were discovered in repository metadata but have not been executed in an isolated sandbox."
                ],
                recommended_action="Trigger isolated verification run to confirm test pass status.",
            )
        else:
            return PlanVerificationAssessment(
                status=PlanTestVerificationStatus.NO_TESTS_FOUND,
                is_backed_by_evidence=False,
                snapshot_commit_sha=snapshot_sha,
                warnings=["No test suite or test configuration recognized in repository overview."],
                recommended_action="Add unit tests to the contribution plan.",
            )

    def reconcile_plan_with_verification(
        self,
        plan: ContributionPlan,
        assessment: PlanVerificationAssessment,
    ) -> ContributionPlan:
        """
        Reconciles a contribution plan with the verification assessment.
        Marks steps verified if backed by genuine sandbox execution.
        Neutralizes claims if execution failed or was not performed.
        """
        new_uncertainties = list(plan.uncertainties)
        new_steps: list[ImplementationStep] = []

        if assessment.status == PlanTestVerificationStatus.TESTS_VERIFIED_PASSED:
            ver_note = (
                f"Verified: Tests executed in sandbox ({assessment.passed_count} passed, "
                f"Run ID: {assessment.matched_run_id})."
            )
            for step in plan.implementation_steps:
                desc = step.description
                is_ver = step.is_verified
                if "test" in desc.lower():
                    is_ver = True
                    desc = f"{desc} [Verified in Sandbox]"
                new_steps.append(
                    ImplementationStep(
                        order=step.order,
                        description=desc,
                        rationale=step.rationale,
                        relevant_files=step.relevant_files,
                        evidence=step.evidence,
                        is_verified=is_ver,
                    )
                )
        else:
            # Neutralize claims
            for warning in assessment.warnings:
                if warning not in new_uncertainties:
                    new_uncertainties.append(warning)

            for step in plan.implementation_steps:
                desc = step.description
                if any(k in desc.lower() for k in ["test passed", "tests passed", "verified that tests pass"]):
                    desc = desc.replace("tests passed", "tests to run")
                    desc = desc.replace("test passed", "test to run")
                new_steps.append(
                    ImplementationStep(
                        order=step.order,
                        description=desc,
                        rationale=step.rationale,
                        relevant_files=step.relevant_files,
                        evidence=step.evidence,
                        is_verified=step.is_verified and False,
                    )
                )

        return ContributionPlan(
            session_id=plan.session_id,
            owner=plan.owner,
            repo=plan.repo,
            issue_number=plan.issue_number,
            issue_title=plan.issue_title,
            issue_url=plan.issue_url,
            summary=plan.summary,
            relevant_files=plan.relevant_files,
            implementation_steps=new_steps,
            suggested_tests=plan.suggested_tests,
            prerequisite_concepts=plan.prerequisite_concepts,
            evidence_refs=plan.evidence_refs,
            uncertainties=new_uncertainties,
            assumptions=plan.assumptions,
            ai_generated=plan.ai_generated,
            generated_at=plan.generated_at,
        )
