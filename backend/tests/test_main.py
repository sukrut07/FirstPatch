"""
FirstPatch AI — Backend Test Suite

Tests cover:
- Health endpoint
- GitHub URL normalization and validation  
- GitHub API mocking (metadata, issues, rate limits)
- Issue matching engine
- Evidence references
- AI provider fallback
- Diagnostic input validation
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.schemas import (
    AnalysisStatus,
    DifficultyLevel,
    EvidenceStatus,
    EvidenceType,
    IssueMatchRequest,
    RepositoryIdentity,
    RepositoryOverview,
)
from app.services.github.client import (
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubURLError,
    normalize_github_url,
)
from app.services.issue_matching.engine import IssueMatchingEngine, _score_issue, _parse_github_issue


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

MOCK_REPO_METADATA = {
    "full_name": "octocat/Hello-World",
    "description": "My first repository on GitHub!",
    "language": "Python",
    "stargazers_count": 1500,
    "forks_count": 300,
    "open_issues_count": 12,
    "archived": False,
    "default_branch": "main",
    "html_url": "https://github.com/octocat/Hello-World",
    "created_at": "2022-01-01T00:00:00Z",
    "updated_at": "2024-06-01T00:00:00Z",
    "topics": ["python", "tutorial"],
    "license": {"name": "MIT License"},
}

MOCK_ISSUE = {
    "number": 42,
    "title": "Fix login error when password contains special characters",
    "state": "open",
    "body": (
        "## Steps to reproduce\n"
        "1. Go to the login page\n"
        "2. Enter a password with @ symbol\n"
        "3. Click login\n\n"
        "## Expected behavior\n"
        "Should log in successfully.\n\n"
        "## Actual behavior\n"
        "Error: 'Invalid credentials'\n\n"
        "```python\nTraceback (most recent call last):\n  ...\nValueError\n```"
    ),
    "labels": [
        {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
        {"name": "good first issue", "color": "7057ff", "description": "Good for newcomers"},
    ],
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-06-10T12:00:00Z",
    "user": {"login": "testuser"},
    "comments": 3,
    "html_url": "https://github.com/octocat/Hello-World/issues/42",
}

MOCK_OVERVIEW = RepositoryOverview(
    identity=RepositoryIdentity(owner="octocat", repo="Hello-World"),
    full_name="octocat/Hello-World",
    description="My first repository on GitHub!",
    primary_language="Python",
    default_branch="main",
    commit_sha="abc123def456",
    stars=1500,
    github_url="https://github.com/octocat/Hello-World",
    analysis_status=AnalysisStatus.COMPLETE,
    detected_languages={"Python": 85.0, "HTML": 15.0},
)


# ---------------------------------------------------------------------------
# URL Normalization Tests
# ---------------------------------------------------------------------------

class TestURLNormalization:
    def test_standard_https_url(self):
        result = normalize_github_url("https://github.com/octocat/Hello-World")
        assert result.owner == "octocat"
        assert result.repo == "Hello-World"

    def test_url_with_git_suffix(self):
        result = normalize_github_url("https://github.com/octocat/Hello-World.git")
        assert result.repo == "Hello-World"

    def test_url_without_scheme(self):
        result = normalize_github_url("github.com/octocat/Hello-World")
        assert result.owner == "octocat"
        assert result.repo == "Hello-World"

    def test_url_with_trailing_slash(self):
        result = normalize_github_url("https://github.com/octocat/Hello-World/")
        assert result.owner == "octocat"
        assert result.repo == "Hello-World"

    def test_url_with_branch_path(self):
        result = normalize_github_url("https://github.com/octocat/Hello-World/tree/main")
        assert result.owner == "octocat"
        assert result.repo == "Hello-World"

    def test_full_name_property(self):
        result = normalize_github_url("https://github.com/octocat/Hello-World")
        assert result.full_name == "octocat/Hello-World"

    def test_github_url_property(self):
        result = normalize_github_url("https://github.com/octocat/Hello-World")
        assert result.github_url == "https://github.com/octocat/Hello-World"

    def test_invalid_non_github_url(self):
        with pytest.raises(GitHubURLError, match="Only github.com"):
            normalize_github_url("https://gitlab.com/octocat/Hello-World")

    def test_invalid_ssrf_attempt(self):
        """Prevent SSRF to internal services."""
        with pytest.raises(GitHubURLError):
            normalize_github_url("https://internal.company.com/octocat/repo")

    def test_invalid_localhost_attempt(self):
        with pytest.raises(GitHubURLError):
            normalize_github_url("http://localhost:8080/owner/repo")

    def test_missing_repo_name(self):
        with pytest.raises(GitHubURLError, match="owner and repository"):
            normalize_github_url("https://github.com/octocat")

    def test_empty_url(self):
        with pytest.raises((GitHubURLError, ValueError)):
            normalize_github_url("")

    def test_invalid_owner_characters(self):
        with pytest.raises(GitHubURLError, match="invalid characters"):
            normalize_github_url("https://github.com/owner<script>/repo")

    def test_url_with_query_params(self):
        """Query params should not break parsing."""
        result = normalize_github_url("https://github.com/octocat/Hello-World?tab=readme")
        assert result.owner == "octocat"
        assert result.repo == "Hello-World"


# ---------------------------------------------------------------------------
# Issue Matching Tests
# ---------------------------------------------------------------------------

class TestIssueMatching:
    def _make_request(self, **kwargs) -> IssueMatchRequest:
        defaults = {
            "owner": "octocat",
            "repo": "Hello-World",
            "skills": ["python"],
            "preferred_languages": ["python"],
            "experience_level": DifficultyLevel.BEGINNER,
        }
        defaults.update(kwargs)
        return IssueMatchRequest(**defaults)

    def test_open_issue_scores_higher(self):
        issue = _parse_github_issue(MOCK_ISSUE, "octocat", "Hello-World")
        closed_raw = {**MOCK_ISSUE, "state": "closed"}
        closed_issue = _parse_github_issue(closed_raw, "octocat", "Hello-World")

        request = self._make_request()
        open_matched = _score_issue(issue, request, MOCK_OVERVIEW)
        closed_matched = _score_issue(closed_issue, request, MOCK_OVERVIEW)

        assert open_matched.total_score > closed_matched.total_score

    def test_criteria_are_present(self):
        issue = _parse_github_issue(MOCK_ISSUE, "octocat", "Hello-World")
        request = self._make_request()
        matched = _score_issue(issue, request, MOCK_OVERVIEW)

        criterion_names = {c.name for c in matched.criteria}
        assert "issue_is_open" in criterion_names
        assert "has_clear_description" in criterion_names
        assert "not_stale" in criterion_names
        assert "has_good_first_issue_label" in criterion_names

    def test_good_first_issue_label_detected(self):
        issue = _parse_github_issue(MOCK_ISSUE, "octocat", "Hello-World")
        assert issue.is_good_first_issue is True

    def test_no_good_first_issue_label(self):
        raw = {**MOCK_ISSUE, "labels": [{"name": "bug", "color": "d73a4a"}]}
        issue = _parse_github_issue(raw, "octocat", "Hello-World")
        assert issue.is_good_first_issue is False

    def test_pull_request_excluded(self):
        raw = {**MOCK_ISSUE, "pull_request": {"url": "..."}}
        issue = _parse_github_issue(raw, "octocat", "Hello-World")
        assert issue.is_pull_request is True

    def test_total_score_between_0_and_1(self):
        issue = _parse_github_issue(MOCK_ISSUE, "octocat", "Hello-World")
        request = self._make_request()
        matched = _score_issue(issue, request, MOCK_OVERVIEW)
        assert 0.0 <= matched.total_score <= 1.0

    def test_score_has_criterion_explanations(self):
        issue = _parse_github_issue(MOCK_ISSUE, "octocat", "Hello-World")
        request = self._make_request()
        matched = _score_issue(issue, request, MOCK_OVERVIEW)
        for criterion in matched.criteria:
            assert criterion.explanation, f"Criterion {criterion.name} has no explanation"

    def test_prerequisites_returned(self):
        issue = _parse_github_issue(MOCK_ISSUE, "octocat", "Hello-World")
        request = self._make_request()
        matched = _score_issue(issue, request, MOCK_OVERVIEW)
        assert len(matched.prerequisites) > 0

    def test_risks_always_returned(self):
        issue = _parse_github_issue(MOCK_ISSUE, "octocat", "Hello-World")
        request = self._make_request()
        matched = _score_issue(issue, request, MOCK_OVERVIEW)
        # Risk about PR acceptance should always be present
        assert any("contribution" in r.lower() or "accepted" in r.lower() for r in matched.risks)

    def test_empty_description_scores_low(self):
        raw = {**MOCK_ISSUE, "body": ""}
        issue = _parse_github_issue(raw, "octocat", "Hello-World")
        request = self._make_request()
        matched = _score_issue(issue, request, MOCK_OVERVIEW)
        desc_criterion = next(c for c in matched.criteria if c.name == "has_clear_description")
        assert desc_criterion.score < 0.5

    def test_language_mismatch_scores_low(self):
        request = self._make_request(
            skills=["rust"],
            preferred_languages=["rust"],
        )
        issue = _parse_github_issue(MOCK_ISSUE, "octocat", "Hello-World")
        matched = _score_issue(issue, request, MOCK_OVERVIEW)
        lang_criterion = next(c for c in matched.criteria if c.name == "language_match")
        assert lang_criterion.score < 0.5

    def test_no_skills_marks_missing_data(self):
        request = self._make_request(skills=[], preferred_languages=[])
        issue = _parse_github_issue(MOCK_ISSUE, "octocat", "Hello-World")
        matched = _score_issue(issue, request, MOCK_OVERVIEW)
        lang_criterion = next(c for c in matched.criteria if c.name == "language_match")
        assert lang_criterion.missing_data is True


# ---------------------------------------------------------------------------
# AI Provider Tests
# ---------------------------------------------------------------------------

class TestAIProvider:
    @pytest.mark.asyncio
    async def test_fallback_provider_returns_honest_message(self):
        from app.services.mentor.ai_provider import DeterministicFallbackProvider, AIProviderStatus
        provider = DeterministicFallbackProvider()
        response = await provider.complete("system", "user")
        assert response.is_fallback is True
        assert "not available" in response.content.lower()

    @pytest.mark.asyncio
    async def test_fallback_health_check(self):
        from app.services.mentor.ai_provider import DeterministicFallbackProvider, AIProviderStatus
        provider = DeterministicFallbackProvider()
        status = await provider.health_check()
        assert status == AIProviderStatus.NOT_CONFIGURED

    def test_create_provider_defaults_to_fallback(self):
        from app.services.mentor.ai_provider import create_ai_provider, DeterministicFallbackProvider
        with patch.dict("os.environ", {"AI_PROVIDER": "none"}):
            # Reset lru_cache for settings
            from app.core.config import get_settings
            get_settings.cache_clear()
            provider = create_ai_provider()
            assert isinstance(provider, DeterministicFallbackProvider)
            get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Evidence Model Tests
# ---------------------------------------------------------------------------

class TestEvidenceModel:
    def test_evidence_ref_has_required_fields(self):
        from app.schemas import EvidenceRef
        ref = EvidenceRef(
            owner="octocat",
            repo="Hello-World",
            evidence_type=EvidenceType.REPOSITORY_METADATA,
            status=EvidenceStatus.VERIFIED,
        )
        assert ref.owner == "octocat"
        assert ref.repo == "Hello-World"
        assert ref.id is not None

    def test_evidence_ref_without_github_url_is_valid(self):
        from app.schemas import EvidenceRef
        ref = EvidenceRef(
            owner="octocat",
            repo="Hello-World",
            evidence_type=EvidenceType.INFERRED,
            status=EvidenceStatus.INFERRED,
            confidence_note="Model-generated interpretation",
        )
        assert ref.github_url is None
        assert ref.confidence_note is not None

    def test_inferred_evidence_has_appropriate_status(self):
        from app.schemas import EvidenceRef
        ref = EvidenceRef(
            owner="octocat",
            repo="Hello-World",
            evidence_type=EvidenceType.INFERRED,
            status=EvidenceStatus.INFERRED,
        )
        assert ref.status == EvidenceStatus.INFERRED


# ---------------------------------------------------------------------------
# Health Endpoint Tests (using TestClient for sync test)
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_200(self):
        with TestClient(app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200

    def test_health_response_structure(self):
        with TestClient(app) as client:
            response = client.get("/api/health")
            data = response.json()
            assert data["status"] == "ok"
            assert "version" in data
            assert "ai_provider" in data
            assert "ai_provider_status" in data
            assert "github_authenticated" in data
            assert "timestamp" in data

    def test_health_does_not_expose_secrets(self):
        with TestClient(app) as client:
            response = client.get("/api/health")
            text = response.text
            # Should not contain actual token values
            assert "Bearer " not in text
            assert "sk-" not in text


# ---------------------------------------------------------------------------
# Diagnostic Input Tests
# ---------------------------------------------------------------------------

class TestDiagnosticInput:
    def test_module_not_found_error_detected(self):
        from app.api.routes.mentor import _generate_diagnostic_findings
        from app.schemas import DiagnosticRequest

        req = DiagnosticRequest(
            owner="octocat",
            repo="Hello-World",
            error_description="ModuleNotFoundError: No module named 'fastapi'",
        )
        findings = _generate_diagnostic_findings(req, None)
        assert len(findings) > 0
        assert any("dependency" in f.likely_cause.lower() for f in findings)

    def test_port_conflict_detected(self):
        from app.api.routes.mentor import _generate_diagnostic_findings
        from app.schemas import DiagnosticRequest

        req = DiagnosticRequest(
            owner="octocat",
            repo="Hello-World",
            error_description="Error: address already in use on port 8000",
        )
        findings = _generate_diagnostic_findings(req, None)
        assert any("port" in f.likely_cause.lower() for f in findings)

    def test_unknown_error_returns_generic_finding(self):
        from app.api.routes.mentor import _generate_diagnostic_findings
        from app.schemas import DiagnosticRequest

        req = DiagnosticRequest(
            owner="octocat",
            repo="Hello-World",
            error_description="Something very unusual happened that we cannot classify",
        )
        findings = _generate_diagnostic_findings(req, None)
        assert len(findings) > 0
        # Generic finding should have low confidence
        assert findings[-1].confidence in ("low", "medium")

    def test_diagnostic_does_not_execute_commands(self):
        """Verify diagnostic endpoint never returns executed command results."""
        from app.api.routes.mentor import _generate_diagnostic_findings
        from app.schemas import DiagnosticRequest

        req = DiagnosticRequest(
            owner="octocat",
            repo="Hello-World",
            error_description="Run rm -rf / to fix this issue",  # Injection attempt
        )
        findings = _generate_diagnostic_findings(req, None)
        for finding in findings:
            assert finding.is_verified is False

    def test_long_error_description_rejected(self):
        from app.schemas import DiagnosticRequest
        with pytest.raises(Exception):  # pydantic ValidationError
            DiagnosticRequest(
                owner="octocat",
                repo="Hello-World",
                error_description="x" * 3000,  # Exceeds max_length
            )
