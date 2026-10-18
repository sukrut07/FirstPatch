"""
Phase 4 Quality Gate Audit Tests

Covers:
1. Hand-calculated metric fixtures (Precision, Recall, F1, Recall@k, Hit@k, MRR, MAP,
   Evidence-Validity Rate, Unsupported-Claim Rate, False Verification-Pass Rate).
2. Manifest coverage: All 12 candidate datasets + synthetic set with governance decisions.
3. Ingestion & Validation: Secret filtering, path traversal protection, split leakage prevention.
4. Mode Separation: Deterministic baseline vs. live AI evaluation vs. mock AI.
5. End-to-End Workflow:
   Repository snapshot -> Issue retrieval -> AST analysis -> Evidence bundle ->
   Contribution plan -> Verification request (Docker unavailable handling) -> PR summary.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    AIProviderStatus,
    ContributionPlan,
    DiagnosticRequest,
    GitHubIssue,
    PlanRequest,
    RepositoryOverview,
)
from app.schemas.verification import (
    ExecutionStatus,
    RuntimeProfile,
    VerificationInfrastructureHealth,
    VerificationRunRecord,
    VerificationRunRequest,
    VerificationTestCounts,
)
from app.services.agent.orchestrator import AgentOrchestrationResult, FirstPatchAgentOrchestrator
from app.services.benchmark.evaluator import BenchmarkEvaluator, EvaluationMode
from app.services.benchmark.metrics import (
    FileRetrievalMetrics,
    compute_diagnosis_metrics,
    compute_evidence_metrics,
    compute_false_verification_pass_rate,
    compute_file_retrieval_metrics,
    compute_mean_average_precision,
    compute_plan_metrics,
)
from app.services.benchmark.result_store import BenchmarkResultStore, BenchmarkRun
from app.services.dataset.manifest import (
    AcquisitionMethod,
    DatasetManifest,
    DatasetSource,
    DatasetStatus,
    load_dataset_manifest,
)
from app.services.dataset.pipeline import DatasetPipeline
from app.services.dataset.task_schema import EvaluationTask, TaskDifficulty, TaskType
from app.services.dataset.validator import DatasetValidator
from app.services.mentor.ai_provider import (
    AIResponse,
    BaseAIProvider,
    DeterministicFallbackProvider,
)
from app.services.mentor.planner import MentorService
from app.services.mentor.pr_summary import PRSummaryService
from app.services.verification.runner import BaseExecutionDriver
from app.services.verification.service import IsolatedVerificationService
from app.services.verification.store import VerificationRecordStore


# ---------------------------------------------------------------------------
# 1. Hand-Calculated Metric Fixtures
# ---------------------------------------------------------------------------

class TestHandCalculatedMetrics:
    """Verifies all metrics against exact, by-hand calculated values."""

    def test_file_retrieval_perfect_match(self):
        # Expected: ["a.py", "b.py"]
        # Predicted: ["a.py", "b.py"]
        # TP = 2, P = 1.0, R = 1.0, F1 = 1.0, MRR = 1.0, AP = 1.0
        m = compute_file_retrieval_metrics(["a.py", "b.py"], ["a.py", "b.py"])
        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.f1 == 1.0
        assert m.mrr == 1.0
        assert m.average_precision == 1.0
        assert m.recall_at_1 == 0.5
        assert m.recall_at_3 == 1.0
        assert m.hit_at_1 is True

    def test_file_retrieval_interleaved_partial_match(self):
        # Expected: ["a.py", "b.py"] (|E| = 2)
        # Predicted: ["c.py", "a.py", "d.py", "b.py"] (|P| = 4)
        # k=1: c.py -> miss. P@1=0, R@1=0
        # k=2: a.py -> hit.  P@2=1/2=0.5, R@2=1/2=0.5
        # k=3: d.py -> miss. P@3=1/3,     R@3=0.5
        # k=4: b.py -> hit.  P@4=2/4=0.5, R@4=2/2=1.0
        # TP = 2
        # Precision = 2/4 = 0.5
        # Recall = 2/2 = 1.0
        # F1 = 2 * 0.5 * 1.0 / (0.5 + 1.0) = 1.0 / 1.5 = 2/3 = 0.666666...
        # MRR = 1 / 2 = 0.5 (first hit at index 2)
        # AP = (P@2 + P@4) / 2 = (0.5 + 0.5) / 2 = 0.5
        m = compute_file_retrieval_metrics(
            predicted=["c.py", "a.py", "d.py", "b.py"],
            expected=["a.py", "b.py"],
        )
        assert m.tp == 2
        assert m.precision == 0.5
        assert m.recall == 1.0
        assert round(m.f1, 4) == 0.6667
        assert m.mrr == 0.5
        assert m.average_precision == 0.5
        assert m.hit_at_1 is False
        assert m.hit_at_3 is True
        assert m.recall_at_1 == 0.0
        assert m.recall_at_3 == 0.5
        assert m.recall_at_5 == 1.0

    def test_file_retrieval_completely_disjoint(self):
        m = compute_file_retrieval_metrics(["x.py", "y.py"], ["a.py", "b.py"])
        assert m.tp == 0
        assert m.precision == 0.0
        assert m.recall == 0.0
        assert m.f1 == 0.0
        assert m.mrr == 0.0
        assert m.average_precision == 0.0
        assert m.hit_at_1 is False
        assert m.hit_at_3 is False
        assert m.hit_at_5 is False

    def test_file_retrieval_empty_predictions(self):
        m = compute_file_retrieval_metrics([], ["a.py"])
        assert m.precision == 0.0
        assert m.recall == 0.0
        assert m.f1 == 0.0
        assert m.mrr == 0.0
        assert m.average_precision == 0.0

    def test_file_retrieval_empty_expected(self):
        m = compute_file_retrieval_metrics(["a.py"], [])
        assert m.precision == 0.0
        assert m.recall == 0.0
        assert m.f1 == 0.0

    def test_mean_average_precision(self):
        # Query 1 AP = 1.0, Query 2 AP = 0.5
        # MAP = 0.75
        assert compute_mean_average_precision([1.0, 0.5]) == 0.75
        assert compute_mean_average_precision([]) == 0.0

    def test_evidence_validity_and_unsupported_claim_rate(self):
        # Cited 4 files; 3 exist in known repo files, 1 is a hallucination
        cited = ["app/main.py", "app/routes.py", "app/utils.py", "app/hallucinated.py"]
        known = ["app/main.py", "app/routes.py", "app/utils.py", "tests/test_main.py"]
        ev = compute_evidence_metrics(cited, known)
        assert ev.total_citations == 4
        assert ev.valid_citations == 3
        assert ev.evidence_validity_rate == 0.75
        assert ev.unsupported_claim_rate == 0.25

    def test_evidence_metrics_zero_citations(self):
        ev = compute_evidence_metrics([], ["app/main.py"])
        assert ev.evidence_validity_rate == 1.0
        assert ev.unsupported_claim_rate == 0.0

    def test_false_verification_pass_rate(self):
        # 4 verification runs:
        # 1. Genuine pass (10 tests ran, 0 failed, driver available)
        # 2. False pass: reported PASSED but 0 tests ran
        # 3. Genuine fail: reported FAILED
        # 4. False pass: reported PASSED but driver was UNAVAILABLE
        runs = [
            {"status": "PASSED", "test_counts": {"total": 10, "failed": 0}, "driver_status": "AVAILABLE"},
            {"status": "PASSED", "test_counts": {"total": 0, "failed": 0}, "driver_status": "AVAILABLE"},
            {"status": "FAILED", "test_counts": {"total": 10, "failed": 1}, "driver_status": "AVAILABLE"},
            {"status": "PASSED", "test_counts": {"total": 5, "failed": 0}, "driver_status": "UNAVAILABLE"},
        ]
        rate = compute_false_verification_pass_rate(runs)
        assert rate == 0.50  # 2 false passes out of 4


# ---------------------------------------------------------------------------
# 2. Manifest Coverage for all 12 Candidate Sources
# ---------------------------------------------------------------------------

class TestManifestComprehensiveCoverage:
    """Confirms all candidate datasets from the quality gate audit are registered."""

    EXPECTED_CANDIDATES = [
        "codesearchnet_python",
        "repobench_retrieval",
        "repobench_java_v11",
        "the_stack_dedup",
        "github_good_first_issues",
        "github_pull_requests_rest",
        "swe_bench_full",
        "swe_bench_lite",
        "swe_gym",
        "bugsinpy",
        "commitpack",
        "helmo_github_issues",
        "swe_review_chat",
        "synthetic_eval_v1",
    ]

    def test_all_12_candidate_datasets_registered(self):
        manifest = load_dataset_manifest()
        registered = {s.name for s in manifest.sources}
        for candidate in self.EXPECTED_CANDIDATES:
            assert candidate in registered, f"Missing candidate dataset: {candidate}"

    def test_candidate_provenance_and_decisions_documented(self):
        manifest = load_dataset_manifest()
        for s in manifest.sources:
            assert s.canonical_url != "", f"{s.name} missing canonical_url"
            assert s.version_or_snapshot != "", f"{s.name} missing version_or_snapshot"
            assert s.intended_task != "", f"{s.name} missing intended_task"
            assert s.provenance_details != "", f"{s.name} missing provenance_details"
            assert s.decision_rationale != "", f"{s.name} missing decision_rationale"
            assert s.decision_status in ("supported", "deferred", "excluded", "available")

    def test_the_stack_and_commitpack_excluded_from_wholesale_download(self):
        manifest = load_dataset_manifest()
        stack = manifest.get("the_stack_dedup")
        assert stack.status == DatasetStatus.EXCLUDED
        assert stack.decision_status == "excluded"

        commitpack = manifest.get("commitpack")
        assert commitpack.status == DatasetStatus.EXCLUDED
        assert commitpack.decision_status == "excluded"


# ---------------------------------------------------------------------------
# 3. Ingestion & Validation Safety
# ---------------------------------------------------------------------------

class TestIngestionAndValidationSafety:
    """Tests secret filtering, duplicate checking, and split leakage protection."""

    def test_secret_detection_flags_credentials(self, tmp_path):
        jsonl = tmp_path / "leaked.jsonl"
        # Record with an exposed GitHub Personal Access Token
        bad_record = {
            "task_type": "file_relevance",
            "issue_title": "Fix with secret token ghp_111122223333444455556666777788889999",
            "expected_relevant_files": ["login.py"],
            "dataset_source": "synthetic_eval_v1",
        }
        jsonl.write_text(json.dumps(bad_record) + "\n", encoding="utf-8")

        validator = DatasetValidator()
        report = validator.validate_file(jsonl, "test_leaked")
        assert not report.is_valid
        assert any(i.field == "security" for i in report.issues)

    def test_google_ai_key_leak_flagged(self, tmp_path):
        jsonl = tmp_path / "google_leaked.jsonl"
        bad_record = {
            "task_type": "file_relevance",
            "issue_title": "Fix API key AIzaSyD1234567890123456789012345678901",
            "expected_relevant_files": ["auth.py"],
            "dataset_source": "synthetic_eval_v1",
        }
        jsonl.write_text(json.dumps(bad_record) + "\n", encoding="utf-8")

        validator = DatasetValidator()
        report = validator.validate_file(jsonl, "test_google_leak")
        assert not report.is_valid
        assert any("Google AI Studio" in i.message for i in report.issues)

    def test_path_traversal_in_task_files_flagged(self, tmp_path):
        jsonl = tmp_path / "traversal.jsonl"
        bad_record = {
            "task_type": "file_relevance",
            "issue_title": "Directory traversal test",
            "repository_snapshot": ["../../etc/passwd", "login.py"],
            "expected_relevant_files": ["login.py"],
            "dataset_source": "synthetic_eval_v1",
        }
        jsonl.write_text(json.dumps(bad_record) + "\n", encoding="utf-8")

        validator = DatasetValidator()
        report = validator.validate_file(jsonl, "test_traversal")
        assert not report.is_valid
        assert any(i.field == "path_traversal" for i in report.issues)

    def test_repository_level_split_leakage_prevented(self):
        pipeline = DatasetPipeline(load_dataset_manifest())
        tasks = [
            EvaluationTask(
                task_type=TaskType.FILE_RELEVANCE,
                owner="django",
                repo="django",
                issue_number=1,
                issue_title="Issue 1",
                expected_relevant_files=["views.py"],
                dataset_source="synthetic_eval_v1",
            ),
            EvaluationTask(
                task_type=TaskType.FILE_RELEVANCE,
                owner="django",
                repo="django",
                issue_number=2,
                issue_title="Issue 2",
                expected_relevant_files=["forms.py"],
                dataset_source="synthetic_eval_v1",
            ),
            EvaluationTask(
                task_type=TaskType.FILE_RELEVANCE,
                owner="pallets",
                repo="flask",
                issue_number=10,
                issue_title="Issue 10",
                expected_relevant_files=["app.py"],
                dataset_source="synthetic_eval_v1",
            ),
            EvaluationTask(
                task_type=TaskType.FILE_RELEVANCE,
                owner="psf",
                repo="requests",
                issue_number=100,
                issue_title="Issue 100",
                expected_relevant_files=["sessions.py"],
                dataset_source="synthetic_eval_v1",
            ),
        ]
        splits = pipeline.create_repository_splits(tasks, train_ratio=0.5, val_ratio=0.25, test_ratio=0.25)
        # Check leakage
        leaks = DatasetValidator.validate_split_leakage(splits["train"], splits["test"])
        assert leaks == []

    def test_acquisition_consent_gating(self):
        pipeline = DatasetPipeline(load_dataset_manifest())
        # Without explicit consent
        res = pipeline.acquire("codesearchnet_python", consent=False)
        assert res["status"] == "consent_required"
        # Excluded dataset
        res_ex = pipeline.acquire("the_stack_dedup", consent=True)
        assert res_ex["status"] == "excluded"


# ---------------------------------------------------------------------------
# 4. Mode Separation: Deterministic Baseline vs Live AI vs Mock AI
# ---------------------------------------------------------------------------

class TestModeSeparation:
    """Verifies clear separation between baseline and live AI evaluations."""

    def test_deterministic_baseline_mode_labeled_correctly(self, tmp_path):
        store = BenchmarkResultStore(results_dir=tmp_path / "res")
        evaluator = BenchmarkEvaluator(
            result_store=store,
            mode=EvaluationMode.DETERMINISTIC_BASELINE,
        )
        task = EvaluationTask(
            task_type=TaskType.AI_ENRICHMENT,
            owner="octocat",
            repo="Hello-World",
            issue_title="Explain login",
            issue_body="Detail the login flow",
            dataset_source="synthetic_eval_v1",
        )
        run = evaluator.evaluate([task], dataset_source="synthetic_eval_v1")
        assert run.evaluation_mode == "deterministic_baseline"
        assert run.task_results[0]["is_fallback"] is True
        assert run.task_results[0]["ai_generated"] is False

    def test_live_ai_mode_without_credentials_reports_honest_fallback(self, tmp_path):
        store = BenchmarkResultStore(results_dir=tmp_path / "res")
        fallback_provider = DeterministicFallbackProvider()
        evaluator = BenchmarkEvaluator(
            result_store=store,
            ai_provider=fallback_provider,
            mode=EvaluationMode.LIVE_AI,
        )
        task = EvaluationTask(
            task_type=TaskType.AI_ENRICHMENT,
            owner="octocat",
            repo="Hello-World",
            issue_title="Explain login",
            issue_body="Detail the login flow",
            dataset_source="synthetic_eval_v1",
        )
        run = evaluator.evaluate([task], dataset_source="synthetic_eval_v1")
        assert run.evaluation_mode == "live_ai"
        # Must report fallback honestly without pretending live inference ran
        assert run.task_results[0]["is_fallback"] is True
        assert run.task_results[0]["ai_generated"] is False
        assert "not configured" in run.task_results[0]["error"]

    def test_mock_ai_mode_never_claims_live_ai(self, tmp_path):
        store = BenchmarkResultStore(results_dir=tmp_path / "res")
        evaluator = BenchmarkEvaluator(
            result_store=store,
            mode=EvaluationMode.MOCK_AI,
        )
        task = EvaluationTask(
            task_type=TaskType.AI_ENRICHMENT,
            owner="octocat",
            repo="Hello-World",
            issue_title="Explain login",
            issue_body="Detail the login flow",
            dataset_source="synthetic_eval_v1",
        )
        run = evaluator.evaluate([task], dataset_source="synthetic_eval_v1")
        assert run.evaluation_mode == "mock_ai"
        assert run.task_results[0]["is_mock"] is True


# ---------------------------------------------------------------------------
# 5. End-to-End Backend Integration Workflow
# ---------------------------------------------------------------------------

class TestEndToEndBackendIntegration:
    """
    Covers the full backend workflow:
    Repo snapshot -> Issue retrieval -> AST analysis -> Evidence bundle ->
    Contribution plan -> Verification request (Docker unavailable safety) -> PR summary.
    """

    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocked_github_and_fallback_ai(self):
        # 1. Setup mock GitHub service
        mock_github = MagicMock()
        mock_github.get_repo_overview = AsyncMock(return_value=RepositoryOverview(
            owner="firstpatch",
            repo="demo",
            full_name="firstpatch/demo",
            primary_language="Python",
            stars=120,
            forks=15,
            open_issues_count=3,
            commit_sha="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            directory_snapshot=["src/main.py", "src/auth.py", "tests/test_auth.py", "README.md"],
            default_branch="main",
        ))
        mock_github.get_issues = AsyncMock(return_value=([
            {
                "number": 10,
                "title": "Fix token validation in src/auth.py",
                "body": "Token validation raises ValueError when authorization header is missing.",
                "html_url": "https://github.com/firstpatch/demo/issues/10",
                "labels": [{"name": "good first issue"}],
                "created_at": "2026-10-18T10:00:00Z",
                "user": {"login": "contributor"},
            }
        ], 1))
        mock_github.get_file_content = AsyncMock(return_value=(
            "def validate_token(token):\n"
            "    if not token:\n"
            "        raise ValueError('Empty token')\n"
            "    return True\n"
        ))

        # 2. Orchestrator with DeterministicFallbackProvider
        ai_provider = DeterministicFallbackProvider()
        orchestrator = FirstPatchAgentOrchestrator(github=mock_github, ai_provider=ai_provider)

        request = PlanRequest(owner="firstpatch", repo="demo", issue_number=10)
        orchestration_result: AgentOrchestrationResult = await orchestrator.execute_plan_workflow(request)

        # 3. Assert plan produced and verified
        plan = orchestration_result.plan
        assert plan.owner == "firstpatch"
        assert plan.repo == "demo"
        assert plan.issue_number == 10
        assert "src/auth.py" in plan.relevant_files
        assert len(plan.implementation_steps) >= 3
        # Evidence validity
        assert len(plan.evidence_refs) >= 1

        # 4. Verification Request with DockerExecutionDriver (Docker daemon unavailable)
        verification_store = VerificationRecordStore()
        verification_service = IsolatedVerificationService(store=verification_store)

        health = await verification_service.check_health()
        assert isinstance(health.runtime_available, bool)

        run_req = VerificationRunRequest(
            owner="firstpatch",
            repo="demo",
            commit_sha="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            test_target="tests/test_auth.py",
            runtime_profile=RuntimeProfile.PYTHON_311,
            issue_number=10,
        )
        record = await verification_service.execute_verification(run_req)

        # Honest reporting: If Docker is unavailable, status is UNAVAILABLE; never claims false pass
        if not health.runtime_available:
            assert record.status == ExecutionStatus.UNAVAILABLE
            assert record.counts is None or record.counts.total == 0
        else:
            assert record.status in (ExecutionStatus.PASSED, ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT)

        # 5. PR Summary Preparation
        pr_service = PRSummaryService(github=mock_github, ai_provider=ai_provider)
        pr_summary = await pr_service.generate_summary(
            owner="firstpatch",
            repo="demo",
            issue_number=10,
            plan=plan,
        )
        assert pr_summary.title.startswith("Fix: ") or "Fix" in pr_summary.title
        assert f"#{plan.issue_number}" in pr_summary.body or str(plan.issue_number) in pr_summary.body

    @pytest.mark.asyncio
    async def test_stale_commit_sha_handled_safely(self):
        mock_github = MagicMock()
        mock_github.get_repo_overview = AsyncMock(return_value=RepositoryOverview(
            owner="firstpatch",
            repo="demo",
            full_name="firstpatch/demo",
            primary_language="Python",
            stars=10,
            forks=2,
            open_issues_count=1,
            commit_sha="current_sha_12345",
            directory_snapshot=["main.py"],
            default_branch="main",
        ))
        mock_github.get_issues = AsyncMock(return_value=([
            {"number": 1, "title": "Test", "body": "Body", "html_url": "url", "labels": []}
        ], 1))
        mock_github.get_file_content = AsyncMock(return_value="x = 1")

        orchestrator = FirstPatchAgentOrchestrator(github=mock_github, ai_provider=DeterministicFallbackProvider())
        res = await orchestrator.execute_plan_workflow(PlanRequest(owner="firstpatch", repo="demo", issue_number=1))
        # Commit SHA in snapshot matches current overview
        assert res.repository.commit_sha == "current_sha_12345"
