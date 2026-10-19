"""Repository analysis service — language detection, framework detection, test discovery."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.schemas import (
    AnalysisStatus,
    DetectedFramework,
    EvidenceRef,
    EvidenceStatus,
    EvidenceType,
    RepositoryIdentity,
    RepositoryOverview,
    TestLocation,
)
from app.services.github.client import (
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubService,
)

logger = logging.getLogger(__name__)

# Known configuration files to look for
_CONFIG_FILES = [
    # Python
    "setup.py", "setup.cfg", "pyproject.toml", "requirements.txt",
    "requirements-dev.txt", "Pipfile", "tox.ini",
    # JavaScript / Node
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    ".nvmrc", ".node-version",
    # Go
    "go.mod", "go.sum",
    # Rust
    "Cargo.toml", "Cargo.lock",
    # Java / Kotlin
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    # C/C++
    "CMakeLists.txt", "Makefile", "meson.build",
    # Docker / infrastructure
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".dockerignore",
    # CI/CD (top-level indicators only — full .github/workflows not listed)
    ".travis.yml", ".circleci/config.yml", "Jenkinsfile",
    # Misc
    ".gitmodules", "CONTRIBUTING.md", "CHANGELOG.md", "LICENSE",
    "CODE_OF_CONDUCT.md",
]

# Test directory patterns
_TEST_DIR_PATTERNS = [
    re.compile(r"^tests?/", re.IGNORECASE),
    re.compile(r"^spec/", re.IGNORECASE),
    re.compile(r"^__tests__/", re.IGNORECASE),
    re.compile(r"^test_", re.IGNORECASE),
    re.compile(r"/_tests?/", re.IGNORECASE),
    re.compile(r"/spec/", re.IGNORECASE),
    re.compile(r"/__tests__/", re.IGNORECASE),
]

# Framework detection rules: (framework_name, file_indicators, import_patterns)
_FRAMEWORK_RULES: list[tuple[str, list[str], list[str]]] = [
    ("Next.js", ["next.config.js", "next.config.ts", "next.config.mjs"], []),
    ("React", ["package.json"], ["react", "react-dom"]),
    ("FastAPI", ["requirements.txt", "pyproject.toml"], ["fastapi"]),
    ("Django", ["manage.py", "requirements.txt"], ["django"]),
    ("Flask", ["requirements.txt", "pyproject.toml"], ["flask"]),
    ("Express", ["package.json"], ["express"]),
    ("Vue.js", ["vue.config.js", "vite.config.js"], ["vue"]),
    ("Pytest", ["pytest.ini", "setup.cfg", "pyproject.toml", "tox.ini"], ["pytest"]),
    ("Jest", ["jest.config.js", "jest.config.ts", "package.json"], ["jest"]),
    ("Docker", ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"], []),
]


class RepositoryAnalysisService:
    """
    Analyzes a GitHub repository structure without cloning it.

    Strategy:
    1. Fetch repository metadata (1 API call)
    2. Fetch the git tree (1 API call, non-recursive for large repos)
    3. Identify config files, test locations, and languages from the tree
    4. Fetch specific important files (README, package.json, etc.)
    5. Build evidence-backed analysis

    All content is treated as untrusted data.
    """

    def __init__(self, github: GitHubService):
        self.github = github

    async def analyze(self, owner: str, repo: str) -> RepositoryOverview:
        """
        Perform a full repository analysis.
        Returns a RepositoryOverview with evidence references.
        """
        start_time = datetime.now(timezone.utc)
        warnings: list[str] = []
        evidence_refs: list[EvidenceRef] = []

        # --- Step 1: Fetch repository metadata ---
        try:
            meta = await self.github.get_repository_metadata(owner, repo)
        except GitHubNotFoundError as exc:
            return RepositoryOverview(
                identity=RepositoryIdentity(owner=owner, repo=repo),
                full_name=f"{owner}/{repo}",
                github_url=f"https://github.com/{owner}/{repo}",
                analysis_status=AnalysisStatus.FAILED,
                analysis_warnings=[str(exc)],
            )
        except GitHubRateLimitError as exc:
            return RepositoryOverview(
                identity=RepositoryIdentity(owner=owner, repo=repo),
                full_name=f"{owner}/{repo}",
                github_url=f"https://github.com/{owner}/{repo}",
                analysis_status=AnalysisStatus.FAILED,
                analysis_warnings=[str(exc)],
            )
        except GitHubAPIError as exc:
            return RepositoryOverview(
                identity=RepositoryIdentity(owner=owner, repo=repo),
                full_name=f"{owner}/{repo}",
                github_url=f"https://github.com/{owner}/{repo}",
                analysis_status=AnalysisStatus.FAILED,
                analysis_warnings=[str(exc)],
            )
        except Exception as exc:
            return RepositoryOverview(
                identity=RepositoryIdentity(owner=owner, repo=repo),
                full_name=f"{owner}/{repo}",
                github_url=f"https://github.com/{owner}/{repo}",
                analysis_status=AnalysisStatus.FAILED,
                analysis_warnings=[f"Network error communicating with GitHub: {exc}"],
            )

        meta_evidence = EvidenceRef(
            owner=owner,
            repo=repo,
            evidence_type=EvidenceType.REPOSITORY_METADATA,
            github_url=f"https://github.com/{owner}/{repo}",
            excerpt=f"stars={meta.get('stargazers_count', 0)}, "
                    f"language={meta.get('language', 'unknown')}",
            status=EvidenceStatus.VERIFIED,
        )
        evidence_refs.append(meta_evidence)

        default_branch = meta.get("default_branch", "main")

        # --- Step 2: Get commit SHA ---
        commit_sha = await self.github.get_default_branch_sha(owner, repo, default_branch)
        if not commit_sha:
            warnings.append(
                f"Could not determine commit SHA for branch '{default_branch}'. "
                "Analysis is not pinned to a specific snapshot."
            )

        # --- Step 3: Get language breakdown ---
        languages_raw = await self.github.get_languages(owner, repo)
        total_bytes = sum(languages_raw.values()) or 1
        detected_languages = {
            lang: round(count / total_bytes * 100, 1)
            for lang, count in languages_raw.items()
        }

        # --- Step 4: Get repository tree ---
        tree_items: list[dict] = []
        if commit_sha:
            tree_items = await self.github.get_tree(owner, repo, commit_sha, recursive=False)
            if not tree_items:
                warnings.append(
                    "Could not retrieve directory tree. "
                    "File analysis will be limited."
                )

        # Flatten to paths
        all_paths = [item["path"] for item in tree_items if "path" in item]

        # Top-level directory snapshot
        top_level = list({
            p.split("/")[0] for p in all_paths
        })[:50]

        # --- Step 5: Identify config files ---
        found_configs = [p for p in all_paths if p in _CONFIG_FILES]

        # --- Step 6: Identify test locations ---
        test_locations = _detect_test_locations(all_paths, owner, repo)

        # --- Step 7: Fetch README ---
        readme_text = await self.github.get_readme(owner, repo)
        readme_summary: Optional[str] = None
        if readme_text:
            readme_summary = _summarize_readme(readme_text)
            readme_evidence = EvidenceRef(
                owner=owner,
                repo=repo,
                commit_sha=commit_sha,
                file_path="README.md",
                github_url=f"https://github.com/{owner}/{repo}/blob/{default_branch}/README.md",
                evidence_type=EvidenceType.README_STATEMENT,
                excerpt=readme_text[:300],
                status=EvidenceStatus.VERIFIED,
            )
            evidence_refs.append(readme_evidence)
        else:
            warnings.append("No README found. Setup instructions may be unavailable.")

        # --- Step 8: Detect frameworks ---
        frameworks = await _detect_frameworks(
            owner, repo, all_paths, self.github, default_branch, commit_sha, warnings
        )

        # --- Step 9: Parse timestamps ---
        created_at = _parse_dt(meta.get("created_at"))
        updated_at = _parse_dt(meta.get("updated_at"))

        from datetime import timedelta
        from app.core.config import get_settings
        settings = get_settings()
        analyzed_at = datetime.now(timezone.utc)
        cache_expires_at = analyzed_at + timedelta(seconds=settings.repo_cache_ttl_seconds)

        status = (
            AnalysisStatus.PARTIAL
            if warnings
            else AnalysisStatus.COMPLETE
        )

        return RepositoryOverview(
            identity=RepositoryIdentity(owner=owner, repo=repo),
            full_name=meta.get("full_name", f"{owner}/{repo}"),
            description=meta.get("description"),
            primary_language=meta.get("language"),
            topics=meta.get("topics", []),
            default_branch=default_branch,
            commit_sha=commit_sha,
            stars=meta.get("stargazers_count", 0),
            forks=meta.get("forks_count", 0),
            open_issues_count=meta.get("open_issues_count", 0),
            archived=meta.get("archived", False),
            license_name=meta.get("license", {}).get("name") if meta.get("license") else None,
            github_url=meta.get("html_url", f"https://github.com/{owner}/{repo}"),
            created_at=created_at,
            updated_at=updated_at,
            readme_summary=readme_summary,
            detected_frameworks=frameworks,
            config_files=found_configs,
            test_locations=test_locations,
            directory_snapshot=sorted(top_level),
            detected_languages=detected_languages,
            analysis_status=status,
            analysis_warnings=warnings,
            evidence_refs=evidence_refs,
            analyzed_at=analyzed_at,
            cache_expires_at=cache_expires_at,
        )


def _detect_test_locations(
    paths: list[str], owner: str, repo: str
) -> list[TestLocation]:
    """Identify likely test directories from the path list."""
    test_dirs: set[str] = set()
    for path in paths:
        for pattern in _TEST_DIR_PATTERNS:
            if pattern.search(path):
                # Get the test directory root
                parts = path.split("/")
                for i, part in enumerate(parts):
                    candidate = "/".join(parts[:i+1])
                    if pattern.search(candidate + "/"):
                        test_dirs.add(candidate)
                        break
                break

    result = []
    for d in sorted(test_dirs)[:10]:  # Limit to 10
        framework = _infer_test_framework_from_path(d)
        result.append(TestLocation(
            path=d,
            framework=framework,
        ))
    return result


def _infer_test_framework_from_path(path: str) -> Optional[str]:
    """Infer the likely testing framework from a directory name."""
    lower = path.lower()
    if "spec" in lower:
        return "Jest/RSpec"
    if "pytest" in lower or (path.startswith("tests") or path == "test"):
        return "pytest (likely)"
    return None


async def _detect_frameworks(
    owner: str,
    repo: str,
    paths: list[str],
    github: GitHubService,
    default_branch: str,
    commit_sha: Optional[str],
    warnings: list[str],
) -> list[DetectedFramework]:
    """Detect frameworks from file existence and content hints."""
    frameworks: list[DetectedFramework] = []
    path_set = set(paths)

    for name, file_indicators, import_patterns in _FRAMEWORK_RULES:
        matched_files = [f for f in file_indicators if f in path_set]
        if not matched_files:
            continue

        confidence = "certain" if not import_patterns else "likely"
        evidence_list: list[EvidenceRef] = []

        for matched_file in matched_files[:1]:  # Check the first matched file
            ref_url = f"https://github.com/{owner}/{repo}/blob/{default_branch}/{matched_file}"
            evidence_list.append(EvidenceRef(
                owner=owner,
                repo=repo,
                commit_sha=commit_sha,
                file_path=matched_file,
                github_url=ref_url,
                evidence_type=EvidenceType.CONFIG_DECLARATION,
                excerpt=f"File '{matched_file}' present in repository",
                status=EvidenceStatus.VERIFIED,
            ))

        frameworks.append(DetectedFramework(
            name=name,
            confidence=confidence,
            evidence=evidence_list,
        ))

    return frameworks


def _summarize_readme(readme_text: str) -> str:
    """Extract a safe, bounded summary from README text."""
    lines = readme_text.splitlines()
    # Find the first non-empty, non-header paragraph
    paragraphs: list[str] = []
    current: list[str] = []

    for line in lines[:100]:  # Only look at first 100 lines
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("!"):
            current.append(stripped)
        else:
            if current:
                paragraphs.append(" ".join(current))
                current = []

    if current:
        paragraphs.append(" ".join(current))

    for para in paragraphs:
        if len(para) > 30:
            return para[:500]

    # Fallback: return first 200 chars of non-empty content
    content = " ".join(lines[:5])
    return content[:200] if content.strip() else "README available (no summary extracted)"


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
