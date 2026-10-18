"""Tests for Receipt Hash Chains, Understanding Gate, and PR Packaging."""

import pytest
from app.services.trust.receipt import (
    ContributionReceiptRecorder,
    verify_receipt_chain,
)
from app.services.understanding_gate.service import UnderstandingGateService
from app.services.trust.claims import Claim, ClaimType, Verdict, VerdictStatus
from app.services.trust.pr_pack import PRPackageGenerator
from app.services.policy_radar.service import AIPolicyStatus, PolicyRadarReport, WelcomenessRating


def test_receipt_hash_chain_validity():
    recorder = ContributionReceiptRecorder("org/repo", "sha12345")
    e0 = recorder.record_event(
        step_name="genesis",
        result_code="INIT",
    )
    e1 = recorder.record_event(
        step_name="policy_check",
        result_code="POLICY_VERIFIED",
        evidence_ids=["ev_1", "ev_2"],
    )
    e2 = recorder.record_event(
        step_name="verify",
        result_code="EXECUTED_PASS",
        verification_driver="docker_isolated",
        verification_status="EXECUTED_PASS",
    )

    events = recorder.export_chain()
    report = verify_receipt_chain(events)
    assert report.is_valid is True
    assert report.verified_event_count == 3
    assert report.first_invalid_index is None
    assert report.final_hash == e2.event_hash


def test_receipt_tampered_hash_detection():
    recorder = ContributionReceiptRecorder("org/repo", "sha12345")
    recorder.record_event("step0", "OK")
    recorder.record_event("step1", "OK")

    events = recorder.export_chain()
    # Corrupt hash of first event
    events[0]["event_hash"] = "deadbeef" * 8
    report = verify_receipt_chain(events)
    assert report.is_valid is False
    assert report.first_invalid_index == 0


def test_receipt_broken_prev_hash_detection():
    recorder = ContributionReceiptRecorder("org/repo", "sha12345")
    recorder.record_event("step0", "OK")
    recorder.record_event("step1", "OK")

    events = recorder.export_chain()
    # Break prev_hash of second event
    events[1]["prev_hash"] = "c0ffee" * 10
    report = verify_receipt_chain(events)
    assert report.is_valid is False
    assert report.first_invalid_index == 1


def test_understanding_gate_questions_and_grounding():
    gate = UnderstandingGateService()
    c = Claim(
        claim_type=ClaimType.SYMBOL_IN_FILE,
        arguments={"path": "src/auth.py", "symbol_name": "verify_token"},
        repository="org/repo",
        snapshot_sha="sha1",
    )
    v = Verdict(
        claim_id=c.claim_id,
        status=VerdictStatus.VERIFIED,
        snapshot_sha="sha1",
        reason_code="SYMBOL_FOUND",
        explanation="Symbol verified",
        witness={"path": "src/auth.py", "symbol_name": "verify_token", "start_line": 10, "end_line": 20},
    )

    # Question generation
    questions = gate.generate_questions([c], [v])
    assert len(questions) == 1
    assert "verify_token" in questions[0].prompt

    # Grounded answer evaluation
    answers_grounded = {
        questions[0].question_id: "We need to update verify_token in auth.py to handle expired timestamps correctly."
    }
    receipt_grounded = gate.evaluate_answers("org/repo", "sha1", questions, answers_grounded)
    assert receipt_grounded.grounded_count == 1
    assert receipt_grounded.evaluations[0].grounded is True

    # Ungrounded answer evaluation
    answers_ungrounded = {
        questions[0].question_id: "I just changed some random stuff to make tests pass."
    }
    receipt_ungrounded = gate.evaluate_answers("org/repo", "sha1", questions, answers_ungrounded)
    assert receipt_ungrounded.grounded_count == 0
    assert receipt_ungrounded.evaluations[0].grounded is False


def test_pr_pack_learn_mode_on_ai_ban():
    generator = PRPackageGenerator()
    policy = PolicyRadarReport(
        repository="org/banned",
        ai_policy=AIPolicyStatus.BANNED,
        welcomeness=WelcomenessRating.RED,
        collection_timestamp="2026-10-18T10:00:00Z",
        contributor_guidance="Banned",
        learn_mode_recommended=True,
    )

    pack = generator.generate_package(
        repository="org/banned",
        snapshot_sha="sha12345",
        issue_number=55,
        issue_title="Update database index",
        policy_report=policy,
        rendered_plan=None,
        verification_record=None,
        understanding_receipt=None,
        receipt_events=None,
    )

    assert pack.is_learn_mode_only is True
    assert "Self-Authoring Guide" in pack.title
    assert "Self-Authoring Checklist" in pack.body_markdown
