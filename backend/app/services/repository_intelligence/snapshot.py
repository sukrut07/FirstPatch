"""
FirstPatch AI — Phase 2 Repository Snapshot & File Inventory Service

Builds an immutable, pinned repository snapshot from real GitHub repository data.
Every analysis, code structure extraction, and evidence claim links directly
to this snapshot's commit SHA.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.github.client import (
    GitHubService,
    normalize_github_url,
)
from app.services.repository_intelligence.exceptions import (
    SecurityBoundaryError,
    SnapshotIncompleteError,
)
from app.services.repository_intelligence.schemas import (
    FileType,
    RepoFileEntry,
    RepositorySnapshot,
)
from app.services.repository_intelligence.security import validate_repo_path

logger = logging.getLogger(__name__)

# Known manifests
_MANIFEST_NAMES = {
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Gemfile",
}

# Known test config files
_TEST_CONFIG_NAMES = {
    "pytest.ini",
    ".pytest.ini",
    "tox.ini",
    ".coveragerc",
    "jest.config.js",
    "jest.config.ts",
    "jest.config.mjs",
    "vitest.config.js",
    "vitest.config.ts",
    ".mocharc.json",
    ".mocharc.js",
    "playwright.config.ts",
    "playwright.config.js",
    "cypress.config.ts",
    "cypress.config.js",
}

# Known documentation files
_DOC_NAMES = {
    "readme.md",
    "contributing.md",
    "license",
    "changelog.md",
    "code_of_conduct.md",
    "architecture.md",
    "security.md",
}


def classify_file(path: str) -> FileType:
    """Classify repository file by path and extension."""
    lower = path.lower()
    base_name = lower.split("/")[-1]

    if base_name in _MANIFEST_NAMES:
        return FileType.MANIFEST

    if base_name in _TEST_CONFIG_NAMES or "test.config" in base_name:
        return FileType.CONFIG

    if base_name in _DOC_NAMES or base_name.endswith((".md", ".rst", ".txt", ".adoc")):
        return FileType.DOC

    # Tests
    if (
        "/tests/" in f"/{lower}"
        or "/test/" in f"/{lower}"
        or "/__tests__/" in f"/{lower}"
        or base_name.startswith("test_")
        or base_name.endswith(("_test.py", ".test.js", ".test.ts", ".spec.js", ".spec.ts"))
    ):
        return FileType.TEST

    # Configs
    if (
        base_name.startswith(".")
        or base_name.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"))
        or "config" in base_name
    ):
        return FileType.CONFIG

    # Source code
    if base_name.endswith((
        ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt",
        ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".scala",
    )):
        return FileType.SOURCE

    # Assets
    if base_name.endswith((
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2",
        ".ttf", ".eot", ".mp4", ".mp3", ".pdf", ".zip", ".tar", ".gz",
    )):
        return FileType.ASSET

    return FileType.OTHER


class RepositorySnapshotService:
    """
    Creates and manages deterministic repository snapshots.
    Pins analysis to an immutable Git commit SHA.
    """

    def __init__(self, github: GitHubService):
        self.github = github
        self._content_cache: dict[tuple[str, str, str], str] = {}

    async def create_snapshot(
        self,
        repository_url: str,
        commit_sha: Optional[str] = None,
        recursive: bool = True,
    ) -> RepositorySnapshot:
        """
        Create a pinned snapshot for a repository URL.
        If commit_sha is not provided, resolves default branch SHA.
        """
        # Step 1: Normalize and validate URL
        normalized = normalize_github_url(repository_url)
        owner = normalized.owner
        repo = normalized.repo
        canonical_url = normalized.github_url

        warnings: list[str] = []
        is_partial = False

        # Step 2: Fetch repository metadata
        meta = await self.github.get_repository_metadata(owner, repo)
        default_branch = meta.get("default_branch", "main")

        # Step 3: Determine commit SHA
        if not commit_sha:
            commit_sha = await self.github.get_default_branch_sha(owner, repo, default_branch)

        if not commit_sha:
            warnings.append(
                f"Could not resolve commit SHA for branch '{default_branch}'. "
                "Snapshot integrity is compromised."
            )
            raise SnapshotIncompleteError(
                f"Cannot create snapshot for {owner}/{repo}: Unable to determine commit SHA."
            )

        # Step 4: Fetch language distribution
        languages_raw = await self.github.get_languages(owner, repo)
        total_bytes = sum(languages_raw.values()) or 1
        languages = {
            lang: round(count / total_bytes * 100, 1)
            for lang, count in languages_raw.items()
        }

        # Step 5: Fetch tree
        tree_data = await self.github.get_tree(owner, repo, commit_sha, recursive=recursive)
        if not tree_data:
            # Fallback to non-recursive if recursive failed or timed out
            tree_data = await self.github.get_tree(owner, repo, commit_sha, recursive=False)
            if tree_data:
                warnings.append("Directory tree was truncated to top-level entries.")
                is_partial = True
            else:
                warnings.append("Could not fetch repository directory tree.")
                is_partial = True

        # Step 6: Process file entries
        files: list[RepoFileEntry] = []
        manifests: list[str] = []
        test_configs: list[str] = []

        for item in tree_data:
            if item.get("type") != "blob":
                continue

            raw_path = item.get("path", "")
            try:
                valid_path = validate_repo_path(raw_path)
            except SecurityBoundaryError as exc:
                warnings.append(f"Skipped suspicious path in repository tree: {exc}")
                continue

            size = item.get("size", 0)
            file_type = classify_file(valid_path)

            file_entry = RepoFileEntry(
                path=valid_path,
                size=size,
                file_type=file_type,
            )
            files.append(file_entry)

            if file_type == FileType.MANIFEST:
                manifests.append(valid_path)
            elif file_type == FileType.CONFIG and any(cfg in valid_path.lower() for cfg in _TEST_CONFIG_NAMES):
                test_configs.append(valid_path)

        return RepositorySnapshot(
            owner=owner,
            repo=repo,
            canonical_url=canonical_url,
            default_branch=default_branch,
            commit_sha=commit_sha,
            analyzed_at=datetime.now(timezone.utc),
            files=files,
            language_percentages=languages,
            dependency_manifests=sorted(manifests),
            test_configs=sorted(test_configs),
            warnings=warnings,
            is_partial=is_partial,
        )

    async def get_file_content(
        self,
        snapshot: RepositorySnapshot,
        file_path: str,
    ) -> Optional[str]:
        """
        Fetch file content pinned to snapshot's commit_sha with caching.
        Enforces path validation and limits.
        """
        valid_path = validate_repo_path(file_path)
        cache_key = (snapshot.owner, snapshot.repo, f"{snapshot.commit_sha}:{valid_path}")

        if cache_key in self._content_cache:
            return self._content_cache[cache_key]

        content = await self.github.get_file_content(
            snapshot.owner,
            snapshot.repo,
            valid_path,
            ref=snapshot.commit_sha,
        )

        if content is not None:
            self._content_cache[cache_key] = content

        return content
