import pytest
import os
from backend.app.services.github_service import parse_repo_identifier
from backend.app.services.ast_service import analyze_python_source, analyze_generic_source
from backend.app.services.chunking_service import chunk_file_content
from backend.app.services.issue_service import issue_service
from backend.app.services.setup_doctor_service import setup_doctor
from backend.app.services.verification_service import verification_service
from backend.app.services.flight_recorder_service import flight_recorder
from backend.app.services.review_simulator_service import review_simulator
from backend.app.database import init_db, get_db

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

def test_parse_repo_identifier():
    assert parse_repo_identifier("https://github.com/pallets/flask") == ("pallets", "flask")
    assert parse_repo_identifier("pallets/flask") == ("pallets", "flask")
    assert parse_repo_identifier("git@github.com:octocat/Hello-World.git") == ("octocat", "Hello-World")
    with pytest.raises(ValueError):
        parse_repo_identifier("invalid-string-without-slash")

def test_python_ast_extractor():
    sample_code = """
import os
from sys import argv

class MathEngine:
    '''Calculates basic math.'''
    def add(self, a, b):
        return a + b

def test_addition():
    engine = MathEngine()
    assert engine.add(2, 3) == 5
"""
    result = analyze_python_source(sample_code)
    assert result["success"] is True
    assert len(result["classes"]) == 1
    assert result["classes"][0]["name"] == "MathEngine"
    assert len(result["classes"][0]["methods"]) == 1
    assert len(result["functions"]) == 1
    assert result["functions"][0]["name"] == "test_addition"
    assert len(result["test_functions"]) == 1
    assert "os" in result["imports"]

def test_chunking_service():
    sample_code = """
class Calculator:
    def add(self, x, y):
        return x + y

def test_calc():
    assert True
"""
    chunks = chunk_file_content("calc.py", sample_code, "test/repo", "sha123")
    assert len(chunks) >= 2
    types = [c["chunk_type"] for c in chunks]
    assert "class" in types
    assert "test" in types
    for c in chunks:
        assert c["start_line"] >= 1
        assert c["end_line"] >= c["start_line"]
        assert len(c["content_hash"]) == 64

def test_issue_intelligence_service():
    issue = {
        "title": "Fix unhandled KeyError in config",
        "body": "When key is missing, raises KeyError. Steps to reproduce:\n1. Unset key\n2. Run pytest",
        "labels": ["good first issue", "bug"],
        "comments_count": 2
    }
    eval_res = issue_service.evaluate_issue(issue, user_skill_level="Beginner")
    assert eval_res["fit_score"] >= 70.0
    assert eval_res["estimated_complexity"] == "Beginner"
    assert any("good first issue" in r.lower() for r in eval_res["reasons"])

def test_setup_failure_doctor():
    error_trace = "ModuleNotFoundError: No module named 'pydantic'"
    diagnosis = setup_doctor.diagnose_error(error_trace)
    assert diagnosis["category"] == "Missing Python Package"
    assert len(diagnosis["remediation_plan"]) >= 1
    assert "pip install pydantic" in diagnosis["remediation_plan"][0]["command"]

def test_verification_safe_command():
    res = verification_service.run_safe_command("echo 'hello firstpatch'")
    assert res["status"] == "PASSED"
    assert res["exit_code"] == 0
    assert "hello firstpatch" in res["stdout"]

def test_verification_blocks_dangerous_tokens():
    res = verification_service.run_safe_command("rm -rf /")
    assert res["status"] == "BLOCKED"
    assert res["exit_code"] == -1

def test_pr_review_simulator():
    diff_text = """
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
+print('debugging credentials')
+dummy_token = "fake_test_dummy_token_12345"
"""
    review = review_simulator.analyze_diff(diff_text)
    assert review["findings_count"] >= 2
    severities = [f["severity"] for f in review["findings"]]
    assert "critical" in severities
    assert "warning" in severities

