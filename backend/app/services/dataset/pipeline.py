"""
FirstPatch AI — Dataset Pipeline (Phase 4)

Handles:
1. Synthetic dataset generation (always available, no external deps)
2. Dataset acquisition coordination (requires explicit user consent; no auto-downloads)
3. JSONL serialization/deserialization for evaluation tasks with full provenance
4. Deterministic sampling and repository-level train/validation/test split generation
   to guarantee zero split leakage across evaluation tasks.

Design constraints:
- No GPU required
- No mandatory external downloads for tests to pass
- Explicit acquisition consent required for external sources
- All external download attempts wrapped with honest reporting
- Synthetic set covers all task types for CI/offline use
"""
from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

from app.services.dataset.manifest import (
    DATASET_DIR,
    AcquisitionMethod,
    DatasetManifest,
    DatasetStatus,
)
from app.services.dataset.task_schema import (
    EvaluationTask,
    TaskDifficulty,
    TaskType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DatasetSample — wire format for one record read from disk
# ---------------------------------------------------------------------------

@dataclass
class DatasetSample:
    """Raw record read from a dataset JSONL file."""
    source: str
    raw: dict[str, Any]

    def to_task(self) -> Optional[EvaluationTask]:
        """
        Convert raw record to an EvaluationTask where possible.
        Returns None if the record cannot be mapped.
        """
        raw = self.raw
        source = self.source

        # SWE-bench Lite schema
        if "instance_id" in raw and "patch" in raw:
            return _swe_bench_to_task(raw, source)

        # CodeSearchNet schema
        if "func_name" in raw and "code" in raw:
            return _codesearchnet_to_task(raw, source)

        # Synthetic / pre-converted schema
        if "task_type" in raw:
            try:
                return EvaluationTask(**raw)
            except Exception as exc:
                logger.debug("Could not parse pre-converted task: %s", exc)
                return None

        return None


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def _swe_bench_to_task(raw: dict[str, Any], source: str) -> EvaluationTask:
    """Map a SWE-bench Lite record to an EvaluationTask."""
    instance_id = raw.get("instance_id", "")
    parts = instance_id.split("-", 1)
    repo_part = parts[0] if parts else ""
    owner_repo = repo_part.split("__", 1)
    owner = owner_repo[0] if owner_repo else ""
    repo = owner_repo[1] if len(owner_repo) > 1 else repo_part

    # Extract files touched in the patch
    patch_text = raw.get("patch", "")
    patch_files: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("diff --git a/"):
            parts_patch = line.split(" b/")
            if len(parts_patch) > 1:
                patch_files.append(parts_patch[1].strip())

    base_commit = raw.get("base_commit", "")
    return EvaluationTask(
        task_type=TaskType.ISSUE_TRACING,
        difficulty=TaskDifficulty.HARD,
        dataset_source=source,
        owner=owner,
        repo=repo,
        issue_number=int(raw.get("number", 0)),
        issue_title=raw.get("problem_statement", "")[:200],
        issue_body=raw.get("problem_statement", ""),
        commit_sha=base_commit,
        source_url=f"https://github.com/{owner}/{repo}/issues/{raw.get('number', 0)}",
        dataset_version="1.0.0",
        license="MIT",
        split="test",
        expected_patch_files=patch_files,
        expected_relevant_files=patch_files,
        tags=["swe_bench", "real_world"],
        extra={"instance_id": instance_id},
    )


def _codesearchnet_to_task(raw: dict[str, Any], source: str) -> EvaluationTask:
    """Map a CodeSearchNet record to a file-relevance EvaluationTask."""
    func_name = raw.get("func_name", "")
    repo = raw.get("repo", "")
    path = raw.get("path", "")
    owner = repo.split("/")[0] if "/" in repo else "unknown"
    repo_name = repo.split("/")[1] if "/" in repo else repo
    return EvaluationTask(
        task_type=TaskType.FILE_RELEVANCE,
        difficulty=TaskDifficulty.EASY,
        dataset_source=source,
        owner=owner,
        repo=repo_name,
        issue_title=func_name,
        issue_body=raw.get("docstring", ""),
        commit_sha=raw.get("sha", ""),
        source_url=raw.get("url", ""),
        dataset_version="1.0.0",
        license="CC BY 4.0",
        split="train",
        expected_relevant_files=[path] if path else [],
        repository_snapshot=[path] if path else [],
        primary_language="Python",
        tags=["codesearchnet", "function_level"],
    )


# ---------------------------------------------------------------------------
# Synthetic dataset generation
# ---------------------------------------------------------------------------

SYNTHETIC_TASKS: list[dict[str, Any]] = [
    # File Relevance — Easy
    {
        "task_type": "file_relevance",
        "difficulty": "easy",
        "dataset_source": "synthetic_eval_v1",
        "owner": "octocat",
        "repo": "Hello-World",
        "issue_number": 1,
        "issue_title": "Fix authentication bug in login.py",
        "issue_body": "The login.py file throws a KeyError when the user field is missing.",
        "repository_snapshot": ["login.py", "utils.py", "tests/test_login.py", "README.md"],
        "primary_language": "Python",
        "commit_sha": "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
        "source_url": "https://github.com/octocat/Hello-World/issues/1",
        "dataset_version": "1.0.0",
        "license": "MIT",
        "split": "test",
        "expected_relevant_files": ["login.py", "tests/test_login.py"],
        "tags": ["synthetic", "file_relevance"],
    },
    # File Relevance — Medium
    {
        "task_type": "file_relevance",
        "difficulty": "medium",
        "dataset_source": "synthetic_eval_v1",
        "owner": "facebook",
        "repo": "react",
        "issue_number": 42,
        "issue_title": "useEffect cleanup not called on unmount",
        "issue_body": "When a component unmounts, the cleanup function in useEffect is skipped if setState is called afterwards.",
        "repository_snapshot": [
            "packages/react/src/hooks.js",
            "packages/react-dom/src/ReactFiberHooks.js",
            "packages/react/src/__tests__/hooks.test.js",
            "README.md",
        ],
        "primary_language": "JavaScript",
        "commit_sha": "b8a53e6d8a7c64a511e4f49b4e548238127f8841",
        "source_url": "https://github.com/facebook/react/issues/42",
        "dataset_version": "1.0.0",
        "license": "MIT",
        "split": "test",
        "expected_relevant_files": [
            "packages/react/src/hooks.js",
            "packages/react-dom/src/ReactFiberHooks.js",
        ],
        "tags": ["synthetic", "file_relevance", "javascript"],
    },
    # Issue Tracing — Medium
    {
        "task_type": "issue_tracing",
        "difficulty": "medium",
        "dataset_source": "synthetic_eval_v1",
        "owner": "psf",
        "repo": "requests",
        "issue_number": 6000,
        "issue_title": "Session cookies not persisted across redirects",
        "issue_body": "When following a 301 redirect, cookies set by the first response are dropped by the second request.",
        "repository_snapshot": [
            "requests/sessions.py",
            "requests/adapters.py",
            "requests/cookies.py",
            "tests/test_cookies.py",
            "README.rst",
        ],
        "primary_language": "Python",
        "commit_sha": "a1c43d9b01f91b314f59955a4e4d4e80d8edf999",
        "source_url": "https://github.com/psf/requests/issues/6000",
        "dataset_version": "1.0.0",
        "license": "Apache-2.0",
        "split": "test",
        "expected_relevant_files": ["requests/sessions.py", "requests/cookies.py"],
        "expected_patch_files": ["requests/sessions.py"],
        "tags": ["synthetic", "issue_tracing", "python"],
    },
    # Plan Quality — Hard
    {
        "task_type": "plan_quality",
        "difficulty": "hard",
        "dataset_source": "synthetic_eval_v1",
        "owner": "django",
        "repo": "django",
        "issue_number": 33210,
        "issue_title": "Add support for async views in class-based views",
        "issue_body": "CBVs do not support async def dispatch(), causing SynchronousOnlyOperation errors.",
        "repository_snapshot": [
            "django/views/generic/base.py",
            "django/utils/decorators.py",
            "tests/class_based_views/tests.py",
        ],
        "primary_language": "Python",
        "commit_sha": "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3",
        "source_url": "https://github.com/django/django/issues/33210",
        "dataset_version": "1.0.0",
        "license": "BSD-3-Clause",
        "split": "test",
        "expected_relevant_files": [
            "django/views/generic/base.py",
            "django/utils/decorators.py",
        ],
        "reference_summary": (
            "Modify View.dispatch() to support async handlers and update "
            "decorators to preserve async signatures."
        ),
        "tags": ["synthetic", "plan_quality", "python", "django"],
    },
    # Setup Diagnosis — Easy
    {
        "task_type": "setup_diagnosis",
        "difficulty": "easy",
        "dataset_source": "synthetic_eval_v1",
        "owner": "example",
        "repo": "myproject",
        "issue_number": 0,
        "issue_title": "Setup fails with ModuleNotFoundError",
        "issue_body": "ModuleNotFoundError: No module named 'requests'",
        "expected_diagnosis": "missing_dependency",
        "commit_sha": "0000000000000000000000000000000000000000",
        "source_url": "local://example/myproject",
        "dataset_version": "1.0.0",
        "license": "MIT",
        "split": "test",
        "tags": ["synthetic", "setup_diagnosis"],
    },
    # AI Enrichment — Medium
    {
        "task_type": "ai_enrichment",
        "difficulty": "medium",
        "dataset_source": "synthetic_eval_v1",
        "owner": "pallets",
        "repo": "flask",
        "issue_number": 4800,
        "issue_title": "Add rate limiting middleware",
        "issue_body": "We need a built-in way to rate-limit requests per IP without external libraries.",
        "repository_snapshot": [
            "src/flask/app.py",
            "src/flask/middleware.py",
            "tests/test_app.py",
        ],
        "primary_language": "Python",
        "commit_sha": "f1e2d3c4b5a697887766554433221100aabbccdd",
        "source_url": "https://github.com/pallets/flask/issues/4800",
        "dataset_version": "1.0.0",
        "license": "BSD-3-Clause",
        "split": "test",
        "expected_relevant_files": ["src/flask/app.py"],
        "reference_summary": "Add a rate limiting middleware class to src/flask/middleware.py.",
        "tags": ["synthetic", "ai_enrichment", "flask"],
    },
]


# ---------------------------------------------------------------------------
# DatasetPipeline
# ---------------------------------------------------------------------------

class DatasetPipeline:
    """
    Manages dataset acquisition, validation, and iteration for evaluation.

    Responsibilities:
    - Generate synthetic evaluation sets deterministically (no external deps)
    - Enforce explicit user consent before external dataset acquisition
    - Iterate JSONL samples from local dataset directories boundedly
    - Convert raw records to EvaluationTask instances with full provenance
    - Split dataset tasks at the repository level to prevent cross-split leakage
    """

    def __init__(self, manifest: DatasetManifest, seed: int = 42):
        self._manifest = manifest
        self._seed = seed
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Synthetic generation
    # ------------------------------------------------------------------

    def generate_synthetic(
        self,
        output_dir: Optional[Path] = None,
        seed: Optional[int] = None,
    ) -> list[EvaluationTask]:
        """
        Generate the synthetic evaluation set deterministically.
        Writes tasks as JSONL to output_dir / synthetic_eval_v1 / test.jsonl.
        """
        active_seed = seed if seed is not None else self._seed
        rng = random.Random(active_seed)

        tasks = [EvaluationTask(**t) for t in SYNTHETIC_TASKS]
        # Deterministic shuffle to test order invariance
        rng.shuffle(tasks)

        if output_dir is None:
            output_dir = DATASET_DIR

        dest = output_dir / "synthetic_eval_v1"
        dest.mkdir(parents=True, exist_ok=True)
        jsonl_path = dest / "test.jsonl"

        with jsonl_path.open("w", encoding="utf-8") as fh:
            for task in tasks:
                fh.write(task.model_dump_json() + "\n")

        logger.info("Synthetic dataset written: %s (%d tasks, seed=%d)", jsonl_path, len(tasks), active_seed)

        # Update manifest entry
        src = self._manifest.get("synthetic_eval_v1")
        if src:
            src.local_path = dest
            src.sample_count = len(tasks)
            src.status = DatasetStatus.SIMULATED

        return tasks

    # ------------------------------------------------------------------
    # Repository-level split generator (Leakage Prevention)
    # ------------------------------------------------------------------

    def create_repository_splits(
        self,
        tasks: list[EvaluationTask],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> dict[str, list[EvaluationTask]]:
        """
        Partition tasks into train, validation, and test splits strictly at the
        repository (owner/repo) level. Guarantees that all tasks from any given
        repository remain in exactly one split, eliminating data leakage.
        """
        # Group tasks by repository
        repo_to_tasks: dict[str, list[EvaluationTask]] = {}
        for task in tasks:
            repo_key = f"{task.owner.lower()}/{task.repo.lower()}" if task.owner and task.repo else "misc/misc"
            repo_to_tasks.setdefault(repo_key, []).append(task)

        unique_repos = sorted(list(repo_to_tasks.keys()))
        rng = random.Random(seed)
        rng.shuffle(unique_repos)

        total_repos = len(unique_repos)
        n_train = max(1, int(total_repos * train_ratio))
        n_val = max(1, int(total_repos * val_ratio)) if total_repos > 2 else 0

        train_repos = set(unique_repos[:n_train])
        val_repos = set(unique_repos[n_train : n_train + n_val])
        test_repos = set(unique_repos[n_train + n_val :])

        splits: dict[str, list[EvaluationTask]] = {
            "train": [],
            "validation": [],
            "test": [],
        }

        for repo, rtasks in repo_to_tasks.items():
            if repo in train_repos:
                for t in rtasks:
                    t.split = "train"
                    splits["train"].append(t)
            elif repo in val_repos:
                for t in rtasks:
                    t.split = "validation"
                    splits["validation"].append(t)
            else:
                for t in rtasks:
                    t.split = "test"
                    splits["test"].append(t)

        logger.info(
            "Created repository splits: train=%d tasks (%d repos), val=%d tasks (%d repos), test=%d tasks (%d repos)",
            len(splits["train"]), len(train_repos),
            len(splits["validation"]), len(val_repos),
            len(splits["test"]), len(test_repos),
        )
        return splits

    # ------------------------------------------------------------------
    # Acquisition descriptions & consent gating
    # ------------------------------------------------------------------

    def describe_acquisition(self, source_name: str) -> dict[str, Any]:
        """
        Return step-by-step acquisition instructions for a dataset source.
        Does NOT perform any download.
        """
        source = self._manifest.get(source_name)
        if not source:
            return {"error": f"Unknown source: {source_name}"}

        if source.acquisition_method == AcquisitionMethod.SYNTHETIC:
            return {
                "source": source_name,
                "method": "synthetic",
                "instructions": "Call DatasetPipeline.generate_synthetic() — no download required.",
                "command": None,
                "status": source.status.value,
            }

        if source.status == DatasetStatus.EXCLUDED:
            return {
                "source": source_name,
                "method": source.acquisition_method.value,
                "status": "excluded",
                "instructions": f"Dataset is excluded from download: {source.decision_rationale}",
                "size_hint_mb": source.size_hint_mb,
                "license": source.license,
            }

        if source.acquisition_method == AcquisitionMethod.HUGGINGFACE:
            return {
                "source": source_name,
                "method": "huggingface_datasets",
                "instructions": (
                    f"pip install datasets\n"
                    f"python -c \"from datasets import load_dataset; "
                    f"ds = load_dataset('{source.acquisition_uri}'); "
                    f"ds.save_to_disk('datasets/{source_name}')\""
                ),
                "uri": source.acquisition_uri,
                "size_hint_mb": source.size_hint_mb,
                "license": source.license,
                "split": source.primary_split,
                "command": (
                    f"python -c \"from datasets import load_dataset; "
                    f"ds = load_dataset('{source.acquisition_uri}'); "
                    f"ds.save_to_disk('datasets/{source_name}')\""
                ),
                "status": source.status.value,
            }

        if source.acquisition_method == AcquisitionMethod.GITHUB_API:
            return {
                "source": source_name,
                "method": "github_api",
                "instructions": (
                    "Requires GITHUB_TOKEN. "
                    "Use DatasetPipeline.acquire_github_issues() to fetch live data."
                ),
                "uri": source.acquisition_uri,
                "size_hint_mb": source.size_hint_mb,
                "license": source.license,
                "command": None,
                "status": source.status.value,
            }

        return {
            "source": source_name,
            "method": source.acquisition_method.value,
            "uri": source.acquisition_uri,
            "status": source.status.value,
            "size_hint_mb": source.size_hint_mb,
            "license": source.license,
        }

    def acquire(self, source_name: str, consent: bool = False) -> dict[str, Any]:
        """
        Safely acquire an external dataset with explicit approval constraint.
        Requires consent=True to proceed with any external network download.
        """
        source = self._manifest.get(source_name)
        if not source:
            return {"status": "error", "message": f"Unknown dataset source: {source_name}"}

        if source.acquisition_method == AcquisitionMethod.SYNTHETIC:
            tasks = self.generate_synthetic()
            return {
                "status": "completed",
                "message": "Synthetic evaluation set generated.",
                "tasks_count": len(tasks),
            }

        if source.status == DatasetStatus.EXCLUDED:
            return {
                "status": "excluded",
                "message": f"Dataset '{source_name}' is excluded from download: {source.decision_rationale}",
            }

        if not consent:
            return {
                "status": "consent_required",
                "message": (
                    f"Acquisition of external dataset '{source_name}' ({source.size_hint_mb} MB) "
                    "requires explicit approval. Re-run with consent=True."
                ),
                "acquisition_info": self.describe_acquisition(source_name),
            }

        # Consent granted: provide instructions and return status
        return {
            "status": "consent_granted_pending_deps",
            "message": f"Consent granted for '{source_name}'. External dataset acquisition instructions returned.",
            "acquisition_info": self.describe_acquisition(source_name),
        }

    # ------------------------------------------------------------------
    # JSONL reading (streaming & bounded)
    # ------------------------------------------------------------------

    def iter_samples(
        self, source_name: str, max_samples: Optional[int] = None
    ) -> Iterator[DatasetSample]:
        """
        Iterate over raw JSONL records from a locally available dataset.
        Skips malformed lines with a debug log. Bounded by max_samples.
        """
        source = self._manifest.get(source_name)
        if not source or not source.local_path:
            logger.warning("Dataset '%s' not available locally.", source_name)
            return

        jsonl_files = sorted(source.local_path.glob("**/*.jsonl"))
        count = 0
        for jf in jsonl_files:
            try:
                for line in jf.open(encoding="utf-8"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        yield DatasetSample(source=source_name, raw=record)
                        count += 1
                        if max_samples and count >= max_samples:
                            return
                    except json.JSONDecodeError as exc:
                        logger.debug("Malformed JSONL in %s: %s", jf, exc)
            except OSError as exc:
                logger.warning("Could not read %s: %s", jf, exc)

    def load_tasks(
        self,
        source_name: str,
        max_tasks: Optional[int] = None,
        shuffle: bool = False,
    ) -> list[EvaluationTask]:
        """
        Load EvaluationTask instances from a locally available dataset.
        Skips records that cannot be converted. Bounded by max_tasks.
        """
        tasks: list[EvaluationTask] = []
        for sample in self.iter_samples(source_name, max_samples=max_tasks):
            task = sample.to_task()
            if task:
                tasks.append(task)
            if max_tasks and len(tasks) >= max_tasks:
                break

        if shuffle:
            self._rng.shuffle(tasks)

        logger.info(
            "Loaded %d tasks from '%s' (max=%s)", len(tasks), source_name, max_tasks
        )
        return tasks

    def sample_tasks(
        self,
        source_name: str,
        n: int,
        task_type: Optional[TaskType] = None,
    ) -> list[EvaluationTask]:
        """
        Draw up to n tasks from a source, optionally filtered by type.
        """
        tasks = self.load_tasks(source_name)
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        if len(tasks) <= n:
            return tasks
        return self._rng.sample(tasks, n)

    # ------------------------------------------------------------------
    # GitHub live data (requires token)
    # ------------------------------------------------------------------

    async def acquire_github_issues(
        self,
        github_service: Any,
        repos: list[tuple[str, str]],
        label: str = "good first issue",
        per_repo: int = 20,
    ) -> list[EvaluationTask]:
        """
        Fetch live 'good first issue' samples from GitHub.
        Converts each to a FILE_RELEVANCE EvaluationTask.
        """
        tasks: list[EvaluationTask] = []
        for owner, repo in repos:
            try:
                issues, _ = await github_service.get_issues(
                    owner=owner, repo=repo, state="open",
                    per_page=per_repo, page=1, label=label,
                )
                for raw in issues:
                    tasks.append(EvaluationTask(
                        task_type=TaskType.FILE_RELEVANCE,
                        difficulty=TaskDifficulty.EASY,
                        dataset_source="github_issues_rest",
                        owner=owner,
                        repo=repo,
                        issue_number=raw.get("number", 0),
                        issue_title=raw.get("title", ""),
                        issue_body=raw.get("body") or "",
                        source_url=raw.get("html_url", ""),
                        dataset_version="live",
                        license="Public",
                        split="live",
                        tags=["live", "good_first_issue"],
                    ))
            except Exception as exc:
                logger.warning("Could not fetch issues for %s/%s: %s", owner, repo, exc)

        logger.info("Acquired %d live GitHub issue tasks", len(tasks))
        return tasks

    # ------------------------------------------------------------------
    # Pipeline timing helper
    # ------------------------------------------------------------------

    def timed(self, fn, *args, **kwargs):
        """Run fn(*args, **kwargs) and return (result, elapsed_ms)."""
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        return result, elapsed
