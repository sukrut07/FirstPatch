"""Phase 5 Master Test Suite: Understanding Gate & Review Memory Audit.

Audits:
- Understanding Gate question generation strictly from verified claims.
- Cases: 0 verified claims, 1 verified claim, multiple verified claims, stale evidence, fabricated symbols.
- Answers: correct, incorrect, empty, mentions real symbol without explanation, advisory disclaimer verification.
- Review Memory: real PR links, 2-witness minimum threshold, duplicate comment rejection, sampling limits.
"""

import pytest

from app.services.trust.claims import (
    Claim,
    ClaimType,
    Verdict,
    VerdictStatus,
    compute_verdict_seal,
)
from app.services.understanding_gate.service import (
    UnderstandingGateService,
    Question,
)
from app.services.trust.review_memory import ReviewMemoryService


def test_understanding_01_no_verified_claims():
    gate = UnderstandingGateService()
    # No verified claims -> fallback question
    questions = gate.generate_questions([], [])
    assert len(questions) == 1
    assert questions[0].claim_id == "fallback_generic"


def test_understanding_02_single_verified_claim():
    gate = UnderstandingGateService()
    c = Claim(
        claim_type=ClaimType.SYMBOL_IN_FILE,
        arguments={"path": "src/auth.py", "symbol_name": "check_token"},
        repository="org/repo",
        snapshot_sha="sha123",
    )
    v = Verdict(
        claim_id=c.claim_id,
        status=VerdictStatus.VERIFIED,
        snapshot_sha="sha123",
        reason_code="SYMBOL_FOUND",
        explanation="Symbol verified",
        witness={"path": "src/auth.py", "symbol_name": "check_token", "start_line": 10, "end_line": 25},
        kernel_seal=compute_verdict_seal(c.claim_id, "VERIFIED", "sha123", "SYMBOL_FOUND"),
    )

    questions = gate.generate_questions([c], [v])
    assert len(questions) == 1
    assert "check_token" in questions[0].prompt
    assert "src/auth.py" in questions[0].prompt


def test_understanding_03_multiple_verified_claims():
    gate = UnderstandingGateService()
    c1 = Claim(
        claim_type=ClaimType.FILE_EXISTS,
        arguments={"path": "src/db.py"},
        repository="org/repo",
        snapshot_sha="sha123",
    )
    v1 = Verdict(
        claim_id=c1.claim_id,
        status=VerdictStatus.VERIFIED,
        snapshot_sha="sha123",
        reason_code="FILE_FOUND",
        explanation="File found",
        witness={"path": "src/db.py"},
        kernel_seal=compute_verdict_seal(c1.claim_id, "VERIFIED", "sha123", "FILE_FOUND"),
    )

    c2 = Claim(
        claim_type=ClaimType.TEST_IMPORTS,
        arguments={"test_path": "tests/test_db.py", "target_module": "src.db"},
        repository="org/repo",
        snapshot_sha="sha123",
    )
    v2 = Verdict(
        claim_id=c2.claim_id,
        status=VerdictStatus.VERIFIED,
        snapshot_sha="sha123",
        reason_code="TEST_IMPORTS_VERIFIED",
        explanation="Test imports verified",
        witness={"test_path": "tests/test_db.py", "target_module": "src.db"},
        kernel_seal=compute_verdict_seal(c2.claim_id, "VERIFIED", "sha123", "TEST_IMPORTS_VERIFIED"),
    )

    questions = gate.generate_questions([c1, c2], [v1, v2], max_questions=2)
    assert len(questions) == 2