def test_flight_recorder_and_pr_draft():
    ws_id = "test-ws-1"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO repositories (id, owner, name, created_at)
        VALUES ('octocat/Hello-World', 'octocat', 'Hello-World', datetime('now'))
        """)
        cursor.execute("""
        INSERT OR REPLACE INTO contribution_workspaces (
            id, repository_id, title, description, status, definition_of_done,
            draft_pr_title, created_at, updated_at
        ) VALUES (?, 'octocat/Hello-World', 'Fix config error', 'Fixes KeyError', 'active', 'Done', 'fix: config', datetime('now'), datetime('now'))
        """, (ws_id,))
        cursor.execute("""
        INSERT INTO contribution_steps (id, workspace_id, step_index, title, description, status, created_at)
        VALUES ('step1', ?, 1, 'Inspect file', 'Checked lines', 'completed', datetime('now'))
        """, (ws_id,))

    flight_recorder.log_event(
        workspace_id=ws_id,
        repository_id="octocat/Hello-World",
        event_type="UNDERSTAND",
        summary="Inspected configuration file."
    )
    draft = flight_recorder.generate_pr_draft(ws_id)
    assert draft["title"] == "fix: config"
    assert "Pull Request: fix: config" in draft["markdown"]
    assert "Maintainer Review Checklist" in draft["markdown"]

@pytest.mark.asyncio
async def test_benchmark_service(monkeypatch):
    from backend.app.services.benchmark_service import benchmark_service, BENCHMARK_SUITE
    from backend.app.services.ollama_service import ollama_service

    async def mock_generate(prompt, model=None, temperature=0.1, format_json=False):
        if format_json:
            return {
                "response": '{"root_cause": "KeyError", "files_to_modify": ["src/flask/config.py"], "learning_gap": "Exceptions", "recommended_test": "pytest tests/test_config.py"}',
                "eval_count": 45,
                "total_duration": 500000000
            }
        if "PROPOSED DIFF" in prompt:
            return {
                "response": "Found hardcoded auth credential and sensitive secret along with debug print statement.",
                "eval_count": 30,
                "total_duration": 300000000
            }
        return {
            "response": "validate_session_token accepts token and max_age_seconds (default 3600), raising InvalidTokenError on line 15-32.",
            "eval_count": 35,
            "total_duration": 400000000
        }

    monkeypatch.setattr(ollama_service, "generate_response", mock_generate)
    report = await benchmark_service.run_model_benchmark("gemma4:e2b")

    assert report["model"] == "gemma4:e2b"
    assert report["tests_run"] == len(BENCHMARK_SUITE)
    assert report["tests_passed"] == len(BENCHMARK_SUITE)
    assert report["pass_rate_percent"] == 100.0
    assert report["average_tokens_per_sec"] > 0

def test_claim_safety_and_stacktrace():
    # 1. Test claim safety
    open_issue = {
        "title": "Fix doc typo",
        "body": "There is a small typo in the README.md documentation file that needs fixing.",
        "labels": ["documentation"]
    }
    safety1 = issue_service.check_claim_safety(open_issue)
    assert safety1["is_safe_to_claim"] is True
    assert safety1["status"] == "ACTIONABLE_SIGNAL_FOUND"

    assigned_issue = {"title": "Fix bug", "body": "Crashing", "assignee": "sukrut07"}
    safety2 = issue_service.check_claim_safety(assigned_issue)
    assert safety2["is_safe_to_claim"] is False
    assert safety2["status"] == "POSSIBLY_CLAIMED"

    # 2. Test stacktrace extractor
    trace_text = """
    Traceback (most recent call last):
      File "src/flask/config.py", line 42, in from_prefixed_env
        val = os.environ[key]
    KeyError: 'SECRET_KEY'
    """
    coords = issue_service.extract_stacktrace_coordinates(trace_text)
    assert len(coords) == 1
    assert coords[0]["file_path"] == "src/flask/config.py"
    assert coords[0]["target_line"] == 42
    assert coords[0]["match_type"] == "STACKTRACE"

def test_documentation_generator():
    from backend.app.services.documentation_service import documentation_service
    repo_id = "octocat/Hello-World"
    doc_res = documentation_service.generate_all_documentation(repo_id)
    assert doc_res["repository_id"] == repo_id
    assert os.path.exists(doc_res["documents"]["project_overview"])
    assert os.path.exists(doc_res["documents"]["architecture"])
    assert os.path.exists(doc_res["documents"]["beginner_setup"])
    assert os.path.exists(doc_res["documents"]["contribution_guide"])


