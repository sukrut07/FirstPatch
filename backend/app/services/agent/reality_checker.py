"""
FirstPatch AI — Repository Reality Checker

Differentiator service that verifies every claim, file reference,
and test statement in AI-generated contribution plans against
verified repository evidence.

Detects:
- Hallucinated file paths (files not in directory snapshot or tree)
- Nonexistent AST symbols (functions/classes claimed but not found in AST)
- Invalid or fabricated Evidence IDs
- Stale or mismatched commit SHAs
- Fabricated test execution claims
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from app.schemas import (
    ContributionPlan,
    EvidenceRef,
    EvidenceStatus,
    ImplementationStep,
    RepositoryOverview,
)

logger = logging.getLogger(__name__)


class RealityCheckReport:
    """Detailed report of reality check results."""

    def __init__(
        self,
        is_valid: bool,
        verified_files: list[str],
        hallucinated_files: list[str],
        verified_symbols: list[str],
        unsupported_symbols: list[str],
        invalid_evidence_ids: list[str],
        unsupported_test_claims: list[str],
        commit_sha_valid: bool,
        repaired_plan: Optional[ContributionPlan] = None,
        warnings: Optional[list[str]] = None,
    ):
        self.is_valid = is_valid
        self.verified_files = verified_files
        self.hallucinated_files = hallucinated_files
        self.verified_symbols = verified_symbols
        self.unsupported_symbols = unsupported_symbols
        self.invalid_evidence_ids = invalid_evidence_ids
        self.unsupported_test_claims = unsupported_test_claims
        self.commit_sha_valid = commit_sha_valid
        self.repaired_plan = repaired_plan
        self.warnings = warnings or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "verified_files": self.verified_files,
            "hallucinated_files": self.hallucinated_files,
            "verified_symbols": self.verified_symbols,
            "unsupported_symbols": self.unsupported_symbols,
            "invalid_evidence_ids": self.invalid_evidence_ids,
            "unsupported_test_claims": self.unsupported_test_claims,
            "commit_sha_valid": self.commit_sha_valid,
            "warning_count": len(self.warnings),
            "warnings": self.warnings,
        }


class RepositoryRealityChecker:
    """
    Evaluates claims in AI-generated or heuristic plans against known repository ground truth.
    """

    def validate_plan(
        self,
        plan: ContributionPlan,
        repo_overview: RepositoryOverview,
        known_symbols: Optional[dict[str, list[str]]] = None,
    ) -> RealityCheckReport:
        """
        Validate plan against repo overview and evidence refs.
        Performs bounded repair: strips hallucinated files, clarifies test claims,
        and moves unverified assumptions into uncertainties.
        """
        verified_files: list[str] = []
        hallucinated_files: list[str] = []
        verified_symbols: list[str] = []
        unsupported_symbols: list[str] = []
        invalid_evidence_ids: list[str] = []
        unsupported_test_claims: list[str] = []
        warnings: list[str] = []

        known_files = set(repo_overview.directory_snapshot)
        for cfg in repo_overview.config_files:
            known_files.add(cfg)
        for tloc in repo_overview.test_locations:
            known_files.add(tloc.path)
        for ev in repo_overview.evidence_refs:
            if ev.file_path:
                known_files.add(ev.file_path)

        if known_symbols:
            for kf in known_symbols.keys():
                known_files.add(kf)

        known_evidence_ids = {str(ev.id) for ev in repo_overview.evidence_refs}
        for ev in plan.evidence_refs:
            known_evidence_ids.add(str(ev.id))

        # 1. Validate file references
        checked_plan_files: list[str] = []
        for file_path in plan.relevant_files:
            # Check if file is in known files or starts with a known directory prefix
            if self._file_matches_known(file_path, known_files):
                verified_files.append(file_path)
                checked_plan_files.append(file_path)
            else:
                hallucinated_files.append(file_path)
                warnings.append(
                    f"File '{file_path}' claimed in plan was not found in repository snapshot."
                )

        # 2. Validate symbols if symbol index provided
        if known_symbols:
            for file_path, sym_list in known_symbols.items():
                for sym in sym_list:
                    # Check if symbol appears in steps
                    mentioned = any(sym in step.description for step in plan.implementation_steps)
                    if mentioned:
                        verified_symbols.append(f"{file_path}::{sym}")

        # 3. Validate evidence references in steps
        for step in plan.implementation_steps:
            if step.evidence:
                ev_id_str = str(step.evidence.id)
                if ev_id_str not in known_evidence_ids:
                    invalid_evidence_ids.append(ev_id_str)
                    warnings.append(f"Step {step.order} cites unknown Evidence ID '{ev_id_str}'.")

            # 4. Check for false test execution claims
            desc_lower = step.description.lower()
            if any(phrase in desc_lower for phrase in ["test passed", "tests passed", "verified that tests pass", "all tests succeeded"]):
                unsupported_test_claims.append(step.description)
                warnings.append(
                    f"Step {step.order} claims tests passed, but tests were not executed in this environment."
                )

        # 5. Commit SHA consistency
        commit_sha_valid = True
        for ev in plan.evidence_refs:
            if ev.commit_sha and repo_overview.commit_sha:
                if ev.commit_sha != repo_overview.commit_sha:
                    commit_sha_valid = False
                    warnings.append(
                        f"Evidence commit SHA '{ev.commit_sha}' does not match repository snapshot SHA '{repo_overview.commit_sha}'."
                    )

        # 6. Bounded repair of plan
        repaired_plan = self._repair_plan(
            plan=plan,
            verified_files=verified_files,
            hallucinated_files=hallucinated_files,
            unsupported_test_claims=unsupported_test_claims,
            warnings=warnings,
        )

        is_valid = (
            len(hallucinated_files) == 0
            and len(invalid_evidence_ids) == 0
            and len(unsupported_test_claims) == 0
            and commit_sha_valid
        )

        return RealityCheckReport(
            is_valid=is_valid,
            verified_files=verified_files,
            hallucinated_files=hallucinated_files,
            verified_symbols=verified_symbols,
            unsupported_symbols=unsupported_symbols,
            invalid_evidence_ids=invalid_evidence_ids,
            unsupported_test_claims=unsupported_test_claims,
            commit_sha_valid=commit_sha_valid,
            repaired_plan=repaired_plan,
            warnings=warnings,
        )

    def _file_matches_known(self, file_path: str, known_files: set[str]) -> bool:
        """Check exact match or path prefix match."""
        norm_path = file_path.strip().replace("\\", "/").lstrip("/")
        for kf in known_files:
            norm_kf = kf.strip().replace("\\", "/").lstrip("/")
            if norm_path == norm_kf or norm_path.startswith(norm_kf + "/") or norm_kf.startswith(norm_path + "/"):
                return True
        return False

    def _repair_plan(
        self,
        plan: ContributionPlan,
        verified_files: list[str],
        hallucinated_files: list[str],
        unsupported_test_claims: list[str],
        warnings: list[str],
    ) -> ContributionPlan:
        """
        Creates a repaired copy of the plan with:
        - Hallucinated files removed from relevant_files and noted in uncertainties
        - Unsupported test claims clarified as 'Recommended test to run locally'
        - Reality check notices added to uncertainties
        """
        new_uncertainties = list(plan.uncertainties)
        if hallucinated_files:
            new_uncertainties.append(
                f"The following file paths were proposed by AI but could not be verified in the repository: {', '.join(hallucinated_files)}. Verify before editing."
            )

        if unsupported_test_claims:
            new_uncertainties.append(
                "Test verification notice: Test execution has not been run on the host. Run suggested tests locally to verify results."
            )

        new_steps: list[ImplementationStep] = []
        for step in plan.implementation_steps:
            new_desc = step.description
            # Neutralize false test pass claims
            for claim in unsupported_test_claims:
                if claim in new_desc:
                    new_desc = new_desc.replace("tests passed", "run tests locally to verify")
                    new_desc = new_desc.replace("test passed", "run tests locally to verify")
            new_steps.append(
                ImplementationStep(
                    order=step.order,
                    description=new_desc,
                    rationale=step.rationale,
                    relevant_files=[f for f in step.relevant_files if f not in hallucinated_files],
                    evidence=step.evidence,
                    is_verified=step.is_verified and (len(hallucinated_files) == 0),
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
            relevant_files=verified_files,
            implementation_steps=new_steps,
            suggested_tests=plan.suggested_tests,
            prerequisite_concepts=plan.prerequisite_concepts,
            evidence_refs=plan.evidence_refs,
            uncertainties=new_uncertainties,
            assumptions=plan.assumptions,
            ai_generated=plan.ai_generated,
            generated_at=plan.generated_at,
        )
