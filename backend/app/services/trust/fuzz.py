"""Kernel Mutation Testing Framework (Fuzz & Adversarial Claim Testing).

Applies controlled adversarial mutations to known-valid claims and receipt events to
prove the deterministic kernel catches fabrications, corruptions, and injection bypasses.
Calculates exact catch rate and false-rejection rate.
"""

import copy
from typing import Any, Dict, List, Tuple
from pydantic import BaseModel, Field
from app.services.trust.claims import Claim, ClaimType, VerdictStatus
from app.services.trust.kernel import CheckerKernel
from app.services.trust.receipt import (
    ContributionReceiptRecorder,
    verify_receipt_chain,
)


class MutationTestResult(BaseModel):
    mutation_name: str
    original_claim_type: str
    mutated_claim: Dict[str, Any]
    verdict_status: str
    reason_code: str
    caught: bool  # True if status is REFUTED, STALE, or UNKNOWN (not VERIFIED)


class MutationSuiteReport(BaseModel):
    total_valid_claims_tested: int
    total_mutations_tested: int
    mutations_detected: int
    mutations_escaped: int
    false_rejections: int
    catch_rate: float
    false_reject_rate: float
    results: List[MutationTestResult] = Field(default_factory=list)


class KernelMutationFuzzer:
    def __init__(self, kernel: CheckerKernel):
        self.kernel = kernel

    def run_mutation_suite(
        self,
        base_valid_claims: List[Claim],
        repository: str,
        authoritative_sha: str,
    ) -> MutationSuiteReport:
        # 1. Test baseline valid claims to ensure false_rejections == 0
        false_rejections = 0
        for c in base_valid_claims:
            verdict = self.kernel.verify_claim(c, authoritative_sha)
            if verdict.status != VerdictStatus.VERIFIED:
                false_rejections += 1

        # 2. Generate controlled mutations
        mutations: List[Tuple[str, Claim]] = []

        for c in base_valid_claims:
            # Mutation 1: Path typo
            if "path" in c.arguments:
                m1 = copy.deepcopy(c)
                m1.arguments["path"] = m1.arguments["path"] + "_typo.py"
                mutations.append(("path_typo", m1))

            # Mutation 2: Directory traversal
            if "path" in c.arguments:
                m2 = copy.deepcopy(c)
                m2.arguments["path"] = "../../../etc/passwd"
                mutations.append(("path_traversal", m2))

            # Mutation 3: Wrong snapshot SHA (stale claim)
            m3 = copy.deepcopy(c)
            m3.snapshot_sha = "deadbeef12345678" * 4
            mutations.append(("stale_snapshot_sha", m3))

            # Mutation 4: Fabricated symbol
            if c.claim_type == ClaimType.SYMBOL_IN_FILE:
                m4 = copy.deepcopy(c)
                m4.arguments["symbol_name"] = "fabricated_symbol_xyz_999"
                mutations.append(("fabricated_symbol", m4))

            # Mutation 5: Invalid line range
            if c.claim_type == ClaimType.LINES_CONTAIN:
                m5 = copy.deepcopy(c)
                m5.arguments["start_line"] = 99999
                m5.arguments["end_line"] = 100000
                mutations.append(("invalid_line_range", m5))

            # Mutation 6: Mock driver claiming EXECUTED_PASS
            if c.claim_type == ClaimType.VERIFY_RESULT:
                m6 = copy.deepcopy(c)
                m6.arguments["status"] = "EXECUTED_PASS"
                mutations.append(("mock_claiming_executed_pass", m6))

        # Mutation 7: Missing required argument
        m7 = Claim(
            claim_type=ClaimType.FILE_EXISTS,
            arguments={},  # missing path
            repository=repository,
            snapshot_sha=authoritative_sha,
        )
        mutations.append(("missing_required_arguments", m7))

        # Mutation 8: Fake verify run ID
        m8 = Claim(
            claim_type=ClaimType.VERIFY_RESULT,
            arguments={"run_id": "non_existent_run_404", "status": "EXECUTED_PASS"},
            repository=repository,
            snapshot_sha=authoritative_sha,
        )
        mutations.append(("fake_verify_run_id", m8))

        # Evaluate mutations against kernel
        results: List[MutationTestResult] = []
        detected_count = 0
        escaped_count = 0

        for mut_name, mut_claim in mutations:
            v = self.kernel.verify_claim(mut_claim, authoritative_sha)
            # Caught if it is NOT marked VERIFIED
            caught = (v.status != VerdictStatus.VERIFIED)
            if caught:
                detected_count += 1
            else:
                escaped_count += 1

            results.append(
                MutationTestResult(
                    mutation_name=mut_name,
                    original_claim_type=mut_claim.claim_type.value,
                    mutated_claim=mut_claim.model_dump(),
                    verdict_status=v.status.value,
                    reason_code=v.reason_code,
                    caught=caught,
                )
            )

        total_mutations = len(mutations)
        catch_rate = round(detected_count / total_mutations, 4) if total_mutations > 0 else 1.0
        false_reject_rate = (
            round(false_rejections / len(base_valid_claims), 4) if base_valid_claims else 0.0
        )

        return MutationSuiteReport(
            total_valid_claims_tested=len(base_valid_claims),
            total_mutations_tested=total_mutations,
            mutations_detected=detected_count,
            mutations_escaped=escaped_count,
            false_rejections=false_rejections,
            catch_rate=catch_rate,
            false_reject_rate=false_reject_rate,
            results=results,
        )

    @staticmethod
    def test_receipt_tampering(recorder: ContributionReceiptRecorder) -> Dict[str, Any]:
        """Tests that corrupted hashes, altered sequence, or broken links in receipts are caught."""
        events = recorder.export_chain()
        if len(events) < 2:
            return {"error": "At least 2 events required to test tampering."}

        # Tamper 1: Alter event hash of event 1
        tampered_hash = copy.deepcopy(events)
        tampered_hash[1]["event_hash"] = "f" * 64
        rep1 = verify_receipt_chain(tampered_hash)

        # Tamper 2: Break prev_hash pointer
        tampered_prev = copy.deepcopy(events)
        tampered_prev[1]["prev_hash"] = "e" * 64
        rep2 = verify_receipt_chain(tampered_prev)

        # Tamper 3: Alter sequence number
        tampered_seq = copy.deepcopy(events)
        tampered_seq[1]["sequence_number"] = 99
        rep3 = verify_receipt_chain(tampered_seq)

        return {
            "tampered_hash_caught": not rep1.is_valid,
            "tampered_prev_caught": not rep2.is_valid,
            "tampered_sequence_caught": not rep3.is_valid,
            "all_tamper_attacks_detected": (
                not rep1.is_valid and not rep2.is_valid and not rep3.is_valid
            ),
        }
