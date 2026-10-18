"""Comprehensive Unit & Integration Tests for Proof-Carrying Trust Kernel & FactStore."""

import pytest
from app.services.trust.claims import Claim, ClaimType, VerdictStatus
from app.services.trust.fact_store import FactStore, normalize_repo_path
from app.services.trust.kernel import CheckerKernel
from app.services.trust.render import TrustedRenderer


@pytest.fixture
def trust_env():
    store = FactStore(":memory:")
    repo = "test-owner/test-repo"
    sha = "1111222233334444555566667777888899990000"

    # Store files
    store.store_file(repo, sha, "app/main.py", "from app.core import config\n\ndef run():\n    return 'running'\n")
    store.store_file(repo, sha, "app/core.py", "def get_config():\n    return {'debug': True}\n")
    store.store_file(repo, sha, "tests/test_main.py", "import app.main\n\ndef test_run():\n    assert app.main.run() == 'running'\n")

    # Store symbols
    store.store_symbol(repo, sha, "app/main.py", "run", "function", 3, 4)
    store.store_symbol(repo, sha, "app/core.py", "get_config", "function", 1, 2)

    # Store imports
    store.store_import(repo, sha, "app/main.py", "app.core", "config")
    store.store_import(repo, sha, "tests/test_main.py", "app.main")

    # Store policy fact
    store.store_policy_fact(repo, sha, "license", "MIT", "LICENSE", "1-5", "MIT License")

    # Store issue fact
    store.store_issue_fact(repo, 42, "open", False, [], False, None, "2026-10-18T10:00:00Z")

    # Store real verification run
    store.store_verification_run(
        run_id="real_docker_run_1",
        repo_id=repo,
        commit_sha=sha,
        driver="docker_isolated",
        status="EXECUTED_PASS",
        exit_code=0,
        output_hash="hash12345",
        passed_tests=5,
        failed_tests=0,
        timestamp="2026-10-18T10:05:00Z",
    )

    kernel = CheckerKernel(store)
    return store, kernel, repo, sha


def test_path_normalization_security():
    # Valid paths
    assert normalize_repo_path("src/utils.py") == "src/utils.py"
    assert normalize_repo_path("./src/utils.py") == "src/utils.py"
    assert normalize_repo_path("src\\utils.py") == "src/utils.py"

    # Malicious or invalid paths must raise ValueError
    with pytest.raises(ValueError, match="forbidden"):
        normalize_repo_path("/etc/passwd")

    with pytest.raises(ValueError, match="forbidden"):
        normalize_repo_path("C:\\Windows\\System32")

    with pytest.raises(ValueError, match="traversal"):
        normalize_repo_path("src/../../secret.txt")

    with pytest.raises(ValueError, match="Null byte"):
        normalize_repo_path("src/evil.py\0.txt")


def test_file_exists_checker(trust_env):
    _, kernel, repo, sha = trust_env

    # Valid file
    c1 = Claim(
        claim_type=ClaimType.FILE_EXISTS,
        arguments={"path": "app/main.py"},
        repository=repo,
        snapshot_sha=sha,
    )
    v1 = kernel.verify_claim(c1, sha)
    assert v1.status == VerdictStatus.VERIFIED
    assert v1.witness["path"] == "app/main.py"

    # Missing file
    c2 = Claim(
        claim_type=ClaimType.FILE_EXISTS,
        arguments={"path": "app/nonexistent.py"},
        repository=repo,
        snapshot_sha=sha,
    )
    v2 = kernel.verify_claim(c2, sha)
    assert v2.status == VerdictStatus.REFUTED
    assert v2.reason_code == "FILE_NOT_FOUND"

    # Path traversal attempt
    c3 = Claim(
        claim_type=ClaimType.FILE_EXISTS,
        arguments={"path": "../../../etc/passwd"},
        repository=repo,
        snapshot_sha=sha,
    )
    v3 = kernel.verify_claim(c3, sha)
    assert v3.status == VerdictStatus.REFUTED
    assert v3.reason_code == "UNSAFE_PATH"


def test_stale_sha_rejection(trust_env):
    _, kernel, repo, sha = trust_env

    # Claim with a different SHA
    stale_sha = "9999999999999999999999999999999999999999"
    c = Claim(
        claim_type=ClaimType.FILE_EXISTS,
        arguments={"path": "app/main.py"},
        repository=repo,
        snapshot_sha=stale_sha,
    )
    v = kernel.verify_claim(c, sha)
    assert v.status == VerdictStatus.STALE
    assert v.reason_code == "SHA_MISMATCH"


