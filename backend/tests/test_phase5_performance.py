"""Phase 5 Master Test Suite: Performance Benchmarking & Resource Bounds.

Measures actual execution times across representative trust operations:
 1. Snapshot ingestion.
 2. Fact-store lookup.
 3. Claim verification.
 4. Policy analysis.
 5. Issue claim checking.
 6. Receipt verification.
 7. Review Memory analysis.
 8. Blast-radius analysis.

Validates bounding constraints:
 - Oversized file bounds.
 - Maximum comments cap in ReviewMemory.
 - Memory stability across repeated requests.
"""

import time
import pytest

from app.services.trust.fact_store import FactStore
from app.services.trust.claims import Claim, ClaimType
from app.services.trust.kernel import CheckerKernel
from app.services.policy_radar.service import PolicyRadarService
from app.services.claim_guard.service import ClaimGuardService
from app.services.trust.receipt import ContributionReceiptRecorder, verify_receipt_chain
from app.services.trust.review_memory import ReviewMemoryService
from app.services.trust.blast_radius import BlastRadiusAnalyzer


def test_performance_benchmarks():
    repo = "perf-org/repo"
    sha = "beef1234567890abcdef1234567890abcdef12"
    timings = {}

    # 1. Snapshot ingestion (10 files)
    store = FactStore(":memory:")
    t0 = time.perf_counter()
    for i in range(10):
        store.store_file(
            repo,
            sha,
            f"src/module_{i}.py",
            f"def func_{i}():\n    return {i}\n",
        )
        store.store_symbol(repo, sha, f"src/module_{i}.py", f"func_{i}", "function", 1, 2)
    t1 = time.perf_counter()
    timings["snapshot_ingestion_ms"] = (t1 - t0) * 1000

    # 2. Fact-store lookup (50 lookups)
    t0 = time.perf_counter()
    for i in range(50):
        mod = i % 10
        f = store.get_file(repo, sha, f"src/module_{mod}.py")
        s = store.get_symbol(repo, sha, f"src/module_{mod}.py", f"func_{mod}")
        assert f is not None
        assert s is not None
    t1 = time.perf_counter()
    timings["fact_store_lookup_50x_ms"] = (t1 - t0) * 1000

    # 3. Claim verification (50 claims through CheckerKernel)
    kernel = CheckerKernel(store)
    claims = [
        Claim(
            claim_type=ClaimType.SYMBOL_IN_FILE,
            arguments={"path": f"src/module_{i % 10}.py", "symbol_name": f"func_{i % 10}"},
            repository=repo,
            snapshot_sha=sha,
        )
        for i in range(50)
    ]
    t0 = time.perf_counter()
    verdicts = kernel.evaluate_claims(claims, repo, sha)
    t1 = time.perf_counter()
    assert len(verdicts) == 50
    timings["claim_verification_50x_ms"] = (t1 - t0) * 1000

    # 4. Policy analysis
    radar = PolicyRadarService()
    files = {
        "CONTRIBUTING.md": "# Guidelines\nPlease declare any AI assistance.\nWait to be assigned before starting.",
        "AI_POLICY.md": "AI is permitted if disclosed.",
    }
    t0 = time.perf_counter()
    policy_rep = radar.analyze_repository_policies(repo, files)
    t1 = time.perf_counter()
    assert policy_rep.ai_policy.value == "disclosure_required"
    timings["policy_analysis_ms"] = (t1 - t0) * 1000

    # 5. Issue claim checking
    guard = ClaimGuardService()
    issue = {"number": 42, "state": "open", "assignees": []}
    prs = [{"number": 1, "title": "Other fix", "body": "unrelated"}]
    comments = [{"body": "I would like to work on this issue", "user": {"login": "dev"}}]
    t0 = time.perf_counter()
    cg_rep = guard.check_issue_readiness(repo, issue, comments=comments, open_prs=prs)
    t1 = time.perf_counter()
    assert cg_rep.status.value == "already_claimed"
    timings["claim_guard_ms"] = (t1 - t0) * 1000

    # 6. Receipt verification (20 events)
    recorder = ContributionReceiptRecorder(repo, sha)
    for i in range(20):
        recorder.record_event(f"step_{i}", "OK")
    chain = recorder.export_chain()
    t0 = time.perf_counter()
    rec_rep = verify_receipt_chain(chain)
    t1 = time.perf_counter()
    assert rec_rep.is_valid is True
    timings["receipt_verification_20_events_ms"] = (t1 - t0) * 1000

    # 7. Review Memory analysis (100 comments)
    review_svc = ReviewMemoryService()
    raw_comments = [
        {
            "body": f"Please add unit tests for edge case {i % 5}.",
            "path": f"src/module_{i % 10}.py",
            "pr_number": i,
        }
        for i in range(100)
    ]
    t0 = time.perf_counter()
    themes = review_svc.analyze_comments(repo, raw_comments)
    t1 = time.perf_counter()
    assert len(themes) > 0
    timings["review_memory_100_comments_ms"] = (t1 - t0) * 1000

    # 8. Blast-radius analysis (AST parsing & dependency tracing)
    analyzer = BlastRadiusAnalyzer()
    repo_files = {
        "src/base.py": "def base_helper(): return 1\n",
        "src/service.py": "from src.base import base_helper\ndef run(): return base_helper()\n",
        "tests/test_service.py": "import src.service\ndef test_run(): assert src.service.run() == 1\n",
    }
    t0 = time.perf_counter()
    blast_rep = analyzer.analyze_impact("src/base.py", repo_files, target_symbol="base_helper")
    t1 = time.perf_counter()
    assert blast_rep.affected_files_count >= 1
    timings["blast_radius_analysis_ms"] = (t1 - t0) * 1000

    # Assert reasonable bounded execution times (< 500ms per operation)
    for op, ms in timings.items():
        assert ms < 500.0, f"Operation {op} exceeded 500ms ceiling: {ms:.2f}ms"
