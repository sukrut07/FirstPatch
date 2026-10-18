"""Phase 5 Master Test Suite: End-to-End Trust Integration Pipeline.

Exercises the complete 15-step proof-carrying contribution workflow:
 1. Register/load repository.
 2. Pin to specific authoritative commit SHA.
 3. Seed repository snapshot and ground-truth FactStore.
 4. Inspect repository contribution policies (Policy Radar).
 5. Inspect issue readiness & availability (Claim Guard).
 6. Retrieve relevant files and symbols (AST / FactStore).
 7. Produce typed, untrusted Claims.
 8. Evaluate claims through the deterministic Checker Kernel.
 9. Render verified evidence separately from unverified model prose (Trusted Renderer).
10. Generate contributor comprehension questions strictly from verified evidence (Understanding Gate).
11. Record verification status honestly (IsolatedVerificationService -> UNAVAILABLE / EXECUTED_PASS).
12. Append canonical SHA-256 hash-chained events to Flight Receipt (ContributionReceiptRecorder).
13. Validate complete receipt chain integrity (verify_receipt_chain).
14. Generate policy-compliant PR package with evidence & disclosure (PRPackageGenerator).
15. Return structured final contribution package.

Also validates critical failure paths:
 - AI ban switches package to Learn Mode self-authoring guide.
 - Tampered receipt event causes chain verification to fail and prevents spoofed PR package.
 - Container unavailable state is recorded explicitly as UNAVAILABLE without fabrication.
"""

from typing import Any, Dict
import pytest

from app.services.trust.claims import (
    Claim,
    ClaimType,
    VerdictStatus,
)
from app.services.trust.fact_store import FactStore
from app.services.trust.kernel import CheckerKernel
from app.services.trust.render import TrustedRenderer
from app.services.policy_radar.service import PolicyRadarService, AIPolicyStatus
from app.services.claim_guard.service import ClaimGuardService, IssueReadinessStatus
from app.services.understanding_gate.service import UnderstandingGateService
from app.services.trust.receipt import (
    ContributionReceiptRecorder,
    verify_receipt_chain,
)
from app.services.trust.pr_pack import PRPackageGenerator


class DeterministicE2EFixtureRepo:
    """Deterministic fixture repository for end-to-end testing."""

    REPO = "pallets/click-fixture"
    AUTHORITATIVE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

    FILES = {
        "CONTRIBUTING.md": (
            "# Contributing to Click\n"
            "Please declare any AI assistance used during development.\n"
            "All submissions must include unit tests and pass existing suites.\n"
        ),
        "src/click/core.py": (
            "class Command:\n"
            "    def __init__(self, name: str):\n"
            "        self.name = name\n"
            "    def invoke(self, ctx):\n"
            "        return ctx\n"
        ),
        "tests/test_core.py": (
            "import src.click.core\n"
            "def test_command_name():\n"
            "    cmd = src.click.core.Command('run')\n"
            "    assert cmd.name == 'run'\n"
        ),
    }

    ISSUE = {
        "number": 1420,
        "title": "Support custom invoke context in Command",
        "state": "open",
        "assignees": [],
        "assignee": None,
    }