def test_symbol_in_file_checker(trust_env):
    _, kernel, repo, sha = trust_env

    # Valid symbol
    c1 = Claim(
        claim_type=ClaimType.SYMBOL_IN_FILE,
        arguments={"path": "app/main.py", "symbol_name": "run"},
        repository=repo,
        snapshot_sha=sha,
    )
    v1 = kernel.verify_claim(c1, sha)
    assert v1.status == VerdictStatus.VERIFIED
    assert v1.witness["symbol_name"] == "run"
    assert v1.witness["start_line"] == 3

    # Missing symbol in existing file
    c2 = Claim(
        claim_type=ClaimType.SYMBOL_IN_FILE,
        arguments={"path": "app/main.py", "symbol_name": "missing_func"},
        repository=repo,
        snapshot_sha=sha,
    )
    v2 = kernel.verify_claim(c2, sha)
    assert v2.status == VerdictStatus.REFUTED
    assert v2.reason_code == "SYMBOL_NOT_FOUND"


def test_lines_contain_checker(trust_env):
    _, kernel, repo, sha = trust_env

    # Valid line content
    c1 = Claim(
        claim_type=ClaimType.LINES_CONTAIN,
        arguments={"path": "app/main.py", "substring": "def run():", "start_line": 2, "end_line": 4},
        repository=repo,
        snapshot_sha=sha,
    )
    v1 = kernel.verify_claim(c1, sha)
    assert v1.status == VerdictStatus.VERIFIED

    # Mismatched line content
    c2 = Claim(
        claim_type=ClaimType.LINES_CONTAIN,
        arguments={"path": "app/main.py", "substring": "def non_existent_code():"},
        repository=repo,
        snapshot_sha=sha,
    )
    v2 = kernel.verify_claim(c2, sha)
    assert v2.status == VerdictStatus.REFUTED
    assert v2.reason_code == "LINES_MISMATCH"


def test_import_and_test_checkers(trust_env):
    _, kernel, repo, sha = trust_env

    # Valid imported_by
    c1 = Claim(
        claim_type=ClaimType.IMPORTED_BY,
        arguments={"source_path": "app/main.py", "imported_module": "app.core"},
        repository=repo,
        snapshot_sha=sha,
    )
    assert kernel.verify_claim(c1, sha).status == VerdictStatus.VERIFIED

    # Valid test_imports
    c2 = Claim(
        claim_type=ClaimType.TEST_IMPORTS,
        arguments={"test_path": "tests/test_main.py", "target_module": "app.main"},
        repository=repo,
        snapshot_sha=sha,
    )
    assert kernel.verify_claim(c2, sha).status == VerdictStatus.VERIFIED


def test_verify_result_security(trust_env):
    _, kernel, repo, sha = trust_env

    # Real docker execution pass verified
    c_real = Claim(
        claim_type=ClaimType.VERIFY_RESULT,
        arguments={"run_id": "real_docker_run_1", "status": "EXECUTED_PASS"},
        repository=repo,
        snapshot_sha=sha,
    )
    v_real = kernel.verify_claim(c_real, sha)
    assert v_real.status == VerdictStatus.VERIFIED
    assert v_real.reason_code == "EXECUTED_PASS_VERIFIED"

    # Non-existent run
    c_none = Claim(
        claim_type=ClaimType.VERIFY_RESULT,
        arguments={"run_id": "ghost_run_404", "status": "EXECUTED_PASS"},
        repository=repo,
        snapshot_sha=sha,
    )
    v_none = kernel.verify_claim(c_none, sha)
    assert v_none.status == VerdictStatus.UNKNOWN
    assert v_none.reason_code == "RUN_NOT_FOUND"


def test_trusted_renderer_separates_prose(trust_env):
    _, kernel, repo, sha = trust_env
    renderer = TrustedRenderer()

    c_valid = Claim(
        claim_type=ClaimType.FILE_EXISTS,
        arguments={"path": "app/main.py"},
        repository=repo,
        snapshot_sha=sha,
    )
    c_fake = Claim(
        claim_type=ClaimType.FILE_EXISTS,
        arguments={"path": "hallucinated.py"},
        repository=repo,
        snapshot_sha=sha,
    )
    verdicts = kernel.evaluate_claims([c_valid, c_fake], repo, sha)

    rendered = renderer.render_plan(
        repository=repo,
        snapshot_sha=sha,
        claims=[c_valid, c_fake],
        verdicts=verdicts,
        raw_model_explanation="The model thinks hallucinated.py solves all issues magically.",
    )

    assert len(rendered.verified_steps) == 1
    assert "app/main.py" in rendered.verified_steps[0].grounded_statement
    assert len(rendered.rejected_claims_diagnostic) == 1
    assert rendered.rejected_claims_diagnostic[0]["arguments"]["path"] == "hallucinated.py"
    assert "Unverified Model Explanation" in rendered.summary_markdown
    assert "hallucinated.py solves all issues" in rendered.summary_markdown
    # Ensure refuted item is NOT in verified steps
    for s in rendered.verified_steps:
        assert "hallucinated.py" not in s.grounded_statement
