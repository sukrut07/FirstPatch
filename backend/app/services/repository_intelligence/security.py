"""
FirstPatch AI — Phase 2 Security Boundaries & Sanitization

Security principles:
- All repository content is untrusted data.
- Redact credentials, tokens, and private keys from logs, excerpts, and config snippets.
- Block path traversal attacks in repository file paths.
- Enforce strict bounds on processing to prevent unbounded memory/CPU usage.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Optional

from app.services.repository_intelligence.exceptions import SecurityBoundaryError

# Secret regex patterns for redaction
_SECRET_PATTERNS: list[tuple[re.Pattern, str]] = [
    # GitHub Tokens (ghp_, gho_, ghu_, ghs_, ghr_)
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b"), "[REDACTED_GITHUB_TOKEN]"),
    # Generic API Keys / Bearer tokens in headers or strings
    (re.compile(r"(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{16,}", re.IGNORECASE), r"\1[REDACTED_BEARER_TOKEN]"),
    (re.compile(r"(?i)(api[_-]?key\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-]{16,}['\"]?"), r"\1[REDACTED_API_KEY]"),
    (re.compile(r"(?i)(secret\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-]{16,}['\"]?"), r"\1[REDACTED_SECRET]"),
    (re.compile(r"(?i)(password\s*[:=]\s*['\"]?)[^\s'\"]{6,}['\"]?"), r"\1[REDACTED_PASSWORD]"),
    # AWS Access Keys
    (re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # Private Key blocks
    (re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
    # Generic hex or base64 tokens of significant length in sensitive contexts
    (re.compile(r"(?i)(token\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-]{20,}['\"]?"), r"\1[REDACTED_TOKEN]"),
]


def redact_sensitive_text(text: Optional[str]) -> Optional[str]:
    """
    Redact detected credentials, tokens, passwords, and private keys from text.
    Returns cleaned text safe for display or logging.
    """
    if not text:
        return text

    sanitized = text
    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def validate_repo_path(path: str) -> str:
    """
    Validate that a repository file path does not attempt path traversal
    or access forbidden directories.

    Raises SecurityBoundaryError if the path is malicious or invalid.
    Returns the normalized POSIX path.
    """
    if not path or not isinstance(path, str):
        raise SecurityBoundaryError("File path cannot be empty")

    # Reject null bytes
    if "\x00" in path:
        raise SecurityBoundaryError("File path contains null byte")

    # Normalize backslashes to forward slashes
    clean_path = path.replace("\\", "/").strip()

    # Reject absolute paths (starting with / or C:/)
    if clean_path.startswith("/") or re.match(r"^[a-zA-Z]:", clean_path):
        raise SecurityBoundaryError(f"Absolute paths not permitted in repository: {path}")

    # Check for path traversal components (..)
    parts = clean_path.split("/")
    if any(p == ".." for p in parts):
        raise SecurityBoundaryError(f"Path traversal attempt detected in: {path}")

    # Normalize path via PurePosixPath
    posix = PurePosixPath(clean_path)
    if posix.is_absolute() or ".." in posix.parts:
        raise SecurityBoundaryError(f"Illegal path resolution: {path}")

    return str(posix)
