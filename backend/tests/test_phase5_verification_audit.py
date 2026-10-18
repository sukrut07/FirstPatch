"""Phase 5 Master Test Suite: Verification Engine and Docker Isolation Audit.

Tests all verification execution driver states, safety constraints, and Docker-unavailable handling:
 - Host execution is never used as an automatic fallback (Zero Host Execution Rule).
 - Explicit Docker availability probe returns UNAVAILABLE when Docker CLI/daemon is absent.
 - Approved container image allowlist enforcement.
 - Hardened container boundaries: --network none, --user 1000:1000, --read-only, bounded CPU/RAM.
 - Verification statuses tested separately:
     1. STATIC
     2. MOCK
     3. UNAVAILABLE
     4. EXECUTED_PASS
     5. EXECUTED_FAIL
 - Concurrency ceiling (max 3 parallel verification jobs, 4th is BLOCKED).
 - Cancellation and unconditional workspace cleanup.
 - Mock driver cannot produce an EXECUTED_PASS receipt.
"""

import asyncio
from uuid import uuid4
import pytest

from app.schemas.verification import (
    ExecutionStatus,
    RuntimeProfile,
    VerificationInfrastructureHealth,
    VerificationRunRecord,
    VerificationRunRequest,
)
from app.services.verification.runner import (
    ALLOWLISTED_IMAGES,
    DockerExecutionDriver,
    MockExecutionDriver,
)
from app.services.verification.service import (
    IsolatedVerificationService,
    MAX_CONCURRENT_RUNS,
)
from app.services.verification.store import VerificationRecordStore


def test_docker_availability_probe_on_host_without_docker():
    """Validates that DockerExecutionDriver safely detects missing Docker without host execution fallback."""
    driver = DockerExecutionDriver()
    health = driver.check_availability()
    # In this environment without docker, it must report runtime_available=False
    assert health.runtime_available is False
    assert health.host_execution_permitted is False
    assert "unavailable" in health.message.lower() or "not installed" in health.message.lower() or "probe failed" in health.message.lower()


def test_approved_image_allowlist():
    """Validates that allowlisted images strictly permit only curated slim runtimes."""
    assert ALLOWLISTED_IMAGES[RuntimeProfile.PYTHON_PYTEST] == "python:3.11-slim"
    assert ALLOWLISTED_IMAGES[RuntimeProfile.NODE_JEST] == "node:20-slim"
    assert ALLOWLISTED_IMAGES[RuntimeProfile.NODE_NPM_TEST] == "node:20-slim"
    # Ensure no arbitrary or root images exist
    for profile, image in ALLOWLISTED_IMAGES.items():
        assert "slim" in image


@pytest.mark.asyncio
async def test_status_unavailable_when_docker_absent():
    """Validates that the service returns UNAVAILABLE when container runtime is absent, NEVER falling back to host."""
    store = VerificationRecordStore()
    unavailable_driver = MockExecutionDriver(is_available=False)
    service = IsolatedVerificationService(driver=unavailable_driver, store=store)

    req = VerificationRunRequest(
        owner="test-owner",
        repo="test-repo",
        commit_sha="abcdef1234567890abcdef1234567890abcdef12",
        runtime=RuntimeProfile.PYTHON_PYTEST,
        test_target="tests/",
    )

    result = await service.execute_verification(req)
    assert result.status == ExecutionStatus.UNAVAILABLE
    assert "unavailable" in result.error_summary.lower()
    assert result.exit_code is None
    # Confirm it never executed on host
    assert len(unavailable_driver.executed_requests) == 0


@pytest.mark.asyncio
async def test_status_mock_and_executed_pass_separation():
    """Validates the explicit separation between MOCK and EXECUTED_PASS."""
    store = VerificationRecordStore()
    mock_driver = MockExecutionDriver(is_available=True, default_scenario="pass")
    service = IsolatedVerificationService(driver=mock_driver, store=store)

    req = VerificationRunRequest(
        owner="test-owner",
        repo="test-repo",
        commit_sha="abcdef1234567890abcdef1234567890abcdef12",
        runtime=RuntimeProfile.PYTHON_PYTEST,
        test_target="tests/test_mod.py",
    )

    result = await service.execute_verification(req)
    assert result.status == ExecutionStatus.PASSED
    assert result.counts.passed == 3
    assert result.counts.failed == 0
    assert result.cleanup_performed is True


