"""
Tests for Security Boundaries, SSRF, Path Traversal, and Secret Redaction
"""
import pytest

from app.services.github.client import GitHubURLError, normalize_github_url
from app.services.repository_intelligence.exceptions import SecurityBoundaryError
from app.services.repository_intelligence.security import (
    redact_sensitive_text,
    validate_repo_path,
)
from app.services.repository_intelligence.service import RepositoryIntelligenceService


def test_ssrf_protection_blocks_disallowed_hosts():
    disallowed_urls = [
        "http://localhost:8000/owner/repo",
        "http://127.0.0.1:8080/repo",
        "http://169.254.169.254/latest/meta-data",
        "https://internal.corp.com/owner/repo",
        "https://evil-site.com/github.com/owner/repo",
        "ftp://github.com/owner/repo",
    ]
    for url in disallowed_urls:
        with pytest.raises(GitHubURLError):
            normalize_github_url(url)


def test_path_traversal_detection():
    invalid_paths = [
        "../etc/passwd",
        "foo/../../bar",
        "/etc/shadow",
        "C:\\Windows\\System32\\cmd.exe",
        "app/\x00hidden.py",
        "",
    ]
    for path in invalid_paths:
        with pytest.raises(SecurityBoundaryError):
            validate_repo_path(path)


def test_valid_repo_paths():
    valid = [
        "app/main.py",
        "src/components/Button.tsx",
        ".github/workflows/ci.yml",
        "README.md",
    ]
    for path in valid:
        assert validate_repo_path(path) == path.replace("\\", "/")


def test_secret_redaction():
    text_with_secrets = (
        "Configuring connection with token: ghp_1234567890abcdef1234567890abcdef1234\n"
        "AWS credentials: AKIAIOSFODNN7EXAMPLE\n"
        "Authorization: Bearer my_super_secret_jwt_token_123456789\n"
        "password = 'my_super_password_123'\n"
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----\n"
    )

    redacted = redact_sensitive_text(text_with_secrets)

    assert "ghp_1234567890abcdef1234567890abcdef1234" not in redacted
    assert "[REDACTED_GITHUB_TOKEN]" in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[REDACTED_AWS_KEY]" in redacted
    assert "[REDACTED_BEARER_TOKEN]" in redacted
    assert "[REDACTED_PASSWORD]" in redacted
    assert "[REDACTED_PRIVATE_KEY]" in redacted


def test_phase2_works_without_model_credentials():
    """Verify that RepositoryIntelligenceService initializes and operates without any AI API key."""
    service = RepositoryIntelligenceService()
    assert service is not None
    assert service.code_analyzer is not None
    assert service.evidence_validator is not None
    assert service.snapshot_service is not None
