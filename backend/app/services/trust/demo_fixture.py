"""Deterministic Demo Fixture & Sanitized Observability Service.

Provides labeled synthetic demo scenarios demonstrating:
 1. A verified claim (FILE_EXISTS, SYMBOL_IN_FILE).
 2. A refuted or stale claim (hallucinated file, commit SHA mismatch).
 3. An unknown claim (absent policy/issue fact, unrecorded run).
 4. A prohibited-AI policy (forcing Learn Mode).
 5. An unavailable verification environment (safe UNAVAILABLE reporting).
 6. A valid receipt vs. a tampered receipt.

CRITICAL: All demo data is strictly marked with `is_synthetic: True`.
It is never represented as live GitHub data, live AI inference, or real execution.
Includes structured sanitized logging utility that excludes secrets.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict
from uuid import uuid4
from pydantic import BaseModel, Field

from app.services.trust.claims import (
    Claim,
    ClaimType,
)
from app.services.trust.fact_store import FactStore
from app.services.trust.kernel import CheckerKernel
from app.services.policy_radar.service import (
    PolicyRadarService,
)
from app.services.trust.receipt import (
    ContributionReceiptRecorder,
    verify_receipt_chain,
)

logger = logging.getLogger("firstpatch.trust.demo")


class StructuredAuditLogEntry(BaseModel):
    """Sanitized structured log entry."""
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    repository: str
    snapshot_sha: str
    claim_type: str
    verdict: str
    verification_driver: str
    verification_status: str
    model_provider_status: str
    receipt_validation_valid: bool
    failure_category: str = "none"
    duration_ms: float = 0.0


def log_sanitized_trust_event(
    repository: str,
    snapshot_sha: str,
    claim_type: str,
    verdict: str,
    verification_driver: str,
    verification_status: str,
    model_provider_status: str,
    receipt_validation_valid: bool,
    failure_category: str = "none",
    duration_ms: float = 0.0,
) -> StructuredAuditLogEntry:
    """Emits structured, sanitized logs without logging authorization headers, keys, or sensitive payload."""
    entry = StructuredAuditLogEntry(
        repository=repository,
        snapshot_sha=snapshot_sha[:8] if snapshot_sha else "none",
        claim_type=claim_type,
        verdict=verdict,
        verification_driver=verification_driver,
        verification_status=verification_status,
        model_provider_status=model_provider_status,
        receipt_validation_valid=receipt_validation_valid,
        failure_category=failure_category,
        duration_ms=round(duration_ms, 2),
    )
    logger.info("TRUST_AUDIT_LOG: %s", entry.model_dump_json())
    return entry


class SyntheticDemoPackage(BaseModel):
    is_synthetic: bool = True
    notice: str = (
        "SYNTHETIC DEMO FIXTURE: This dataset is entirely synthetic for deterministic demonstration "
        "and is NEVER represented as live GitHub facts, live AI generation, or real code execution."
    )
    repository: str = "demo-org/synthetic-firstpatch-demo"
    snapshot_sha: str = "deadbeef00001111222233334444555566667777"
    verified_claim_example: Dict[str, Any]
    refuted_claim_example: Dict[str, Any]
    stale_claim_example: Dict[str, Any]
    unknown_claim_example: Dict[str, Any]
    prohibited_ai_policy_report: Dict[str, Any]
    unavailable_verification_example: Dict[str, Any]
    valid_receipt_report: Dict[str, Any]
    tampered_receipt_report: Dict[str, Any]


def generate_synthetic_demo_package() -> SyntheticDemoPackage:
    """Constructs a deterministic, fully self-contained demo bundle."""
    repo = "demo-org/synthetic-firstpatch-demo"
    authoritative_sha = "deadbeef00001111222233334444555566667777"

    store = FactStore(":memory:")
    store.store_file(
        repo,
        authoritative_sha,
        "src/calculator.py",
        "def add(a: int, b: int) -> int:\n    return a + b\n",
    )
    store.store_symbol(repo, authoritative_sha, "src/calculator.py", "add", "function", 1, 2)
    store.store_verification_run(
        run_id="demo_docker_run",
        repo_id=repo,
        commit_sha=authoritative_sha,
        driver="docker_isolated",
        status="EXECUTED_PASS",
        exit_code=0,
        output_hash="demo_hash_123",
        passed_tests=5,
        failed_tests=0,
        timestamp="2026-10-18T10:00:00Z",
    )

    kernel = CheckerKernel(store)

    # 1. Verified claim
    c_verified = Claim(
        claim_type=ClaimType.SYMBOL_IN_FILE,
        arguments={"path": "src/calculator.py", "symbol_name": "add"},
        repository=repo,
        snapshot_sha=authoritative_sha,
    )
    v_verified = kernel.verify_claim(c_verified, authoritative_sha)

    # 2. Refuted claim
    c_refuted = Claim(
        claim_type=ClaimType.FILE_EXISTS,
        arguments={"path": "src/phantom_nonexistent.py"},
        repository=repo,
        snapshot_sha=authoritative_sha,
    )
    v_refuted = kernel.verify_claim(c_refuted, authoritative_sha)

    # 3. Stale claim
    c_stale = Claim(
        claim_type=ClaimType.SYMBOL_IN_FILE,
        arguments={"path": "src/calculator.py", "symbol_name": "add"},
        repository=repo,
        snapshot_sha="old_commit_00000000000000000000000000000000",
    )
    v_stale = kernel.verify_claim(c_stale, authoritative_sha)

    # 4. Unknown claim
    c_unknown = Claim(
        claim_type=ClaimType.POLICY_FACT,
        arguments={"policy_type": "security_disclosure_policy", "value": "required"},
        repository=repo,
        snapshot_sha=authoritative_sha,
    )
    v_unknown = kernel.verify_claim(c_unknown, authoritative_sha)

    # 5. Prohibited AI policy
    radar = PolicyRadarService()
    files = {"CONTRIBUTING.md": "# Contribution Guide\nWe do not accept AI-generated code or pull requests."}
    banned_report = radar.analyze_repository_policies(repo, files)

    # 6. Unavailable verification
    unavailable_demo = {
        "status": "UNAVAILABLE",
        "driver": "docker_isolated",
        "message": "Docker CLI/daemon is not accessible on host. Host execution is strictly prohibited by FirstPatch AI.",
        "tests_executed": 0,
        "is_fallback": True,
    }

    # 7. Valid and tampered receipts
    recorder = ContributionReceiptRecorder(repo, authoritative_sha)
    recorder.record_event("genesis", "INIT")
    recorder.record_event("policy_check", "POLICY_VERIFIED")
    valid_chain = recorder.export_chain()
    valid_rep = verify_receipt_chain(valid_chain)

    tampered_chain = [dict(e) for e in valid_chain]
    tampered_chain[1]["result_code"] = "TAMPERED_PAYLOAD"
    tampered_rep = verify_receipt_chain(tampered_chain)

    return SyntheticDemoPackage(
        verified_claim_example={"claim": c_verified.model_dump(), "verdict": v_verified.model_dump()},
        refuted_claim_example={"claim": c_refuted.model_dump(), "verdict": v_refuted.model_dump()},
        stale_claim_example={"claim": c_stale.model_dump(), "verdict": v_stale.model_dump()},
        unknown_claim_example={"claim": c_unknown.model_dump(), "verdict": v_unknown.model_dump()},
        prohibited_ai_policy_report=banned_report.model_dump(),
        unavailable_verification_example=unavailable_demo,
        valid_receipt_report=valid_rep.model_dump(),
        tampered_receipt_report=tampered_rep.model_dump(),
    )
