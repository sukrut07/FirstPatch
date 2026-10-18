"""
FirstPatch AI — GitHub API Service

Handles all communication with the GitHub REST API.
- URL normalization and validation
- Repository metadata retrieval
- Issue listing with pagination and PR filtering
- File content retrieval (bounded)
- Rate limit handling

Security: All fetched content is treated as untrusted data.
"""
from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Allowlist: only github.com hostname is permitted
_ALLOWED_GITHUB_HOST = "github.com"
_GITHUB_API_BASE = "https://api.github.com"

# Safety limits
_MAX_README_BYTES = 50_000
_MAX_FILE_BYTES = 30_000
_MAX_ISSUES_PER_PAGE = 100


@dataclass
class NormalizedRepo:
    owner: str
    repo: str
    original_url: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def github_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"


class GitHubURLError(ValueError):
    """Raised when a GitHub URL cannot be parsed or is invalid."""
    pass


class GitHubAPIError(Exception):
    """Raised when a GitHub API call fails."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub rate limit is exceeded."""
    pass


class GitHubNotFoundError(GitHubAPIError):
    """Raised when a repository or resource is not found."""
    pass


def normalize_github_url(url: str) -> NormalizedRepo:
    """
    Parse and normalize a GitHub repository URL.

    Accepts:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - https://github.com/owner/repo/tree/branch
      - github.com/owner/repo (without scheme)

    Returns a NormalizedRepo with validated owner and repo.

    Raises GitHubURLError for invalid or disallowed URLs.
    """
    original = url.strip()

    # Add scheme if missing
    if not original.startswith("http"):
        url = "https://" + original

    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise GitHubURLError(f"Cannot parse URL: {original}") from exc

    # SSRF protection: enforce github.com hostname
    hostname = parsed.hostname or ""
    if hostname.lower() != _ALLOWED_GITHUB_HOST:
        raise GitHubURLError(
            f"Only github.com URLs are supported. Got hostname: {hostname!r}"
        )

    # Extract path segments
    path = parsed.path.rstrip("/")
    segments = [s for s in path.split("/") if s]

    if len(segments) < 2:
        raise GitHubURLError(
            f"URL must include owner and repository name: {original}"
        )

    owner = segments[0]
    repo = segments[1].removesuffix(".git")

    # Validate identifier characters (GitHub allows alphanumeric, dash, underscore, dot)
    _validate_identifier(owner, "owner")
    _validate_identifier(repo, "repository")

    return NormalizedRepo(owner=owner, repo=repo, original_url=original)


def _validate_identifier(value: str, label: str) -> None:
    """Ensure a GitHub owner or repo name contains only allowed characters."""
    if not value:
        raise GitHubURLError(f"GitHub {label} name must not be empty")
    if len(value) > 100:
        raise GitHubURLError(f"GitHub {label} name is too long: {value!r}")
    if not re.match(r"^[a-zA-Z0-9._-]+$", value):
        raise GitHubURLError(
            f"GitHub {label} name contains invalid characters: {value!r}"
        )


def _make_client() -> httpx.AsyncClient:
    settings = get_settings()
    return httpx.AsyncClient(
        headers=settings.github_headers,
        timeout=settings.github_http_timeout,
        follow_redirects=True,
    )


