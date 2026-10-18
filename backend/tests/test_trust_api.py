"""FastAPI End-to-End API Integration Tests for Trust & Proof-Carrying Contributions."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_trust_api_store_and_evaluate():
    repo = "api-test-org/repo"
    sha = "aaaabbbbccccddddeeeeffff0000111122223333"

    # 1. Store facts
    store_resp = client.post(
        "/api/trust/facts/store",
        json={
            "repository": repo,
            "commit_sha": sha,
            "files": {"src/server.py": "def start_server():\n    return True\n"},
            "symbols": [
                {
                    "path": "src/server.py",
                    "symbol_name": "start_server",
                    "symbol_type": "function",
                    "start_line": 1,
                    "end_line": 2,
                }
            ],
            "policies": [{"policy_type": "license", "value": "Apache-2.0"}],
            "issues": [
                {
                    "issue_number": 99,
                    "state": "open",
                    "is_assigned": False,
                    "assignees": [],
                    "has_open_pr": False,
                }
            ],
        },
    )
    assert store_resp.status_code == 201

    # 2. Evaluate Claims via Kernel
    eval_resp = client.post(
        "/api/trust/evaluate",
        json={
            "repository": repo,
            "authoritative_sha": sha,
            "claims": [
                {
                    "claim_type": "FILE_EXISTS",
                    "arguments": {"path": "src/server.py"},
                    "repository": repo,
                    "snapshot_sha": sha,
                },
                {
                    "claim_type": "SYMBOL_IN_FILE",
                    "arguments": {"path": "src/server.py", "symbol_name": "start_server"},
                    "repository": repo,
                    "snapshot_sha": sha,
                },
                {
                    "claim_type": "FILE_EXISTS",
                    "arguments": {"path": "src/fabricated.py"},
                    "repository": repo,
                    "snapshot_sha": sha,
                },
            ],
            "raw_model_explanation": "Model suggests editing src/server.py and src/fabricated.py.",
        },
    )
    assert eval_resp.status_code == 200
    data = eval_resp.json()
    assert len(data["verdicts"]) == 3
    # Check verified vs refuted
    status_map = {v["reason_code"]: v["status"] for v in data["verdicts"]}
    assert status_map["FILE_FOUND"] == "VERIFIED"
    assert status_map["SYMBOL_FOUND"] == "VERIFIED"
    assert status_map["FILE_NOT_FOUND"] == "REFUTED"

    # Plan rendering check
    pkg = data["rendered_package"]
    assert len(pkg["verified_steps"]) == 2
    assert len(pkg["rejected_claims_diagnostic"]) == 1


def test_trust_api_policy_radar_and_claim_guard():
    # Policy radar endpoint
    radar_resp = client.post(
        "/api/trust/policy-radar",
        json={
            "repository": "org/test-repo",
            "files": {
                "CONTRIBUTING.md": "# Contribution Guide\nPlease state if AI was used in creating this pull request."
            },
        },
    )
    assert radar_resp.status_code == 200
    r_data = radar_resp.json()
    assert r_data["ai_policy"] == "disclosure_required"
    assert r_data["welcomeness"] == "green"

    # Claim guard endpoint
    guard_resp = client.post(
        "/api/trust/claim-guard",
        json={
            "repository": "org/test-repo",
            "issue_data": {"number": 12, "state": "open", "assignees": [{"login": "someone"}]},
        },
    )
    assert guard_resp.status_code == 200
    g_data = guard_resp.json()
    assert g_data["status"] == "already_assigned"


def test_trust_api_receipt_and_fuzz():
    # Test receipt verify
    rec_resp = client.post(
        "/api/trust/receipt/verify",
        json={
            "events": [
                {
                    "sequence_number": 0,
                    "step_name": "genesis",
                    "timestamp": "2026-10-18T10:00:00Z",
                    "repository": "org/repo",
                    "snapshot_sha": "sha1",
                    "evidence_ids": [],
                    "result_code": "INIT",
                    "prev_hash": "0" * 64,
                    "event_hash": "dummy_hash_will_fail",
                }
            ]
        },
    )
    assert rec_resp.status_code == 200
    assert rec_resp.json()["is_valid"] is False  # Tampered dummy hash detected


def test_trust_api_demo_fixture():
    resp = client.get("/api/trust/demo-fixture")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_synthetic"] is True
    assert "SYNTHETIC DEMO FIXTURE" in data["notice"]
    assert data["verified_claim_example"]["verdict"]["status"] == "VERIFIED"
    assert data["refuted_claim_example"]["verdict"]["status"] == "REFUTED"
    assert data["stale_claim_example"]["verdict"]["status"] == "STALE"
    assert data["unknown_claim_example"]["verdict"]["status"] == "UNKNOWN"
    assert data["prohibited_ai_policy_report"]["ai_policy"] == "banned"
    assert data["unavailable_verification_example"]["status"] == "UNAVAILABLE"
    assert data["valid_receipt_report"]["is_valid"] is True
    assert data["tampered_receipt_report"]["is_valid"] is False

