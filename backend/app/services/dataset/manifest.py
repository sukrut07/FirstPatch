"""
FirstPatch AI — Dataset Manifest (Phase 4)

Defines the canonical list of dataset sources used for evaluation.
Each entry describes: name, origin, license, acquisition method,
expected size, and relevance to FirstPatch AI tasks.

No datasets are bundled — the manifest describes *how* to acquire
each dataset and validates what is locally available.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical dataset directory (relative to repo root)
# ---------------------------------------------------------------------------
DATASET_DIR = Path(__file__).resolve().parents[5] / "datasets"


class DatasetStatus(str, Enum):
    """Lifecycle status of a dataset source."""
    AVAILABLE = "available"           # Locally present and validated
    PARTIAL = "partial"               # Partially downloaded
    NOT_DOWNLOADED = "not_downloaded" # Not yet acquired
    UNAVAILABLE = "unavailable"       # Cannot be acquired (license/access)
    SIMULATED = "simulated"           # Synthetic subset present for CI


class AcquisitionMethod(str, Enum):
    """How the dataset is acquired."""
    HUGGINGFACE = "huggingface_datasets"
    HTTP_DOWNLOAD = "http_download"
    GITHUB_API = "github_api"
    SYNTHETIC = "synthetic"


@dataclass
class DatasetSource:
    """Describes one evaluable dataset source."""
    name: str
    display_name: str
    description: str
    license: str
    acquisition_method: AcquisitionMethod
    acquisition_uri: str                     # HF dataset ID or URL
    primary_split: str                       # train / test / validation
    size_hint_mb: float                      # Approximate download size
    relevance_tags: list[str] = field(default_factory=list)
    local_path: Optional[Path] = None        # Where it lives on disk
    status: DatasetStatus = DatasetStatus.NOT_DOWNLOADED
    sample_count: Optional[int] = None       # Records confirmed locally
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "license": self.license,
            "acquisition_method": self.acquisition_method.value,
            "acquisition_uri": self.acquisition_uri,
            "primary_split": self.primary_split,
            "size_hint_mb": self.size_hint_mb,
            "relevance_tags": self.relevance_tags,
            "local_path": str(self.local_path) if self.local_path else None,
            "status": self.status.value,
            "sample_count": self.sample_count,
            "notes": self.notes,
        }


@dataclass
class DatasetManifest:
    """Registry of all datasets relevant to FirstPatch AI evaluation."""
    sources: list[DatasetSource] = field(default_factory=list)

    def get(self, name: str) -> Optional[DatasetSource]:
        """Look up a source by name."""
        return next((s for s in self.sources if s.name == name), None)

    def available(self) -> list[DatasetSource]:
        """Return sources that are locally available."""
        return [
            s for s in self.sources
            if s.status in (DatasetStatus.AVAILABLE, DatasetStatus.SIMULATED)
        ]

    def summary(self) -> dict[str, Any]:
        total = len(self.sources)
        avail = len(self.available())
        return {
            "total_sources": total,
            "available": avail,
            "not_downloaded": len([s for s in self.sources if s.status == DatasetStatus.NOT_DOWNLOADED]),
            "simulated": len([s for s in self.sources if s.status == DatasetStatus.SIMULATED]),
            "sources": [s.to_dict() for s in self.sources],
        }


def _build_canonical_manifest() -> DatasetManifest:
    """
    Build the canonical dataset manifest.

    Datasets are described but NOT downloaded here — download is
    handled by DatasetPipeline.acquire().
    """
    sources = [
        DatasetSource(
            name="codesearchnet_python",
            display_name="CodeSearchNet (Python)",
            description=(
                "~500K Python functions with docstrings from GitHub. "
                "Used for code understanding, function-to-docstring alignment, "
                "and file relevance scoring."
            ),
            license="CC BY 4.0",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="code_search_net",
            primary_split="train",
            size_hint_mb=400,
            relevance_tags=["code_understanding", "file_relevance", "python"],
            notes="HuggingFace: datasets.load_dataset('code_search_net', 'python')",
        ),
        DatasetSource(
            name="repobench_retrieval",
            display_name="RepoBench (Retrieval)",
            description=(
                "Repository-level code completion benchmark with cross-file context. "
                "Used to evaluate how well FirstPatch AI identifies relevant files "
                "across a codebase."
            ),
            license="MIT",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="Fsoft-AIC/RepoExec",
            primary_split="test",
            size_hint_mb=150,
            relevance_tags=["file_retrieval", "cross_file", "repository_level"],
            notes="Evaluates cross-file file identification accuracy.",
        ),
        DatasetSource(
            name="swe_bench_lite",
            display_name="SWE-bench Lite",
            description=(
                "300 real GitHub issues paired with verified patches from 11 OSS projects. "
                "Used to evaluate issue-to-code traceability and plan accuracy."
            ),
            license="MIT",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="princeton-nlp/SWE-bench_Lite",
            primary_split="test",
            size_hint_mb=5,
            relevance_tags=["issue_tracing", "patch_validation", "real_world"],
            notes=(
                "Ground truth: issue text → correct file + patch. "
                "FirstPatch maps issue → files; compare against SWE-bench oracle."
            ),
        ),
        DatasetSource(
            name="github_good_first_issues",
            display_name="Good First Issues (GitHub API)",
            description=(
                "Live 'good first issue' samples fetched via GitHub API from popular "
                "OSS repositories. Demonstrates real-time data acquisition and "
                "issue matching quality."
            ),
            license="Public",
            acquisition_method=AcquisitionMethod.GITHUB_API,
            acquisition_uri="https://api.github.com/search/issues?q=label:good-first-issue+state:open",
            primary_split="live",
            size_hint_mb=1,
            relevance_tags=["issue_matching", "beginner_friendly", "live"],
            notes="Requires GITHUB_TOKEN. Rate-limited to 1000 results per query.",
        ),
        DatasetSource(
            name="synthetic_eval_v1",
            display_name="Synthetic Evaluation Set v1 (Built-in)",
            description=(
                "A small, deterministically-generated evaluation set built into "
                "FirstPatch AI. Used for CI, offline testing, and baseline checks "
                "without any external downloads."
            ),
            license="MIT",
            acquisition_method=AcquisitionMethod.SYNTHETIC,
            acquisition_uri="local://synthetic",
            primary_split="test",
            size_hint_mb=0.01,
            relevance_tags=["ci", "offline", "baseline", "all_tasks"],
            notes="Always available. Generated by DatasetPipeline.generate_synthetic().",
        ),
    ]
    return DatasetManifest(sources=sources)


def load_dataset_manifest() -> DatasetManifest:
    """
    Return the canonical manifest with local availability probed.
    Updates each source's status and sample_count based on disk state.
    """
    manifest = _build_canonical_manifest()

    for source in manifest.sources:
        if source.acquisition_method == AcquisitionMethod.SYNTHETIC:
            source.status = DatasetStatus.SIMULATED
            source.local_path = DATASET_DIR / source.name
            continue

        candidate = DATASET_DIR / source.name
        if candidate.exists():
            # Count JSONL records
            jsonl_files = list(candidate.glob("**/*.jsonl"))
            count = 0
            for jf in jsonl_files:
                try:
                    count += sum(1 for line in jf.open(encoding="utf-8") if line.strip())
                except OSError:
                    pass
            source.local_path = candidate
            source.sample_count = count
            source.status = DatasetStatus.AVAILABLE if count > 0 else DatasetStatus.PARTIAL
        else:
            source.status = DatasetStatus.NOT_DOWNLOADED

    return manifest