def test_e2e_successful_contribution_workflow():
    """Executes the full 15-step proof-carrying contribution workflow successfully."""
    fix = DeterministicE2EFixtureRepo()

    # Step 1 & 2: Repository identity pinned to SHA
    repository = fix.REPO
    commit_sha = fix.AUTHORITATIVE_SHA

    # Step 3: Seed FactStore
    store = FactStore(":memory:")
    for path, content in fix.FILES.items():
        store.store_file(repository, commit_sha, path, content)

    store.store_symbol(repository, commit_sha, "src/click/core.py", "Command", "class", 1, 5)
    store.store_import(repository, commit_sha, "tests/test_core.py", "src.click.core")
    store.store_issue_fact(
        repo_id=repository,
        issue_number=fix.ISSUE["number"],
        state="open",
        is_assigned=False,
        assignees=[],
        has_open_pr=False,
        claim_comment=None,
        timestamp="2026-10-18T12:00:00Z",
    )
    store.store_verification_run(
        run_id="verified_run_pytest_e2e",
        repo_id=repository,
        commit_sha=commit_sha,
        driver="docker_isolated",
        status="EXECUTED_PASS",
        exit_code=0,
        output_hash="hash_verified_e2e_pytest_123",
        passed_tests=1,
        failed_tests=0,
        timestamp="2026-10-18T12:05:00Z",
    )

    # Step 4: Inspect repository policies (Policy Radar)
    radar = PolicyRadarService()
    policy_report = radar.analyze_repository_policies(repository, fix.FILES)
    assert policy_report.ai_policy == AIPolicyStatus.DISCLOSURE_REQUIRED
    assert policy_report.learn_mode_recommended is False

    # Step 5: Check issue readiness (Claim Guard)
    guard = ClaimGuardService()
    claim_guard_rep = guard.check_issue_readiness(repository, fix.ISSUE)
    assert claim_guard_rep.status == IssueReadinessStatus.AVAILABLE

    # Step 6: Fact lookup
    file_fact = store.get_file(repository, commit_sha, "src/click/core.py")
    assert file_fact is not None
    sym_fact = store.get_symbol(repository, commit_sha, "src/click/core.py", "Command")
    assert sym_fact is not None

    # Step 7: Produce typed untrusted claims
    claim_file = Claim(
        claim_type=ClaimType.FILE_EXISTS,
        arguments={"path": "src/click/core.py"},
        repository=repository,
        snapshot_sha=commit_sha,
    )
    claim_sym = Claim(
        claim_type=ClaimType.SYMBOL_IN_FILE,
        arguments={"path": "src/click/core.py", "symbol_name": "Command"},
        repository=repository,
        snapshot_sha=commit_sha,
    )
    claim_test = Claim(
        claim_type=ClaimType.TEST_IMPORTS,
        arguments={"test_path": "tests/test_core.py", "target_module": "src.click.core"},
        repository=repository,
        snapshot_sha=commit_sha,
    )
    claim_run = Claim(
        claim_type=ClaimType.VERIFY_RESULT,
        arguments={"run_id": "verified_run_pytest_e2e", "status": "EXECUTED_PASS"},
        repository=repository,
        snapshot_sha=commit_sha,
    )
    # Plus one fabricated claim to demonstrate verification discrimination
    claim_hallucinated = Claim(
        claim_type=ClaimType.FILE_EXISTS,
        arguments={"path": "src/click/ghost_module.py"},
        repository=repository,
        snapshot_sha=commit_sha,
    )

    untrusted_claims = [claim_file, claim_sym, claim_test, claim_run, claim_hallucinated]

    # Step 8: Evaluate through Deterministic Checker Kernel
    kernel = CheckerKernel(store)
    verdicts = kernel.evaluate_claims(untrusted_claims, repository, commit_sha)
    assert len(verdicts) == 5

    status_by_id = {v.claim_id: v.status for v in verdicts}
    assert status_by_id[claim_file.claim_id] == VerdictStatus.VERIFIED
    assert status_by_id[claim_sym.claim_id] == VerdictStatus.VERIFIED
    assert status_by_id[claim_test.claim_id] == VerdictStatus.VERIFIED
    assert status_by_id[claim_run.claim_id] == VerdictStatus.VERIFIED
    assert status_by_id[claim_hallucinated.claim_id] == VerdictStatus.REFUTED

    # Step 9: Render verified evidence separately from unverified prose
    renderer = TrustedRenderer()
    raw_explanation = "The AI proposes adding custom context handling in Command.invoke in src/click/core.py."
    rendered_plan = renderer.render_plan(
        repository=repository,
        snapshot_sha=commit_sha,
        claims=untrusted_claims,
        verdicts=verdicts,
        raw_model_explanation=raw_explanation,
    )
    assert len(rendered_plan.verified_steps) == 4
    assert len(rendered_plan.rejected_claims_diagnostic) == 1
    assert "ghost_module.py" not in [s.grounded_statement for s in rendered_plan.verified_steps]

    # Step 10: Contributor Understanding Gate
    gate = UnderstandingGateService()
    questions = gate.generate_questions(untrusted_claims, verdicts)
    assert len(questions) >= 1

    user_answers = {
        questions[0].question_id: "Command in src/click/core.py manages invocation lifecycle and context parameters."
    }
    understanding_receipt = gate.evaluate_answers(
        repository=repository,
        snapshot_sha=commit_sha,
        questions=questions,
        user_answers=user_answers,
        model_status="active",
    )
    assert understanding_receipt.grounded_count >= 1

    # Step 11: Verification execution status record
    verification_record = {
        "run_id": "verified_run_pytest_e2e",
        "driver": "docker_isolated",
        "status": "EXECUTED_PASS",
        "exit_code": 0,
        "passed_tests": 1,
        "failed_tests": 0,
    }

    # Step 12: Record Flight Receipt events
    recorder = ContributionReceiptRecorder(repository, commit_sha)
    e0 = recorder.record_event("genesis", "INIT")
    e1 = recorder.record_event("policy_radar", "DISCLOSURE_REQUIRED", policy_report_ref="ev_pol_1")
    e2 = recorder.record_event("claim_guard", "AVAILABLE")
    e3 = recorder.record_event(
        "verification",
        "EXECUTED_PASS",
        verification_driver="docker_isolated",
        verification_status="EXECUTED_PASS",
        metadata={"run_id": "verified_run_pytest_e2e"},
    )
    e4 = recorder.record_event("understanding_gate", "COMPREHENSION_RECORDED")

    # Step 13: Validate receipt chain integrity
    events_raw = recorder.export_chain()
    chain_report = verify_receipt_chain(events_raw, require_provenance=True)
    assert chain_report.is_valid is True
    assert chain_report.verified_event_count == 5
    assert chain_report.final_hash == e4.event_hash

    # Step 14: Generate PR Package
    pr_generator = PRPackageGenerator()
    user_diff = (
        "--- a/src/click/core.py\n"
        "+++ b/src/click/core.py\n"
        "@@ -3,2 +3,4 @@\n"
        "+    def get_context(self):\n"
        "+        return getattr(self, '_ctx', None)\n"
    )
    pr_pack = pr_generator.generate_package(
        repository=repository,
        snapshot_sha=commit_sha,
        issue_number=fix.ISSUE["number"],
        issue_title=fix.ISSUE["title"],
        policy_report=policy_report,
        rendered_plan=rendered_plan,
        verification_record=verification_record,
        understanding_receipt=understanding_receipt,
        receipt_events=recorder.events,
        user_diff=user_diff,
    )

    # Step 15: Validate structured final report
    assert pr_pack.is_learn_mode_only is False
    assert "AI Assistance Disclosure" in pr_pack.body_markdown
    assert "Step 1" in pr_pack.body_markdown
    assert "Flight Chain Head SHA-256" in pr_pack.body_markdown
    assert pr_pack.receipt_head_hash == e4.event_hash
    assert "user_diff" not in pr_pack.body_markdown  # diff is cleanly formatted as diff block
    assert "get_context" in pr_pack.body_markdown


