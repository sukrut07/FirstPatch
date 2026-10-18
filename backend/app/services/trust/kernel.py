"""Deterministic Checker Kernel for Proof-Carrying Contributions.

The kernel is the trust boundary of FirstPatch AI. Proposers (LLMs, tools)
submit untrusted Claim objects. The Kernel dispatches to deterministic checkers
and emits non-forgeable Verdict objects.
"""

import logging
from typing import Callable, Dict, List
from app.services.trust.claims import (
    Claim,
    ClaimType,
    Verdict,
    VerdictStatus,
    KERNEL_SECRET_DEFAULT,
    compute_verdict_seal,
)
from app.services.trust.fact_store import FactStore
from app.services.trust.checkers import (
    check_file_exists,
    check_symbol_in_file,
    check_lines_contain,
    check_imported_by,
    check_test_imports,
    check_policy_fact,
    check_issue_unclaimed,
    check_verify_result,
    check_review_theme,
)

logger = logging.getLogger(__name__)

CheckerFn = Callable[[Claim, FactStore, str], Verdict]


class CheckerKernel:
    def __init__(self, fact_store: FactStore, secret: str = KERNEL_SECRET_DEFAULT):
        self.fact_store = fact_store
        self.secret = secret
        self._registry: Dict[ClaimType, CheckerFn] = {
            ClaimType.FILE_EXISTS: check_file_exists,
            ClaimType.SYMBOL_IN_FILE: check_symbol_in_file,
            ClaimType.LINES_CONTAIN: check_lines_contain,
            ClaimType.IMPORTED_BY: check_imported_by,
            ClaimType.TEST_IMPORTS: check_test_imports,
            ClaimType.POLICY_FACT: check_policy_fact,
            ClaimType.ISSUE_UNCLAIMED: check_issue_unclaimed,
            ClaimType.VERIFY_RESULT: check_verify_result,
            ClaimType.REVIEW_THEME_SUPPORTED: check_review_theme,
        }

    def seal_verdict(self, verdict: Verdict) -> Verdict:
        """Applies a tamper-evident cryptographic kernel seal to an issued verdict."""
        verdict.kernel_seal = compute_verdict_seal(
            claim_id=verdict.claim_id,
            status=verdict.status.value if isinstance(verdict.status, VerdictStatus) else str(verdict.status),
            snapshot_sha=verdict.snapshot_sha,
            reason_code=verdict.reason_code,
            secret=self.secret,
        )
        return verdict

    def is_verdict_authentic(self, verdict: Verdict) -> bool:
        """Validates that a verdict was genuinely generated and sealed by the kernel."""
        return verdict.is_sealed_by_kernel(self.secret)

    def verify_claim(self, claim: Claim, authoritative_sha: str) -> Verdict:
        # 1. Snapshot SHA validation: Stale if mismatch or empty
        if not claim.snapshot_sha or claim.snapshot_sha != authoritative_sha:
            return self.seal_verdict(
                Verdict(
                    claim_id=claim.claim_id,
                    status=VerdictStatus.STALE,
                    snapshot_sha=authoritative_sha,
                    reason_code="SHA_MISMATCH",
                    explanation=(
                        f"Claim snapshot {claim.snapshot_sha[:8] if claim.snapshot_sha else 'EMPTY'} does not match "
                        f"authoritative snapshot {authoritative_sha[:8]}."
                    ),
                )
            )

        # 2. Dispatch to registered checker
        checker = self._registry.get(claim.claim_type)
        if not checker:
            return self.seal_verdict(
                Verdict(
                    claim_id=claim.claim_id,
                    status=VerdictStatus.UNKNOWN,
                    snapshot_sha=authoritative_sha,
                    reason_code="UNSUPPORTED_CLAIM_TYPE",
                    explanation=f"No registered deterministic checker for claim type '{claim.claim_type}'.",
                )
            )

        # 3. Secure execution: Catch exceptions and return UNKNOWN
        try:
            verdict = checker(claim, self.fact_store, authoritative_sha)
            return self.seal_verdict(verdict)
        except Exception as ex:
            logger.exception("Checker exception on claim %s: %s", claim.claim_id, ex)
            return self.seal_verdict(
                Verdict(
                    claim_id=claim.claim_id,
                    status=VerdictStatus.UNKNOWN,
                    snapshot_sha=authoritative_sha,
                    reason_code="CHECKER_EXCEPTION",
                    explanation=f"Checker encountered an internal error: {ex}",
                )
            )

    def evaluate_claims(
        self,
        claims: List[Claim],
        repository: str,
        authoritative_sha: str,
    ) -> List[Verdict]:
        results: List[Verdict] = []
        for claim in claims:
            # Enforce repository match
            if claim.repository != repository:
                results.append(
                    self.seal_verdict(
                        Verdict(
                            claim_id=claim.claim_id,
                            status=VerdictStatus.REFUTED,
                            snapshot_sha=authoritative_sha,
                            reason_code="REPOSITORY_MISMATCH",
                            explanation=f"Claim repository '{claim.repository}' contradicts target '{repository}'.",
                        )
                    )
                )
                continue
            results.append(self.verify_claim(claim, authoritative_sha))
        return results

