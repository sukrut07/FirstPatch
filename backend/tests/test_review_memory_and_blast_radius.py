"""Tests for Review Memory, Blast Radius, Abstention, and Kernel Mutation Fuzzing."""

import pytest
from app.services.trust.review_memory import ReviewMemoryService
from app.services.trust.blast_radius import BlastRadiusAnalyzer
from app.services.trust.abstain import (
    AbstentionEngine,
    CandidateRecommendation,
)
from app.services.trust.claims import Claim, ClaimType
from app.services.trust.fact_store import FactStore
from app.services.trust.kernel import CheckerKernel
from app.services.trust.fuzz import KernelMutationFuzzer


def test_review_memory_theme_extraction():
    service = ReviewMemoryService(min_evidence_threshold=2)
    comments = [
        {"body": "Please add unit tests for this case.", "path": "src/calc.py", "pr_number": 10},
        {"body": "Missing unit tests covering zero division.", "path": "src/calc.py", "pr_number": 12},
        {"body": "Can you add type hints to this function?", "path": "src/calc.py", "pr_number": 14},
    ]

    results = service.analyze_comments("org/repo", comments)
    theme_by_key = {r.theme: r for r in results}

    assert "tests_requested" in theme_by_key
    tests_res = theme_by_key["tests_requested"]
    assert tests_res.frequency == 2
    assert tests_res.is_supported is True  # >= 2

    type_res = theme_by_key["type_annotations"]
    assert type_res.frequency == 1
    assert type_res.is_supported is False  # < 2


def test_blast_radius_ast_analysis():
    analyzer = BlastRadiusAnalyzer()
    files = {
        "src/auth.py": "def login():\n    return True\n",
        "src/api.py": "from src.auth import login\n\ndef route():\n    return login()\n",
        "tests/test_api.py": "import src.api\n\ndef test_route():\n    assert src.api.route() is True\n",
    }

    report = analyzer.analyze_impact("src/auth.py", files, target_symbol="login")
    assert report.affected_files_count >= 1
    assert "src/api.py" in report.direct_importers
    assert report.parser_tier == "python_ast_high_confidence"


def test_abstention_engine_decisions():
    engine = AbstentionEngine(min_score_threshold=0.3, min_margin_threshold=0.1)

    # Low score candidate triggers abstention
    cand_low = [
        CandidateRecommendation(file_path="src/a.py", retrieval_score=0.15, has_verified_evidence=False)
    ]
    dec_low = engine.evaluate_recommendations(cand_low)
    assert dec_low.should_abstain is True
    assert "below threshold" in dec_low.reason

    # Ambiguous candidates without verified evidence trigger abstention
    cand_ambiguous = [
        CandidateRecommendation(file_path="src/a.py", retrieval_score=0.70, has_verified_evidence=False),
        CandidateRecommendation(file_path="src/b.py", retrieval_score=0.68, has_verified_evidence=False),
    ]
    dec_amb = engine.evaluate_recommendations(cand_ambiguous)
    assert dec_amb.should_abstain is True
    assert "ambiguous" in dec_amb.reason

    # High score with verified evidence succeeds
    cand_good = [
        CandidateRecommendation(file_path="src/a.py", retrieval_score=0.85, has_verified_evidence=True),
        CandidateRecommendation(file_path="src/b.py", retrieval_score=0.40, has_verified_evidence=False),
    ]
    dec_good = engine.evaluate_recommendations(cand_good)
    assert dec_good.should_abstain is False
    assert dec_good.selected_candidate.file_path == "src/a.py"


def test_kernel_mutation_fuzzing():
    store = FactStore(":memory:")
    repo = "fuzz-org/repo"
    sha = "f000ba7111222333444555666777888999000aaa"

    store.store_file(repo, sha, "src/calculator.py", "def add(a, b):\n    return a + b\n")
    store.store_symbol(repo, sha, "src/calculator.py", "add", "function", 1, 2)

    kernel = CheckerKernel(store)
    fuzzer = KernelMutationFuzzer(kernel)

    valid_claim = Claim(
        claim_type=ClaimType.SYMBOL_IN_FILE,
        arguments={"path": "src/calculator.py", "symbol_name": "add"},
        repository=repo,
        snapshot_sha=sha,
    )

    report = fuzzer.run_mutation_suite([valid_claim], repo, sha)
    assert report.total_valid_claims_tested == 1
    assert report.false_rejections == 0
    assert report.false_reject_rate == 0.0
    assert report.mutations_detected > 0
    assert report.mutations_escaped == 0
    assert report.catch_rate == 1.0