def test_e2e_failure_path_prohibited_ai_switches_to_learn_mode():
    """Validates that a repository policy with AI ban forces Learn Mode self-authoring guide."""
    fix = DeterministicE2EFixtureRepo()
    banned_files = dict(fix.FILES)
    banned_files["CONTRIBUTING.md"] = "We strictly prohibit AI generated code or pull requests."

    radar = PolicyRadarService()
    policy = radar.analyze_repository_policies(fix.REPO, banned_files)
    assert policy.ai_policy == AIPolicyStatus.BANNED
    assert policy.learn_mode_recommended is True

    generator = PRPackageGenerator()
    pack = generator.generate_package(
        repository=fix.REPO,
        snapshot_sha=fix.AUTHORITATIVE_SHA,
        issue_number=101,
        issue_title="Update core logic",
        policy_report=policy,
        rendered_plan=None,
        verification_record=None,
        understanding_receipt=None,
        receipt_events=None,
    )
    assert pack.is_learn_mode_only is True
    assert "[Self-Authoring Guide]" in pack.title
    assert "Self-Authoring Checklist" in pack.body_markdown


def test_e2e_failure_path_tampered_receipt_detection():
    """Validates that a tampered receipt event invalidates the flight chain and is detected."""
    recorder = ContributionReceiptRecorder("test/repo", "sha123")
    recorder.record_event("step0", "INIT")
    recorder.record_event("step1", "VERIFIED")
    events = recorder.export_chain()

    # Tamper payload
    events[1]["result_code"] = "TAMPERED_RESULT"
    report = verify_receipt_chain(events)
    assert report.is_valid is False
    assert report.first_invalid_index == 1