class GitHubService:
    """
    Encapsulates all GitHub API interactions.

    Every method documents:
    - What GitHub endpoint it calls
    - What it returns
    - What errors it raises
    - Any rate-limit or pagination behaviour
    """

    async def get_repository_metadata(self, owner: str, repo: str) -> dict[str, Any]:
        """
        Fetch repository metadata from GET /repos/{owner}/{repo}.

        Returns the raw GitHub API response dict.
        Raises GitHubNotFoundError, GitHubRateLimitError, or GitHubAPIError.
        """
        url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}"
        async with _make_client() as client:
            response = await client.get(url)
            _check_response(response, owner, repo)
            return response.json()

    async def get_default_branch_sha(self, owner: str, repo: str, branch: str) -> Optional[str]:
        """
        Fetch the latest commit SHA for the default branch.
        GET /repos/{owner}/{repo}/commits/{branch}
        """
        url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{branch}"
        async with _make_client() as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("sha")
            logger.warning(
                "Could not fetch commit SHA for %s/%s@%s: HTTP %s",
                owner, repo, branch, response.status_code,
            )
            return None

    async def get_readme(self, owner: str, repo: str) -> Optional[str]:
        """
        Fetch the README content (decoded from base64).
        GET /repos/{owner}/{repo}/readme

        Returns the raw README text (max _MAX_README_BYTES bytes) or None.
        Content is treated as untrusted data.
        """
        url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
        async with _make_client() as client:
            response = await client.get(url)
            if response.status_code == 404:
                return None
            _check_response(response, owner, repo)
            data = response.json()
            encoded = data.get("content", "")
            if not encoded:
                return None
            try:
                decoded = base64.b64decode(encoded).decode("utf-8", errors="replace")
                return decoded[:_MAX_README_BYTES]
            except Exception:
                logger.warning("Failed to decode README for %s/%s", owner, repo)
                return None

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: Optional[str] = None
    ) -> Optional[str]:
        """
        Fetch a specific file's content.
        GET /repos/{owner}/{repo}/contents/{path}

        Returns up to _MAX_FILE_BYTES of decoded content or None.
        """
        url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params["ref"] = ref

        async with _make_client() as client:
            response = await client.get(url, params=params)
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                return None
            data = response.json()
            if data.get("type") != "file":
                return None
            encoded = data.get("content", "")
            if not encoded:
                return None
            try:
                decoded = base64.b64decode(encoded).decode("utf-8", errors="replace")
                return decoded[:_MAX_FILE_BYTES]
            except Exception:
                return None

    async def get_tree(
        self, owner: str, repo: str, sha: str, recursive: bool = False
    ) -> list[dict[str, Any]]:
        """
        Fetch the repository tree.
        GET /repos/{owner}/{repo}/git/trees/{sha}

        Returns a list of tree items. Use recursive=False for top-level only.
        Truncated trees are logged as warnings.
        """
        url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{sha}"
        params = {"recursive": "1"} if recursive else {}
        async with _make_client() as client:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                logger.warning(
                    "Could not fetch tree for %s/%s@%s: HTTP %s",
                    owner, repo, sha, response.status_code,
                )
                return []
            data = response.json()
            if data.get("truncated"):
                logger.warning(
                    "Tree for %s/%s is truncated (large repository). "
                    "Analysis will be partial.",
                    owner, repo,
                )
            return data.get("tree", [])

    async def get_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
        labels: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """
        Fetch issues (excluding pull requests) from the repository.
        GET /repos/{owner}/{repo}/issues

        Returns (issues_list, has_more_pages).
        Pull requests are excluded from results.
        """
        settings = get_settings()
        capped_per_page = min(per_page, _MAX_ISSUES_PER_PAGE)

        url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
        params: dict[str, Any] = {
            "state": state,
            "per_page": capped_per_page,
            "page": page,
            "direction": "desc",
            "sort": "updated",
        }
        if labels:
            params["labels"] = labels

        async with _make_client() as client:
            response = await client.get(url, params=params)
            _check_response(response, owner, repo)
            all_items = response.json()

        # Exclude pull requests (GitHub Issues API includes PRs)
        issues = [item for item in all_items if "pull_request" not in item]

        # Check for next page via Link header
        link_header = response.headers.get("link", "")
        has_more = 'rel="next"' in link_header

        return issues, has_more

    async def get_languages(self, owner: str, repo: str) -> dict[str, int]:
        """
        Fetch language breakdown.
        GET /repos/{owner}/{repo}/languages
        Returns {language: bytes} dict.
        """
        url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/languages"
        async with _make_client() as client:
            response = await client.get(url)
            if response.status_code != 200:
                return {}
            return response.json()

    async def get_rate_limit(self) -> dict[str, Any]:
        """Check current rate limit status."""
        url = f"{_GITHUB_API_BASE}/rate_limit"
        async with _make_client() as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            return {}


def _check_response(response: httpx.Response, owner: str, repo: str) -> None:
    """Check HTTP response and raise appropriate errors."""
    if response.status_code == 200:
        return
    if response.status_code == 403:
        reset_time = response.headers.get("X-RateLimit-Reset", "unknown")
        raise GitHubRateLimitError(
            f"GitHub rate limit exceeded. Resets at: {reset_time}. "
            "Set GITHUB_TOKEN in .env to increase limits.",
            status_code=403,
        )
    if response.status_code == 404:
        raise GitHubNotFoundError(
            f"Repository {owner}/{repo} not found or is private.",
            status_code=404,
        )
    if response.status_code == 451:
        raise GitHubAPIError(
            f"Repository {owner}/{repo} is unavailable for legal reasons.",
            status_code=451,
        )
    raise GitHubAPIError(
        f"GitHub API error: HTTP {response.status_code} for {owner}/{repo}",
        status_code=response.status_code,
    )


# Singleton accessor
_github_service: Optional[GitHubService] = None


def get_github_service() -> GitHubService:
    global _github_service
    if _github_service is None:
        _github_service = GitHubService()
    return _github_service