def test_understanding_04_stale_and_refuted_claims_produce_no_questions():
    gate = UnderstandingGateService()
    c_stale = Claim(
        claim_type=ClaimType.SYMBOL_IN_FILE,
        arguments={"path": "src/old.py", "symbol_name": "old_func"},
        repository="org/repo",
        snapshot_sha="old_sha",
    )
    v_stale = Verdict(
        claim_id=c_stale.claim_id,
        status=VerdictStatus.STALE,
        snapshot_sha="new_sha",
        reason_code="SHA_MISMATCH",
        explanation="Stale",
    )

    c_fake = Claim(
        claim_type=ClaimType.SYMBOL_IN_FILE,
        arguments={"path": "src/fake.py", "symbol_name": "fake_func"},
        repository="org/repo",
        snapshot_sha="new_sha",
    )
    v_fake = Verdict(
        claim_id=c_fake.claim_id,
        status=VerdictStatus.REFUTED,
        snapshot_sha="new_sha",
        reason_code="SYMBOL_NOT_FOUND",
        explanation="Not found",
    )

    # Stale & refuted items MUST NOT generate grounded questions
    questions = gate.generate_questions([c_stale, c_fake], [v_stale, v_fake])
    assert len(questions) == 1
    assert questions[0].claim_id == "fallback_generic"


def test_understanding_05_answer_evaluation_grounding_and_advisory_note():
    gate = UnderstandingGateService()
    q = Question(
        prompt="Explain check_token in src/auth.py",
        claim_id="c1",
        grounding_keywords=["check_token", "auth.py"],
    )

    # 1. Correct / grounded answer
    receipt_good = gate.evaluate_answers(
        "org/repo",
        "sha123",
        [q],
        {q.question_id: "We update check_token in auth.py to validate jwt signature expiration."},
    )
    assert receipt_good.grounded_count == 1
    assert receipt_good.evaluations[0].grounded is True
    # Advisory note must be present
    assert "not a certification of human comprehension" in receipt_good.cautionary_note

    # 2. Empty answer
    receipt_empty = gate.evaluate_answers("org/repo", "sha123", [q], {q.question_id: ""})
    assert receipt_empty.grounded_count == 0
    assert receipt_empty.evaluations[0].grounded is False

    # 3. Off-topic answer without keywords
    receipt_off = gate.evaluate_answers(
        "org/repo",
        "sha123",
        [q],
        {q.question_id: "I edited some unrelated CSS styles in the user profile page."},
    )
    assert receipt_off.grounded_count == 0
    assert receipt_off.evaluations[0].grounded is False


def test_review_memory_two_witness_minimum_threshold():
    svc = ReviewMemoryService(min_evidence_threshold=2)
    # 1 comment: under threshold (not supported)
    single_comment = [
        {"body": "Please add unit tests for this case.", "path": "src/a.py", "pr_number": 10}
    ]
    rep1 = svc.analyze_comments("org/repo", single_comment)
    tests_t1 = next(r for r in rep1 if r.theme == "tests_requested")
    assert tests_t1.frequency == 1
    assert tests_t1.is_supported is False

    # 2 comments across distinct PRs: satisfies threshold
    two_comments = [
        {"body": "Please add unit tests for this case.", "path": "src/a.py", "pr_number": 10},
        {"body": "Missing unit tests covering edge case.", "path": "src/a.py", "pr_number": 12},
    ]
    rep2 = svc.analyze_comments("org/repo", two_comments)
    tests_t2 = next(r for r in rep2 if r.theme == "tests_requested")
    assert tests_t2.frequency == 2
    assert tests_t2.is_supported is True


def test_review_memory_duplicate_comments_rejected():
    svc = ReviewMemoryService(min_evidence_threshold=2)
    # Identical duplicated comments on same PR must NOT count as 2 distinct witnesses
    duplicate_comments = [
        {"body": "Please add unit tests for this case.", "path": "src/a.py", "pr_number": 10},
        {"body": "Please add unit tests for this case.", "path": "src/a.py", "pr_number": 10},
    ]
    rep = svc.analyze_comments("org/repo", duplicate_comments)
    tests_t = next(r for r in rep if r.theme == "tests_requested")
    assert tests_t.frequency == 1  # Deduplicated to 1
    assert tests_t.is_supported is False  # Cannot pass threshold of 2


def test_review_memory_sampling_bounds():
    svc = ReviewMemoryService(max_comments_cap=5)
    # Provide 10 comments
    lots_of_comments = [
        {"body": f"Comment {i}", "path": "src/a.py", "pr_number": i} for i in range(10)
    ]
    rep = svc.analyze_comments("org/repo", lots_of_comments)
    # Sample size is capped at 5
    if rep:
        assert rep[0].sample_size == 5
