"""
FirstPatch AI — Dataset Manifest (Phase 4)

Defines the canonical list of dataset sources used for evaluation.
Each entry describes: name, origin, license, acquisition method,
expected size, relevance to FirstPatch AI tasks, provenance, and governance decision.

No datasets are bundled — the manifest describes *how* to acquire
each dataset, governance decisions (supported, deferred, excluded),
and validates what is locally available.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical dataset directory (relative to repo root)
# parents[4] points to s:\HacktoberDYP (the workspace root)
# ---------------------------------------------------------------------------
DATASET_DIR = Path(__file__).resolve().parents[4] / "datasets"


class DatasetStatus(str, Enum):
    """Lifecycle / governance status of a dataset source."""
    AVAILABLE = "available"           # Locally present and validated
    PARTIAL = "partial"               # Partially downloaded / empty
    NOT_DOWNLOADED = "not_downloaded" # Not yet acquired
    UNAVAILABLE = "unavailable"       # Cannot be acquired (license/access)
    SIMULATED = "simulated"           # Synthetic subset present for CI
    SUPPORTED = "supported"           # Schema/converter implemented; ready for bounded ingestion
    DEFERRED = "deferred"             # Planned but deferred due to size/compute/environment needs
    EXCLUDED = "excluded"             # Excluded from wholesale acquisition (license or multi-TB size)


class AcquisitionMethod(str, Enum):
    """How the dataset is acquired."""
    HUGGINGFACE = "huggingface_datasets"
    HTTP_DOWNLOAD = "http_download"
    GITHUB_API = "github_api"
    SYNTHETIC = "synthetic"
    GIT_CLONE = "git_clone"


@dataclass
class DatasetSource:
    """Describes one evaluable dataset source with provenance and governance metadata."""
    name: str
    display_name: str
    description: str
    license: str
    acquisition_method: AcquisitionMethod
    acquisition_uri: str                     # HF dataset ID, URL, or API endpoint
    primary_split: str                       # train / test / validation / live
    size_hint_mb: float                      # Approximate download size in MB
    relevance_tags: list[str] = field(default_factory=list)
    canonical_url: str = ""
    version_or_snapshot: str = ""
    intended_task: str = ""
    provenance_details: str = ""
    privacy_redistribution_notes: str = ""
    acquisition_requirements: str = ""
    decision_status: str = "supported"       # supported | deferred | excluded | available
    decision_rationale: str = ""
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
            "canonical_url": self.canonical_url,
            "version_or_snapshot": self.version_or_snapshot,
            "intended_task": self.intended_task,
            "provenance_details": self.provenance_details,
            "privacy_redistribution_notes": self.privacy_redistribution_notes,
            "acquisition_requirements": self.acquisition_requirements,
            "decision_status": self.decision_status,
            "decision_rationale": self.decision_rationale,
            "local_path": str(self.local_path) if self.local_path else None,
            "status": self.status.value,
            "sample_count": self.sample_count,
            "notes": self.notes,
        }


@dataclass
class DatasetManifest:
    """Registry of all candidate datasets relevant to FirstPatch AI evaluation."""
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
            "supported": len([s for s in self.sources if s.status == DatasetStatus.SUPPORTED]),
            "deferred": len([s for s in self.sources if s.status == DatasetStatus.DEFERRED]),
            "excluded": len([s for s in self.sources if s.status == DatasetStatus.EXCLUDED]),
            "sources": [s.to_dict() for s in self.sources],
        }


def _build_canonical_manifest() -> DatasetManifest:
    """
    Build the canonical dataset manifest covering all candidate datasets.

    Datasets are described but NOT downloaded here — download requires
    explicit consent and is handled by DatasetPipeline.
    """
    sources = [
        # 1. CodeSearchNet (Python)
        DatasetSource(
            name="codesearchnet_python",
            display_name="CodeSearchNet (Python)",
            description=(
                "~500K Python functions with docstrings from open-source GitHub repositories. "
                "Used for code understanding, function-to-docstring alignment, "
                "and file relevance scoring."
            ),
            license="CC BY 4.0 (compilation); individual repo OSS licenses apply",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="code_search_net",
            primary_split="train",
            size_hint_mb=400,
            relevance_tags=["code_understanding", "file_relevance", "python"],
            canonical_url="https://github.com/github/CodeSearchNet",
            version_or_snapshot="v1.0 (python subset)",
            intended_task="Code-to-docstring semantic alignment and file relevance ranking",
            provenance_details="Extracted from public GitHub repositories with permissive licenses by GitHub/SRI.",
            privacy_redistribution_notes="Dataset compilation licensed under CC BY 4.0; underlying repositories retain original author licenses and copyrights.",
            acquisition_requirements="HuggingFace datasets library; ~400 MB download; requires user consent.",
            decision_status="supported",
            decision_rationale="Supported with conversion adapter in pipeline. Wholesale download deferred to avoid large bandwidth overhead during CI.",
            status=DatasetStatus.SUPPORTED,
            notes="HuggingFace: datasets.load_dataset('code_search_net', 'python')",
        ),

        # 2. RepoBench Python v1.1 (Retrieval)
        DatasetSource(
            name="repobench_retrieval",
            display_name="RepoBench (Retrieval - Python v1.1)",
            description=(
                "Repository-level code retrieval and completion benchmark across multi-file Python contexts. "
                "Used to evaluate cross-file dependency understanding and file retrieval."
            ),
            license="Apache-2.0",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="Fsoft-AIC/RepoExec",
            primary_split="test",
            size_hint_mb=150,
            relevance_tags=["file_retrieval", "cross_file", "repository_level", "python"],
            canonical_url="https://github.com/Leolty/repobench",
            version_or_snapshot="v1.1 (Python)",
            intended_task="Cross-file context retrieval and repository-level code navigation",
            provenance_details="Curated by researchers from GitHub repositories created between 2022-2023.",
            privacy_redistribution_notes="Contains code snippets from public GitHub repos. Verify attribution requirements for commercial redistributions.",
            acquisition_requirements="HuggingFace datasets library or git clone; ~150 MB.",
            decision_status="supported",
            decision_rationale="Core benchmark for cross-file retrieval evaluation. Supported in metric architecture; offline simulated subset available.",
            status=DatasetStatus.SUPPORTED,
            notes="Evaluates cross-file file identification accuracy.",
        ),

        # 3. RepoBench Java v1.1
        DatasetSource(
            name="repobench_java_v11",
            display_name="RepoBench (Java v1.1)",
            description=(
                "Repository-level code retrieval and completion benchmark for Java projects. "
                "Evaluates cross-file imports and class references in Java codebases."
            ),
            license="Apache-2.0",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="Fsoft-AIC/RepoExec",
            primary_split="test",
            size_hint_mb=180,
            relevance_tags=["file_retrieval", "cross_file", "java"],
            canonical_url="https://github.com/Leolty/repobench",
            version_or_snapshot="v1.1 (Java)",
            intended_task="Cross-file context retrieval in Java repositories",
            provenance_details="Curated from public Java repositories on GitHub.",
            privacy_redistribution_notes="Public repository code subject to upstream licenses.",
            acquisition_requirements="HuggingFace datasets library; ~180 MB.",
            decision_status="deferred",
            decision_rationale="Deferred because FirstPatch AI currently specializes in Python and JavaScript/TypeScript stacks. Java support is on roadmap.",
            status=DatasetStatus.DEFERRED,
            notes="Deferred pending Java language parser and AST intelligence support.",
        ),

        # 4. The Stack Dedup
        DatasetSource(
            name="the_stack_dedup",
            display_name="The Stack Dedup",
            description=(
                "3+ TB deduplicated dataset of permissively licensed source code in 358 languages. "
                "Designed for pre-training code models."
            ),
            license="Permissive licenses compilation; individual repo licenses apply; respects opt-outs",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="bigcode/the-stack-dedup",
            primary_split="train",
            size_hint_mb=3000000,
            relevance_tags=["pretraining", "massive_corpus", "multi_language"],
            canonical_url="https://huggingface.co/datasets/bigcode/the-stack-dedup",
            version_or_snapshot="v1.2",
            intended_task="Foundation code model training",
            provenance_details="BigCode project crawl from public GitHub repositories with license filtering and author opt-out.",
            privacy_redistribution_notes="Strict author opt-out compliance required. Wholesale redistribution is prohibited without opt-out indexing.",
            acquisition_requirements="Requires HuggingFace gated dataset access and multi-terabyte storage.",
            decision_status="excluded",
            decision_rationale="Excluded from wholesale acquisition due to multi-TB storage requirements and irrelevance to lightweight mentor evaluation.",
            status=DatasetStatus.EXCLUDED,
            notes="Excluded from local downloads; wholesale download violates operational constraints.",
        ),

        # 5. GitHub Issues REST API (Good First Issues)
        DatasetSource(
            name="github_good_first_issues",
            display_name="Good First Issues (GitHub API)",
            description=(
                "Live GitHub REST API for searching and fetching issue metadata, "
                "labels ('good first issue'), comments, and state from public repositories."
            ),
            license="Public",
            acquisition_method=AcquisitionMethod.GITHUB_API,
            acquisition_uri="https://api.github.com/search/issues",
            primary_split="live",
            size_hint_mb=5,
            relevance_tags=["issue_matching", "beginner_friendly", "live"],
            canonical_url="https://docs.github.com/en/rest/issues",
            version_or_snapshot="API Version 2022-11-28",
            intended_task="Live good-first-issue discovery and issue-to-code mapping",
            provenance_details="Fetched directly from target public repositories via GitHub REST API.",
            privacy_redistribution_notes="No private repositories queried. User PAT never leaked or persisted in dataset caches.",
            acquisition_requirements="Optional GITHUB_TOKEN for higher rate limits (5,000 req/hr vs 60 req/hr).",
            decision_status="supported",
            decision_rationale="Core runtime integration for FirstPatch AI. Live data acquired boundedly on demand.",
            status=DatasetStatus.SUPPORTED,
            notes="Active in application runtime. Bounded queries with pagination.",
        ),

        # 6. GitHub Pull Requests REST API
        DatasetSource(
            name="github_pull_requests_rest",
            display_name="GitHub Pull Requests REST API",
            description=(
                "Live GitHub REST API for fetching PR metadata, changed files, diffs, "
                "and CI checks to evaluate PR summary and contribution verification."
            ),
            license="GitHub API Terms of Service; repository content subject to project licenses",
            acquisition_method=AcquisitionMethod.GITHUB_API,
            acquisition_uri="https://api.github.com/repos/{owner}/{repo}/pulls",
            primary_split="live",
            size_hint_mb=5,
            relevance_tags=["pr_summary", "diff_analysis", "live"],
            canonical_url="https://docs.github.com/en/rest/pulls",
            version_or_snapshot="API Version 2022-11-28",
            intended_task="PR summary generation, diff inspection, and test command discovery",
            provenance_details="Fetched dynamically from public GitHub repositories.",
            privacy_redistribution_notes="Public PR data only. Strict redaction of secrets in diffs and comments.",
            acquisition_requirements="Optional GITHUB_TOKEN.",
            decision_status="supported",
            decision_rationale="Supported in GitHubService and verification pipelines.",
            status=DatasetStatus.SUPPORTED,
            notes="Active in application runtime for PR summary preparation.",
        ),

        # 7. SWE-bench (Full)
        DatasetSource(
            name="swe_bench_full",
            display_name="SWE-bench (Full)",
            description=(
                "2,294 software engineering problems extracted from 12 popular Python repositories. "
                "Requires dynamic Docker execution environments to evaluate patch resolution."
            ),
            license="MIT (benchmark harness); underlying repos carry their respective OSS licenses",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="princeton-nlp/SWE-bench",
            primary_split="test",
            size_hint_mb=250000,
            relevance_tags=["end_to_end", "patch_resolution", "docker_required"],
            canonical_url="https://github.com/princeton-nlp/SWE-bench",
            version_or_snapshot="v1.0 (2,294 instances)",
            intended_task="Full end-to-end bug resolution and dynamic test execution",
            provenance_details="Curated by Princeton NLP from resolved GitHub issues and PRs across 12 Python projects.",
            privacy_redistribution_notes="Benchmark harness is MIT; each repository snapshot is subject to its original open-source license.",
            acquisition_requirements="Requires Docker runtime with ~250 GB storage for complete environment container images.",
            decision_status="deferred",
            decision_rationale="Deferred due to 250 GB Docker container storage requirement. SWE-bench Lite is used instead for static evaluation.",
            status=DatasetStatus.DEFERRED,
            notes="Full execution deferred; SWE-bench Lite provides identical evaluation signal for file retrieval without massive image downloads.",
        ),

        # 8. SWE-bench Lite
        DatasetSource(
            name="swe_bench_lite",
            display_name="SWE-bench Lite",
            description=(
                "300 curated real GitHub issues paired with verified patches from 11 OSS projects. "
                "Used to evaluate issue-to-code traceability, file localization, and plan accuracy."
            ),
            license="MIT",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="princeton-nlp/SWE-bench_Lite",
            primary_split="test",
            size_hint_mb=5,
            relevance_tags=["issue_tracing", "patch_validation", "real_world"],
            canonical_url="https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite",
            version_or_snapshot="v1.0 (300 instances)",
            intended_task="Issue-to-code traceability and expected relevant files oracle",
            provenance_details="Subset of SWE-bench selected for solvable, self-contained evaluation tasks.",
            privacy_redistribution_notes="Evaluation metadata is MIT licensed; underlying repository code follows original OSS terms.",
            acquisition_requirements="HuggingFace datasets library; ~5 MB metadata download.",
            decision_status="supported",
            decision_rationale="Primary external benchmark for issue tracing. Converter implemented in pipeline (`_swe_bench_to_task`).",
            status=DatasetStatus.SUPPORTED,
            notes="Ground truth: issue text -> correct file + patch. Compare predicted files against SWE-bench oracle.",
        ),

        # 9. SWE-Gym
        DatasetSource(
            name="swe_gym",
            display_name="SWE-Gym",
            description=(
                "Reinforcement learning and agentic environment benchmark for software engineering agents. "
                "Provides interactive environments for multi-step agent tool use."
            ),
            license="MIT",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="SWE-Gym/SWE-Gym",
            primary_split="train",
            size_hint_mb=100000,
            relevance_tags=["agentic_rl", "interactive_environment", "docker_required"],
            canonical_url="https://github.com/SWE-Gym/SWE-Gym",
            version_or_snapshot="v1.0",
            intended_task="Multi-turn agent interaction and tool-use policy optimization",
            provenance_details="Constructed for training and evaluating interactive SWE agents.",
            privacy_redistribution_notes="Container images encapsulate underlying repository code under various OSS licenses.",
            acquisition_requirements="Docker daemon with 100+ GB available container cache.",
            decision_status="deferred",
            decision_rationale="Deferred because interactive RL training is out of scope for Phase 4 quality gate audit.",
            status=DatasetStatus.DEFERRED,
            notes="Deferred; interactive RL training not required for deterministic mentor evaluation.",
        ),

        # 10. BugsInPy
        DatasetSource(
            name="bugsinpy",
            display_name="BugsInPy",
            description=(
                "493 real bugs extracted from 17 real-world Python projects with reproducible tests. "
                "Enables fine-grained bug localization and test verification."
            ),
            license="MIT (benchmark harness); target Python projects retain original licenses",
            acquisition_method=AcquisitionMethod.GIT_CLONE,
            acquisition_uri="https://github.com/soarsmu/BugsInPy.git",
            primary_split="test",
            size_hint_mb=200,
            relevance_tags=["bug_localization", "python", "isolated_testing"],
            canonical_url="https://github.com/soarsmu/BugsInPy",
            version_or_snapshot="v1.0 (493 bugs)",
            intended_task="Python bug localization, test failure diagnosis, and patch verification",
            provenance_details="Extracted from historical commits of popular Python projects (e.g. pandas, tornado, spacy).",
            privacy_redistribution_notes="Underlying code belongs to respective upstream projects with MIT, BSD, or Apache licenses.",
            acquisition_requirements="Git clone of repo; ~200 MB; Python 3.x environment.",
            decision_status="supported",
            decision_rationale="Supported candidate for Python bug localization. Schema can be converted to EvaluationTask format.",
            status=DatasetStatus.SUPPORTED,
            notes="Excellent fit for Python repository intelligence testing.",
        ),

        # 11. CommitPack
        DatasetSource(
            name="commitpack",
            display_name="CommitPack",
            description=(
                "4 TB compilation of high-quality commits with commit messages in 350+ languages. "
                "Used to evaluate intent-to-diff alignment."
            ),
            license="Compilation filtered for permissive licenses; underlying commits retain author licenses",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="bigcode/commitpackft",
            primary_split="train",
            size_hint_mb=4000000,
            relevance_tags=["commits", "intent_to_diff", "multi_language"],
            canonical_url="https://huggingface.co/datasets/bigcode/commitpackft",
            version_or_snapshot="v1.0",
            intended_task="Commit message understanding and change description synthesis",
            provenance_details="Curated from GitHub public commit histories by BigCode.",
            privacy_redistribution_notes="Subject to individual commit author licenses and BigCode opt-out registry.",
            acquisition_requirements="Multi-terabyte storage; gated HuggingFace dataset.",
            decision_status="excluded",
            decision_rationale="Excluded from wholesale acquisition due to multi-TB size. Bounded query sampling may be approved in future phases.",
            status=DatasetStatus.EXCLUDED,
            notes="Wholesale download prohibited by operational constraints.",
        ),

        # 12. helmo/github-issues
        DatasetSource(
            name="helmo_github_issues",
            display_name="helmo/github-issues",
            description=(
                "Large collection of GitHub issues scraped across public repositories. "
                "Useful for issue label prediction and issue text categorization."
            ),
            license="CC0 / Public Domain compilation; original issue content retains author copyright",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="helmo/github-issues",
            primary_split="train",
            size_hint_mb=1200,
            relevance_tags=["issue_classification", "labels", "text_mining"],
            canonical_url="https://huggingface.co/datasets/helmo/github-issues",
            version_or_snapshot="v1.0",
            intended_task="Issue text classification and difficulty scoring",
            provenance_details="Scraped from public GitHub issue trackers.",
            privacy_redistribution_notes="Public issue text; may contain user handles and issue submitter names.",
            acquisition_requirements="HuggingFace datasets library; ~1.2 GB download.",
            decision_status="deferred",
            decision_rationale="Deferred because live GitHub Issues REST API provides fresher, repository-specific issues without 1.2 GB download overhead.",
            status=DatasetStatus.DEFERRED,
            notes="Deferred in favor of live GitHub API and SWE-bench Lite.",
        ),

        # 13. SWE-Review-Chat
        DatasetSource(
            name="swe_review_chat",
            display_name="SWE-Review-Chat",
            description=(
                "Dataset of code review discussions, comments, and reviewer feedback loops on GitHub pull requests. "
                "Used to evaluate mentor PR commentary and review assistance."
            ),
            license="Apache-2.0 / MIT",
            acquisition_method=AcquisitionMethod.HUGGINGFACE,
            acquisition_uri="m-a-p/SWE-Review-Chat",
            primary_split="test",
            size_hint_mb=50,
            relevance_tags=["code_review", "pull_requests", "mentorship"],
            canonical_url="https://huggingface.co/datasets/m-a-p/SWE-Review-Chat",
            version_or_snapshot="v1.0",
            intended_task="PR review comment generation and reviewer feedback guidance",
            provenance_details="Curated from public pull request code review discussions on GitHub.",
            privacy_redistribution_notes="Public review discussions. Redact sensitive tokens and credentials.",
            acquisition_requirements="HuggingFace datasets library; ~50 MB download.",
            decision_status="supported",
            decision_rationale="Supported for future PR review commentary benchmark tasks. Lightweight footprint.",
            status=DatasetStatus.SUPPORTED,
            notes="Targeted for mentor PR review guidance evaluation.",
        ),

        # 14. Synthetic Evaluation Set v1 (Built-in)
        DatasetSource(
            name="synthetic_eval_v1",
            display_name="Synthetic Evaluation Set v1 (Built-in)",
            description=(
                "A curated, deterministically-generated evaluation set built directly into "
                "FirstPatch AI. Used for CI, offline testing, and baseline checks "
                "without any external downloads or credentials."
            ),
            license="MIT (FirstPatch AI)",
            acquisition_method=AcquisitionMethod.SYNTHETIC,
            acquisition_uri="local://synthetic",
            primary_split="test",
            size_hint_mb=0.01,
            relevance_tags=["ci", "offline", "baseline", "all_tasks"],
            canonical_url="local://firstpatch_ai/synthetic_eval_v1",
            version_or_snapshot="v1.0.0",
            intended_task="Deterministic CI baseline testing covering all 5 evaluation task types",
            provenance_details="Authored natively for FirstPatch AI test harness; sanitized mock repository contexts.",
            privacy_redistribution_notes="Free of PII, secrets, and external proprietary code. MIT licensed.",
            acquisition_requirements="None. Generated on-the-fly via DatasetPipeline.generate_synthetic().",
            decision_status="available",
            decision_rationale="Always available; guaranteed offline execution for test suite and reproducible benchmarks.",
            status=DatasetStatus.SIMULATED,
            sample_count=10,
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
            if count > 0:
                source.status = DatasetStatus.AVAILABLE
            elif source.status not in (DatasetStatus.EXCLUDED, DatasetStatus.DEFERRED):
                source.status = DatasetStatus.PARTIAL
        else:
            # Preserve governance status if already deferred or excluded
            if source.status not in (DatasetStatus.EXCLUDED, DatasetStatus.DEFERRED, DatasetStatus.SUPPORTED):
                source.status = DatasetStatus.NOT_DOWNLOADED

    return manifest
