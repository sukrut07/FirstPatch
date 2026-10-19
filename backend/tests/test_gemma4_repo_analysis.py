import pytest
import httpx
import respx
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.cloud_llm_service import cloud_llm_service

client = TestClient(app)

@pytest.mark.asyncio
async def test_gemma_analyze_repository_fallback():
    repo_meta = {
        "full_name": "pallets/flask",
        "name": "flask",
        "description": "The Python micro framework for building web applications.",
        "language": "Python"
    }
    tree = [
        {"path": "src/flask/app.py", "size": 1200},
        {"path": "tests/test_app.py", "size": 800},
        {"path": "README.md", "size": 500}
    ]
    key_files = {"src/flask/app.py": "class Flask:\n    pass\n"}
    ast_summary = {
        "modules": [{"path": "src/flask/app.py", "classes": ["Flask"], "functions": []}],
        "entrypoints": ["src/flask/app.py"],
        "test_functions": 4
    }

    result = await cloud_llm_service.gemma_analyze_repository(
        repo_metadata=repo_meta,
        file_tree=tree,
        key_files=key_files,
        ast_summary=ast_summary,
        api_key=None
    )

    assert "executive_summary" in result
    assert "architecture_pattern" in result
    assert "beginner_friendly_areas" in result
    assert isinstance(result["beginner_friendly_areas"], list)
    assert "high_risk_areas" in result
    assert "contribution_quickstart" in result
    assert "setup_command" in result["contribution_quickstart"]
    assert "test_command" in result["contribution_quickstart"]

@pytest.mark.asyncio
async def test_gemma_analyze_repository_cloud_mock():
    repo_meta = {"name": "test-repo", "language": "Python"}
    tree = [{"path": "main.py", "size": 100}]
    key_files = {"main.py": "print('hello')"}
    ast_summary = {"modules": []}

    mock_json_reply = {
        "executive_summary": "Test software architecture.",
        "architecture_pattern": "Modular Pipeline",
        "primary_language": "Python",
        "entrypoints": [{"path": "main.py", "role": "CLI"}],
        "key_components": [],
        "beginner_friendly_areas": [{"area": "cli", "why": "simple", "recommended_files": ["main.py"]}],
        "high_risk_areas": [],
        "contribution_quickstart": {
            "prerequisites": ["Python 3.12"],
            "setup_command": "pip install -e .",
            "test_command": "pytest",
            "lint_command": "ruff check"
        },
        "architectural_pitfalls": ["Avoid global state"],
        "suggested_first_issues": ["Add docstrings"]
    }

    import json
    async with respx.mock(assert_all_called=False) as mock:
        mock.post("https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent").return_value = httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": json.dumps(mock_json_reply)}]
                        }
                    }
                ]
            }
        )

        result = await cloud_llm_service.gemma_analyze_repository(
            repo_metadata=repo_meta,
            file_tree=tree,
            key_files=key_files,
            ast_summary=ast_summary,
            api_key="AIzaSyMockKeyForGemma4Testing",
            provider="google_ai_studio",
            model="gemma-4-31b-it"
        )

        assert result["architecture_pattern"] == "Modular Pipeline"
        assert result["contribution_quickstart"]["test_command"] == "pytest"

def test_test_cloud_key_endpoint():
    with respx.mock(assert_all_called=False) as mock:
        mock.post("https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent").return_value = httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "Open source powers collaboration and innovation."}]
                        }
                    }
                ]
            }
        )

        res = client.post("/api/models/test-cloud-key", json={
            "api_key": "AIzaSyMockKeyForVerification",
            "provider": "google_ai_studio",
            "model": "gemma-4-31b-it"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "Open source" in data["test_output"]

def test_repo_ai_analysis_api_flow():
    # 1. Analyze repo
    res = client.post("/api/repositories/analyze", json={
        "url": "https://github.com/mock-gemma/gemma-test-repo"
    })
    assert res.status_code == 200
    repo_data = res.json()
    assert "ai_analysis" in repo_data

    # 2. Get repository detail
    get_res = client.get(f"/api/repositories/{repo_data['owner']}/{repo_data['name']}")
    assert get_res.status_code == 200
    detail = get_res.json()
    assert "ai_analysis" in detail
    assert isinstance(detail["ai_analysis"], dict)

    # 3. Get dedicated AI analysis endpoint
    ai_res = client.get(f"/api/repositories/{repo_data['owner']}/{repo_data['name']}/ai-analysis")
    assert ai_res.status_code == 200
    ai_data = ai_res.json()
    assert ai_data["status"] == "success"
    assert "ai_analysis" in ai_data

    # 4. Re-analyze with custom key
    re_res = client.post(f"/api/repositories/{repo_data['owner']}/{repo_data['name']}/ai-analyze", json={
        "api_key": None
    })
    assert re_res.status_code == 200
    re_data = re_res.json()
    assert re_data["status"] == "success"
    assert "ai_analysis" in re_data
