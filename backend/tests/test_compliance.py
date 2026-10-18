import pytest
from backend.app.services.ast_service import analyze_python_source
from backend.app.services.issue_service import issue_service
from backend.app.services.setup_doctor_service import setup_doctor
from backend.app.services.verification_service import verification_service
from backend.app.services.review_simulator_service import review_simulator
from backend.app.services.flight_recorder_service import flight_recorder
from backend.app.services.documentation_service import documentation_service
from backend.app.database import init_db, get_db

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

# Problem 1: Difficulty Understanding Large Codebases
def test_p1_codebase_understanding_ast_and_docs():
    sample_code = """
class CoreService:
    '''Core orchestration logic.'''
    def execute_task(self, task_id: str):
        return f"Executing {task_id}"

def test_execute():
    assert True
"""
    ast = analyze_python_source(sample_code)
    assert ast["success"] is True
    assert len(ast["classes"]) == 1
    assert ast["classes"][0]["name"] == "CoreService"

    docs = documentation_service.generate_all_documentation("octocat/Hello-World")
    assert docs["repository_id"] == "octocat/Hello-World"
    assert "project_overview" in docs["documents"]

# Problem 2: Finding Suitable Open-Source Issues
def test_p2_suitable_issue_discovery_multidimensional():
    issue = {
        "title": "Fix unhandled KeyError in config",
        "body": "When API_TIMEOUT is missing, raises KeyError instead of default.",
        "labels": ["good first issue", "bug"],
        "comments_count": 1
    }
    eval_res = issue_service.evaluate_issue(issue, user_skill_level="Beginner", user_interests=["web"])
    assert eval_res["technical_fit_score"] >= 60.0
    assert eval_res["interest_fit_score"] >= 60.0
    assert eval_res["why_this_project"] is not None
    assert eval_res["why_this_issue"] is not None

# Problem 3: Difficulty Connecting Issues to Source Code
def test_p3_issue_to_code_mapping_and_stacktraces():
    trace = 'File "src/flask/config.py", line 42, in from_prefixed_env\nKeyError: "PORT"'
    coords = issue_service.extract_stacktrace_coordinates(trace)
    assert len(coords) == 1
    assert coords[0]["file_path"] == "src/flask/config.py"
    assert coords[0]["target_line"] == 42
    assert coords[0]["match_type"] == "STACKTRACE"

# Problem 4: Lack of Confidence and Impostor Syndrome
def test_p4_confidence_and_beginner_onboarding():
    # Verify claim safety advisory protects beginner from claiming assigned issues
    assigned_issue = {"title": "Fix bug", "body": "Need fix", "assignee": "maintainer1"}
    safety = issue_service.check_claim_safety(assigned_issue)
    assert safety["is_safe_to_claim"] is False
    assert safety["status"] == "POSSIBLY_CLAIMED"

# Problem 5: Development Environment and Setup Issues
def test_p5_setup_doctor_diagnostics():
    err = "ModuleNotFoundError: No module named 'fastapi'"
    diag = setup_doctor.diagnose_error(err)
    assert diag["category"] == "Missing Python Package"
    assert any("pip install fastapi" in step["command"] for step in diag["remediation_plan"])

# Problem 6: Overdependence on AI-Generated Code
def test_p6_triage_and_hypothesis_log_before_codegen():
    issue = {"number": 10, "title": "Crash on empty string"}
    triage_notes = {
        "user_summary": "Passing empty string crashes parser",
        "expected_behavior": "Return empty list",
        "actual_behavior": "IndexError: string index out of range",
        "reproduction_notes": "python -c 'import parser; parser.parse(\"\")'"
    }
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO repositories (id, owner, name, created_at) VALUES ('test/repo', 'test', 'repo', datetime('now'))")
        cursor.execute("INSERT OR REPLACE INTO issues (id, repository_id, number, title, created_at) VALUES ('test/repo:10', 'test/repo', 10, 'Crash', datetime('now'))")
        cursor.execute("""
        INSERT OR REPLACE INTO issue_triages (id, issue_id, user_summary, expected_behavior, actual_behavior, reproduction_notes, decision, created_at, updated_at)
        VALUES ('t_p6', 'test/repo:10', ?, ?, ?, ?, 'proceed', datetime('now'), datetime('now'))
        """, (triage_notes["user_summary"], triage_notes["expected_behavior"], triage_notes["actual_behavior"], triage_notes["reproduction_notes"]))
        
        cursor.execute("SELECT decision FROM issue_triages WHERE issue_id='test/repo:10'")
        row = cursor.fetchone()
        assert row["decision"] == "proceed"

# Problem 7: Unclear Contribution Policies
def test_p7_contribution_policy_and_guidelines():
    docs = documentation_service.generate_all_documentation("octocat/Hello-World")
    with open(docs["documents"]["contribution_guide"], "r", encoding="utf-8") as f:
        guide = f.read()
    assert "Branch & Git Conventions" in guide
    assert "Pull Request Checklist" in guide

# Problem 8: Lack of Reliable Verification (Proof-Carrying Contributions)
def test_p8_reliable_verification_reality_checker():
    # Pass check
    pass_res = verification_service.run_safe_command("python3 --version")
    assert pass_res["status"] == "PASSED"
    assert pass_res["exit_code"] == 0

    # Dangerous check blocked
    blocked_res = verification_service.run_safe_command("sudo rm -rf /")
    assert blocked_res["status"] == "BLOCKED"

# Problem 9: Difficulty Maintaining Motivation
def test_p9_flight_recorder_event_ledger():
    ws_id = "ws_motivation_1"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO repositories (id, owner, name, created_at) VALUES ('test/repo', 'test', 'repo', datetime('now'))")
        cursor.execute("""
        INSERT OR REPLACE INTO contribution_workspaces (id, repository_id, title, status, created_at, updated_at)
        VALUES (?, 'test/repo', 'Add feature', 'active', datetime('now'), datetime('now'))
        """, (ws_id,))

    flight_recorder.log_event(ws_id, "test/repo", "TRIAGE", "Completed 6-step contributor triage.")
    draft = flight_recorder.generate_pr_draft(ws_id)
    assert draft["title"] is not None
    assert draft["events_logged"] >= 1
    assert "Maintainer Review Checklist" in draft["markdown"]

# Problem 10: Maintainer Overload
def test_p10_maintainer_drafts_and_diff_review():
    issue = {"number": 15, "title": "Update timeout default"}
    drafts = issue_service.generate_maintainer_drafts(issue, None, "test/repo")
    assert len(drafts) == 4
    assert drafts[0]["draft_type"] == "ask_if_wanted"

    # Pre-review secret leak scanner
    diff_with_token = '+ GITHUB_TOKEN = "ghp_mockSecretTokenForTestingOnly1234"'
    review = review_simulator.analyze_diff(diff_with_token)
    assert review["findings_count"] >= 1
    assert any("secret" in f["title"].lower() or "critical" in f["severity"] for f in review["findings"])