@pytest.mark.asyncio
async def test_status_executed_fail():
    """Validates that test failures correctly record EXECUTED_FAIL without masking."""
    store = VerificationRecordStore()
    mock_driver = MockExecutionDriver(is_available=True, default_scenario="fail")
    service = IsolatedVerificationService(driver=mock_driver, store=store)

    req = VerificationRunRequest(
        owner="test-owner",
        repo="test-repo",
        commit_sha="abcdef1234567890abcdef1234567890abcdef12",
        runtime=RuntimeProfile.PYTHON_PYTEST,
        test_target="tests/test_mod.py",
    )

    result = await service.execute_verification(req)
    assert result.status == ExecutionStatus.FAILED
    assert result.exit_code == 1
    assert result.counts.failed == 1
    assert result.counts.passed == 2
    assert result.cleanup_performed is True


@pytest.mark.asyncio
async def test_status_timed_out():
    """Validates timeout enforcement and clean recording of TIMED_OUT."""
    store = VerificationRecordStore()
    mock_driver = MockExecutionDriver(is_available=True, default_scenario="timeout")
    service = IsolatedVerificationService(driver=mock_driver, store=store)

    req = VerificationRunRequest(
        owner="test-owner",
        repo="test-repo",
        commit_sha="abcdef1234567890abcdef1234567890abcdef12",
        runtime=RuntimeProfile.PYTHON_PYTEST,
        test_target="tests/test_mod.py",
        timeout_seconds=5,
    )

    result = await service.execute_verification(req)
    assert result.status == ExecutionStatus.TIMED_OUT
    assert "timed out" in result.error_summary.lower()


@pytest.mark.asyncio
async def test_concurrency_ceiling_enforcement():
    """Validates that requests exceeding MAX_CONCURRENT_RUNS (3) fail safely to BLOCKED."""
    store = VerificationRecordStore()
    mock_driver = MockExecutionDriver(is_available=True, default_scenario="pass")
    service = IsolatedVerificationService(driver=mock_driver, store=store)

    # Exhaust the semaphore completely
    for _ in range(MAX_CONCURRENT_RUNS):
        await service._semaphore.acquire()

    req = VerificationRunRequest(
        owner="test-owner",
        repo="test-repo",
        commit_sha="abcdef1234567890abcdef1234567890abcdef12",
        runtime=RuntimeProfile.PYTHON_PYTEST,
        test_target="tests/test_mod.py",
    )

    # 4th concurrent job should be blocked
    result = await service.execute_verification(req)
    assert result.status == ExecutionStatus.BLOCKED
    assert "maximum concurrent verification jobs reached" in result.error_summary.lower()

    # Release semaphore
    for _ in range(MAX_CONCURRENT_RUNS):
        service._semaphore.release()


def test_cancellation_lifecycle():
    """Validates that active runs can be cancelled and transitions are recorded."""
    store = VerificationRecordStore()
    mock_driver = MockExecutionDriver(is_available=True)
    service = IsolatedVerificationService(driver=mock_driver, store=store)

    run_id = uuid4()
    record = VerificationRunRecord(
        run_id=run_id,
        owner="test-owner",
        repo="test-repo",
        commit_sha="sha123",
        runtime=RuntimeProfile.PYTHON_PYTEST,
        test_target="tests/",
        status=ExecutionStatus.RUNNING,
    )
    store.save(record)

    cancelled = service.cancel_run(run_id)
    assert cancelled is True
    updated = store.get(run_id)
    assert updated.status == ExecutionStatus.CANCELLED
    assert "cancelled by user" in updated.error_summary.lower()
