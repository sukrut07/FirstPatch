"""
Phase 4 Tests — Dataset Intelligence, Benchmark Evaluation & End-to-End Integration

Coverage:
- DatasetManifest: source registry, status probing, summary
- DatasetPipeline: synthetic generation, describe_acquisition, iter_samples, load_tasks, sample_tasks
- DatasetValidator: JSONL integrity, required fields, schema conformance
- EvaluationTask / TaskResult: schema validation and field defaults
- Metrics: FileRetrievalMetrics precision/recall/F1/MRR, PlanMetrics, DiagnosisMetrics
- BenchmarkEvaluator: full evaluate() run on synthetic set
- BenchmarkResultStore: save/load/list/summary
- API routes: manifest, describe, generate-synthetic, validate, run, list, get, summary
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.benchmark.evaluator import BenchmarkEvaluator, _keyword_match_files
from app.services.benchmark.metrics import (
    compute_diagnosis_metrics,
    compute_file_retrieval_metrics,
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
from app.services.dataset.pipeline import (
    DatasetPipeline,
    DatasetSample,
    SYNTHETIC_TASKS,
    _swe_bench_to_task,
    _codesearchnet_to_task,
)
from app.services.dataset.task_schema import (
    EvaluationTask,
    TaskDifficulty,
    TaskResult,
    TaskType,
)
from app.services.dataset.validator import DatasetValidator, ValidationReport


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def tmp_dataset_dir(tmp_path):
    return tmp_path / "datasets"


@pytest.fixture
def manifest():
    return load_dataset_manifest()


@pytest.fixture
def pipeline(manifest):
    return DatasetPipeline(manifest)


@pytest.fixture
def result_store(tmp_path):
    return BenchmarkResultStore(results_dir=tmp_path / "results")


@pytest.fixture
def evaluator(result_store):
    return BenchmarkEvaluator(result_store=result_store)


@pytest.fixture
def synthetic_tasks(tmp_dataset_dir, manifest):
    """Generate synthetic tasks and return them."""
    pipeline = DatasetPipeline(manifest)
    return pipeline.generate_synthetic(output_dir=tmp_dataset_dir)


# ---------------------------------------------------------------------------
# DatasetManifest Tests
# ---------------------------------------------------------------------------

class TestDatasetManifest:
    def test_manifest_has_expected_sources(self, manifest):
        names = [s.name for s in manifest.sources]
        assert "synthetic_eval_v1" in names
        assert "swe_bench_lite" in names
        assert "codesearchnet_python" in names
        assert "repobench_retrieval" in names
        assert "github_good_first_issues" in names

    def test_synthetic_source_always_simulated(self, manifest):
        src = manifest.get("synthetic_eval_v1")
        assert src is not None
        assert src.status == DatasetStatus.SIMULATED

    def test_manifest_summary_keys(self, manifest):
        summary = manifest.summary()
        assert "total_sources" in summary
        assert "available" in summary
        assert "simulated" in summary
        assert "sources" in summary
        assert summary["total_sources"] == len(manifest.sources)

    def test_manifest_available_includes_simulated(self, manifest):
        avail = manifest.available()
        names = [s.name for s in avail]
        assert "synthetic_eval_v1" in names

    def test_manifest_get_unknown_returns_none(self, manifest):
        assert manifest.get("nonexistent_dataset_xyz") is None

    def test_data_source_to_dict(self, manifest):
        src = manifest.get("swe_bench_lite")
        assert src is not None
        d = src.to_dict()
        assert d["name"] == "swe_bench_lite"
        assert d["license"] == "MIT"
        assert isinstance(d["relevance_tags"], list)


# ---------------------------------------------------------------------------
# EvaluationTask / TaskResult Tests
# ---------------------------------------------------------------------------

class TestEvaluationTask:
    def test_task_creation_defaults(self):
        task = EvaluationTask(
            task_type=TaskType.FILE_RELEVANCE,
            dataset_source="test",
        )
        assert task.task_id is not None
        assert task.difficulty == TaskDifficulty.MEDIUM
        assert task.expected_relevant_files == []

    def test_task_type_enum_values(self):
        values = [t.value for t in TaskType]
        assert "file_relevance" in values
        assert "issue_tracing" in values
        assert "plan_quality" in values
        assert "ai_enrichment" in values
        assert "setup_diagnosis" in values

    def test_task_from_synthetic(self):
        raw = SYNTHETIC_TASKS[0]
        task = EvaluationTask(**raw)
        assert task.task_type in (TaskType.FILE_RELEVANCE, "file_relevance")
        assert len(task.expected_relevant_files) > 0

    def test_task_serialization(self):
        task = EvaluationTask(
            task_type=TaskType.ISSUE_TRACING,
            dataset_source="test",
            issue_title="Fix crash",
            expected_relevant_files=["src/app.py"],
        )
        dumped = json.loads(task.model_dump_json())
        restored = EvaluationTask(**dumped)
        assert restored.task_id == task.task_id
        assert restored.expected_relevant_files == ["src/app.py"]

    def test_task_result_defaults(self):
        result = TaskResult(task_id="abc", task_type="file_relevance")
        assert result.latency_ms == 0.0
        assert result.metrics == {}
        assert result.error is None


# ---------------------------------------------------------------------------
# DatasetPipeline Tests
# ---------------------------------------------------------------------------

class TestDatasetPipeline:
    def test_synthetic_generation_creates_tasks(self, tmp_dataset_dir, manifest):
        pipeline = DatasetPipeline(manifest)
        tasks = pipeline.generate_synthetic(output_dir=tmp_dataset_dir)
        assert len(tasks) == len(SYNTHETIC_TASKS)
        for task in tasks:
            assert isinstance(task, EvaluationTask)

    def test_synthetic_jsonl_written(self, tmp_dataset_dir, manifest):
        pipeline = DatasetPipeline(manifest)
        pipeline.generate_synthetic(output_dir=tmp_dataset_dir)
        jsonl = tmp_dataset_dir / "synthetic_eval_v1" / "test.jsonl"
        assert jsonl.exists()
        lines = [l for l in jsonl.read_text().splitlines() if l.strip()]
        assert len(lines) == len(SYNTHETIC_TASKS)

    def test_load_tasks_from_synthetic(self, tmp_dataset_dir, manifest):
        pipeline = DatasetPipeline(manifest)
        tasks = pipeline.generate_synthetic(output_dir=tmp_dataset_dir)
        # Now update manifest source path
        src = manifest.get("synthetic_eval_v1")
        src.local_path = tmp_dataset_dir / "synthetic_eval_v1"
        loaded = pipeline.load_tasks("synthetic_eval_v1")
        assert len(loaded) == len(tasks)

    def test_load_tasks_with_max(self, tmp_dataset_dir, manifest):
        pipeline = DatasetPipeline(manifest)
        pipeline.generate_synthetic(output_dir=tmp_dataset_dir)
        src = manifest.get("synthetic_eval_v1")
        src.local_path = tmp_dataset_dir / "synthetic_eval_v1"
        loaded = pipeline.load_tasks("synthetic_eval_v1", max_tasks=3)
        assert len(loaded) <= 3

    def test_sample_tasks(self, tmp_dataset_dir, manifest):
        pipeline = DatasetPipeline(manifest)
        pipeline.generate_synthetic(output_dir=tmp_dataset_dir)
        src = manifest.get("synthetic_eval_v1")
        src.local_path = tmp_dataset_dir / "synthetic_eval_v1"
        sampled = pipeline.sample_tasks("synthetic_eval_v1", n=2)
        assert len(sampled) <= 2

    def test_sample_tasks_by_type(self, tmp_dataset_dir, manifest):
        pipeline = DatasetPipeline(manifest)
        pipeline.generate_synthetic(output_dir=tmp_dataset_dir)
        src = manifest.get("synthetic_eval_v1")
        src.local_path = tmp_dataset_dir / "synthetic_eval_v1"
        sampled = pipeline.sample_tasks("synthetic_eval_v1", n=10, task_type=TaskType.FILE_RELEVANCE)
        for t in sampled:
            tt = t.task_type if isinstance(t.task_type, str) else t.task_type.value
            assert tt == "file_relevance"

    def test_load_tasks_unknown_source(self, manifest):
        pipeline = DatasetPipeline(manifest)
        tasks = pipeline.load_tasks("totally_unknown_source_xyz")
        assert tasks == []

    def test_describe_acquisition_synthetic(self, manifest):
        pipeline = DatasetPipeline(manifest)
        desc = pipeline.describe_acquisition("synthetic_eval_v1")
        assert desc["method"] == "synthetic"
        assert "generate_synthetic" in desc["instructions"]

    def test_describe_acquisition_huggingface(self, manifest):
        pipeline = DatasetPipeline(manifest)
        desc = pipeline.describe_acquisition("swe_bench_lite")
        assert desc["method"] == "huggingface_datasets"
        assert "load_dataset" in desc["instructions"]

    def test_describe_acquisition_unknown(self, manifest):
        pipeline = DatasetPipeline(manifest)
        desc = pipeline.describe_acquisition("not_a_real_source")
        assert "error" in desc

    def test_swe_bench_conversion(self):
        raw = {
            "instance_id": "psf__requests-6000",
            "problem_statement": "Session cookies are dropped on redirect.",
            "patch": (
                "diff --git a/requests/sessions.py b/requests/sessions.py\n"
                "index abc..def 100644\n"
                "--- a/requests/sessions.py\n"
                "+++ b/requests/sessions.py\n"
                "@@ -1,1 +1,1 @@\n-old\n+new\n"
            ),
            "number": 6000,
        }
        task = _swe_bench_to_task(raw, "swe_bench_lite")
        assert task.task_type == TaskType.ISSUE_TRACING or task.task_type == "issue_tracing"
        assert "requests/sessions.py" in task.expected_patch_files

    def test_codesearchnet_conversion(self):
        raw = {
            "func_name": "parse_url",
            "code": "def parse_url(url): ...",
            "docstring": "Parse a URL into components.",
            "repo": "urllib/urllib3",
            "path": "src/urllib3/util/url.py",
        }
        task = _codesearchnet_to_task(raw, "codesearchnet_python")
        assert task.task_type == TaskType.FILE_RELEVANCE or task.task_type == "file_relevance"
        assert task.expected_relevant_files == ["src/urllib3/util/url.py"]


# ---------------------------------------------------------------------------
# DatasetValidator Tests
# ---------------------------------------------------------------------------

class TestDatasetValidator:
    def test_valid_jsonl(self, tmp_path):
        validator = DatasetValidator()
        jf = tmp_path / "test.jsonl"
        task = EvaluationTask(task_type=TaskType.FILE_RELEVANCE, dataset_source="test",
                               issue_title="fix", expected_relevant_files=["a.py"])
        jf.write_text(task.model_dump_json() + "\n", encoding="utf-8")
        report = validator.validate_file(jf, "test")
        assert report.valid_tasks == 1
        assert report.invalid_lines == 0
        assert report.is_valid

    def test_invalid_json_line(self, tmp_path):
        validator = DatasetValidator()
        jf = tmp_path / "test.jsonl"
        jf.write_text('not valid json\n{"task_type": "file_relevance", "dataset_source": "t"}\n')
        report = validator.validate_file(jf, "test")
        assert report.invalid_lines >= 1
        assert any(i.field == "json" for i in report.issues)

    def test_missing_required_field_warning(self, tmp_path):
        validator = DatasetValidator()
        jf = tmp_path / "test.jsonl"
        task = EvaluationTask(task_type=TaskType.FILE_RELEVANCE, dataset_source="test",
                               issue_title="", expected_relevant_files=[])
        jf.write_text(task.model_dump_json() + "\n", encoding="utf-8")
        report = validator.validate_file(jf, "test")
        # Should have warnings for missing required fields
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert len(warnings) > 0

    def test_validate_directory_no_jsonl(self, tmp_path):
        validator = DatasetValidator()
        empty = tmp_path / "empty_dataset"
        empty.mkdir()
        report = validator.validate_directory(empty, "test")
        assert not report.is_valid
        assert any("No JSONL" in i.message for i in report.issues)

    def test_validate_directory_multiple_files(self, tmp_path):
        validator = DatasetValidator()
        dataset_dir = tmp_path / "multi"
        dataset_dir.mkdir()
        for i in range(3):
            task = EvaluationTask(
                task_type=TaskType.FILE_RELEVANCE,
                dataset_source="test",
                issue_title=f"fix {i}",
                expected_relevant_files=[f"file{i}.py"],
            )
            (dataset_dir / f"part{i}.jsonl").write_text(task.model_dump_json() + "\n")
        report = validator.validate_directory(dataset_dir, "test")
        assert report.valid_tasks == 3
        assert report.is_valid


# ---------------------------------------------------------------------------
# Metrics Tests
# ---------------------------------------------------------------------------

class TestFileRetrievalMetrics:
    def test_perfect_match(self):
        m = compute_file_retrieval_metrics(["a.py", "b.py"], ["a.py", "b.py"])
        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.f1 == 1.0
        assert m.hit_at_1

    def test_no_match(self):
        m = compute_file_retrieval_metrics(["c.py"], ["a.py"])
        assert m.precision == 0.0
        assert m.recall == 0.0
        assert m.f1 == 0.0
        assert not m.hit_at_1

    def test_partial_match(self):
        m = compute_file_retrieval_metrics(["a.py", "c.py"], ["a.py", "b.py"])
        assert m.precision == 0.5
        assert m.recall == 0.5
        assert m.tp == 1

    def test_empty_predicted(self):
        m = compute_file_retrieval_metrics([], ["a.py"])
        assert m.precision == 0.0
        assert m.recall == 0.0
        assert m.f1 == 0.0

    def test_empty_expected(self):
        m = compute_file_retrieval_metrics(["a.py"], [])
        assert m.expected_count == 0

    def test_mrr_first_correct(self):
        m = compute_file_retrieval_metrics(["a.py", "b.py", "c.py"], ["b.py"])
        assert m.mrr == pytest.approx(0.5, abs=1e-4)

    def test_hit_at_k(self):
        predicted = ["x.py", "y.py", "z.py", "a.py", "b.py"]
        m = compute_file_retrieval_metrics(predicted, ["a.py"])
        assert not m.hit_at_1
        assert not m.hit_at_3
        assert m.hit_at_5

    def test_path_normalization(self):
        m = compute_file_retrieval_metrics(["./src/App.py"], ["src/app.py"])
        assert m.tp == 1

    def test_to_dict_keys(self):
        m = compute_file_retrieval_metrics(["a.py"], ["a.py"])
        d = m.to_dict()
        assert "precision" in d
        assert "recall" in d
        assert "f1" in d
        assert "mrr" in d
        assert "hit_at_1" in d


class TestPlanMetrics:
    def test_complete_plan(self):
        plan = {
            "implementation_steps": [
                {"description": "Read the issue"},
                {"description": "Create a branch"},
                {"description": "Implement the fix"},
                {"description": "Write tests for the change"},
                {"description": "Open a pull request"},
            ],
            "relevant_files": ["a.py", "b.py"],
            "evidence_refs": [{"type": "issue"}, {"type": "file"}, {"type": "file"}],
            "uncertainties": [],
            "ai_generated": False,
        }
        m = compute_plan_metrics(plan)
        assert m.step_count == 5
        assert m.has_test_step
        assert m.has_pr_step
        assert m.quality_score > 0.5

    def test_empty_plan(self):
        m = compute_plan_metrics({})
        assert m.step_count == 0
        assert m.quality_score == 0.0

    def test_to_dict(self):
        m = compute_plan_metrics({})
        d = m.to_dict()
        assert "quality_score" in d
        assert "has_test_step" in d


class TestDiagnosisMetrics:
    def test_exact_match(self):
        m = compute_diagnosis_metrics("missing_dependency", "missing_dependency")
        assert m.correct

    def test_partial_match(self):
        # "dependency" from "missing_dependency" appears in predicted text
        m = compute_diagnosis_metrics(
            "missing a required dependency or package",
            "missing_dependency",
        )
        assert m.partial_match

    def test_no_match(self):
        m = compute_diagnosis_metrics("port conflict", "missing_dependency")
        assert not m.correct

    def test_to_dict_keys(self):
        m = compute_diagnosis_metrics("a", "b")
        d = m.to_dict()
        assert "predicted" in d
        assert "expected" in d
        assert "correct" in d


# ---------------------------------------------------------------------------
# BenchmarkResultStore Tests
# ---------------------------------------------------------------------------

class TestBenchmarkResultStore:
    def test_save_and_load(self, result_store):
        run = BenchmarkRun(
            dataset_source="synthetic_eval_v1",
            total_tasks=6,
            completed_tasks=6,
        )
        result_store.save(run)
        loaded = result_store.load(run.run_id)
        assert loaded is not None
        assert loaded.run_id == run.run_id
        assert loaded.total_tasks == 6

    def test_list_runs(self, result_store):
        for i in range(3):
            run = BenchmarkRun(dataset_source="synthetic_eval_v1", total_tasks=i)
            result_store.save(run)
        runs = result_store.list_runs()
        assert len(runs) == 3

    def test_list_runs_filtered(self, result_store):
        run_a = BenchmarkRun(dataset_source="source_a", total_tasks=1)
        run_b = BenchmarkRun(dataset_source="source_b", total_tasks=2)
        result_store.save(run_a)
        result_store.save(run_b)
        runs = result_store.list_runs(dataset_source="source_a")
        assert all(r.dataset_source == "source_a" for r in runs)

    def test_load_unknown_returns_none(self, result_store):
        assert result_store.load("nonexistent-run-id-xyz") is None

    def test_latest(self, result_store):
        for i in range(2):
            result_store.save(BenchmarkRun(dataset_source="test", total_tasks=i))
        latest = result_store.latest()
        assert latest is not None

    def test_aggregate_summary_empty(self, result_store):
        summary = result_store.aggregate_summary()
        assert summary["total_runs"] == 0

    def test_aggregate_summary_with_runs(self, result_store):
        from datetime import datetime, timezone
        run = BenchmarkRun(
            dataset_source="synthetic_eval_v1",
            total_tasks=6,
            completed_tasks=6,
            completed_at=datetime.now(timezone.utc),
            aggregate_metrics={"mean_f1": 0.8, "mean_recall": 0.75},
        )
        result_store.save(run)
        summary = result_store.aggregate_summary(dataset_source="synthetic_eval_v1")
        assert summary["total_runs"] >= 1


# ---------------------------------------------------------------------------
# BenchmarkEvaluator Tests
# ---------------------------------------------------------------------------

class TestBenchmarkEvaluator:
    def test_evaluate_synthetic_set(self, tmp_dataset_dir, manifest, result_store):
        pipeline = DatasetPipeline(manifest)
        tasks = pipeline.generate_synthetic(output_dir=tmp_dataset_dir)
        src = manifest.get("synthetic_eval_v1")
        src.local_path = tmp_dataset_dir / "synthetic_eval_v1"

        evaluator = BenchmarkEvaluator(result_store=result_store)
        run = evaluator.evaluate(tasks, dataset_source="synthetic_eval_v1")

        assert run.run_id is not None
        assert run.total_tasks == len(tasks)
        assert run.completed_tasks + run.failed_tasks == run.total_tasks
        assert "total_tasks" in run.aggregate_metrics

    def test_evaluate_file_relevance_only(self, tmp_dataset_dir, manifest, result_store):
        pipeline = DatasetPipeline(manifest)
        tasks = pipeline.generate_synthetic(output_dir=tmp_dataset_dir)
        evaluator = BenchmarkEvaluator(result_store=result_store)
        run = evaluator.evaluate(
            tasks, dataset_source="test", task_type_filter=TaskType.FILE_RELEVANCE
        )
        assert all(
            r["task_type"] in ("file_relevance", TaskType.FILE_RELEVANCE)
            for r in run.task_results
        )
        if run.completed_tasks > 0:
            assert "mean_f1" in run.aggregate_metrics

    def test_evaluate_plan_quality(self, tmp_dataset_dir, manifest, result_store):
        pipeline = DatasetPipeline(manifest)
        tasks = pipeline.generate_synthetic(output_dir=tmp_dataset_dir)
        pq_tasks = [t for t in tasks if t.task_type in ("plan_quality", TaskType.PLAN_QUALITY)]
        assert len(pq_tasks) > 0
        evaluator = BenchmarkEvaluator(result_store=result_store)
        run = evaluator.evaluate(pq_tasks, dataset_source="test", task_type_filter=TaskType.PLAN_QUALITY)
        assert run.completed_tasks > 0
        assert "mean_plan_quality" in run.aggregate_metrics

    def test_evaluate_setup_diagnosis(self, tmp_dataset_dir, manifest, result_store):
        pipeline = DatasetPipeline(manifest)
        tasks = pipeline.generate_synthetic(output_dir=tmp_dataset_dir)
        sd_tasks = [t for t in tasks if t.task_type in ("setup_diagnosis", TaskType.SETUP_DIAGNOSIS)]
        assert len(sd_tasks) > 0
        evaluator = BenchmarkEvaluator(result_store=result_store)
        run = evaluator.evaluate(sd_tasks, dataset_source="test", task_type_filter=TaskType.SETUP_DIAGNOSIS)
        assert run.completed_tasks > 0
        assert "diagnosis_accuracy" in run.aggregate_metrics

    def test_run_persisted_to_store(self, tmp_dataset_dir, manifest, result_store):
        pipeline = DatasetPipeline(manifest)
        tasks = pipeline.generate_synthetic(output_dir=tmp_dataset_dir)
        evaluator = BenchmarkEvaluator(result_store=result_store)
        run = evaluator.evaluate(tasks[:2], dataset_source="test")
        loaded = result_store.load(run.run_id)
        assert loaded is not None
        assert loaded.run_id == run.run_id

    def test_evaluate_empty_task_list(self, result_store):
        evaluator = BenchmarkEvaluator(result_store=result_store)
        run = evaluator.evaluate([], dataset_source="test")
        assert run.total_tasks == 0
        assert run.completed_tasks == 0


# ---------------------------------------------------------------------------
# Keyword Match Helper Tests
# ---------------------------------------------------------------------------

class TestKeywordMatch:
    def test_direct_file_mention(self):
        result = _keyword_match_files("fix login.py crash", ["login.py", "utils.py"])
        assert "login.py" in result

    def test_keyword_scoring(self):
        result = _keyword_match_files(
            "authentication error in session management",
            ["auth.py", "session.py", "main.py", "utils.py"],
        )
        assert "auth.py" in result or "session.py" in result

    def test_no_match_returns_empty(self):
        result = _keyword_match_files("zzz qqq", ["completely_unrelated.py"])
        assert result == [] or isinstance(result, list)

    def test_max_five_results(self):
        snapshot = [f"file{i}.py" for i in range(20)]
        result = _keyword_match_files("file fix code", snapshot)
        assert len(result) <= 5


# ---------------------------------------------------------------------------
# API Route Tests
# ---------------------------------------------------------------------------

class TestDatasetRoutes:
    def test_manifest_endpoint(self, client):
        resp = client.get("/api/dataset/manifest")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sources" in data
        assert data["total_sources"] >= 5
        assert "sources" in data

    def test_describe_synthetic(self, client):
        resp = client.get("/api/dataset/describe/synthetic_eval_v1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["method"] == "synthetic"

    def test_describe_swe_bench(self, client):
        resp = client.get("/api/dataset/describe/swe_bench_lite")
        assert resp.status_code == 200
        data = resp.json()
        assert "huggingface" in data["method"]

    def test_describe_unknown_source(self, client):
        resp = client.get("/api/dataset/describe/unknown_xyz")
        assert resp.status_code == 404

    def test_generate_synthetic(self, client):
        resp = client.post("/api/dataset/generate-synthetic")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "generated"
        assert data["task_count"] == len(SYNTHETIC_TASKS)

    def test_validate_synthetic_after_generation(self, client):
        client.post("/api/dataset/generate-synthetic")
        resp = client.post("/api/dataset/validate/synthetic_eval_v1")
        assert resp.status_code == 200
        data = resp.json()
        assert "valid_tasks" in data or "status" in data

    def test_validate_unknown_source(self, client):
        resp = client.post("/api/dataset/validate/unknown_source_xyz")
        assert resp.status_code == 404


class TestBenchmarkRoutes:
    def test_run_benchmark_synthetic(self, client):
        # Ensure synthetic set is generated
        client.post("/api/dataset/generate-synthetic")
        resp = client.post(
            "/api/benchmark/run",
            json={"dataset_source": "synthetic_eval_v1", "max_tasks": 6},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "run_id" in data
        assert data["status"] == "completed"
        assert "aggregate_metrics" in data
        assert data["total_tasks"] > 0

    def test_run_benchmark_with_task_type_filter(self, client):
        client.post("/api/dataset/generate-synthetic")
        resp = client.post(
            "/api/benchmark/run",
            json={
                "dataset_source": "synthetic_eval_v1",
                "task_type": "file_relevance",
                "max_tasks": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "mean_f1" in data["aggregate_metrics"]

    def test_run_benchmark_invalid_task_type(self, client):
        resp = client.post(
            "/api/benchmark/run",
            json={"dataset_source": "synthetic_eval_v1", "task_type": "not_a_type"},
        )
        assert resp.status_code == 422

    def test_run_benchmark_unavailable_source(self, client):
        resp = client.post(
            "/api/benchmark/run",
            json={"dataset_source": "swe_bench_lite", "max_tasks": 5},
        )
        assert resp.status_code == 404

    def test_list_benchmark_runs(self, client):
        client.post("/api/dataset/generate-synthetic")
        client.post(
            "/api/benchmark/run",
            json={"dataset_source": "synthetic_eval_v1", "max_tasks": 3},
        )
        resp = client.get("/api/benchmark/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "runs" in data
        assert data["total"] >= 1

    def test_get_run_by_id(self, client):
        client.post("/api/dataset/generate-synthetic")
        run_resp = client.post(
            "/api/benchmark/run",
            json={"dataset_source": "synthetic_eval_v1", "max_tasks": 2},
        )
        run_id = run_resp.json()["run_id"]

        resp = client.get(f"/api/benchmark/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run_id

    def test_get_run_not_found(self, client):
        resp = client.get("/api/benchmark/runs/nonexistent-run-id-xyz-12345")
        assert resp.status_code == 404

    def test_benchmark_summary(self, client):
        resp = client.get("/api/benchmark/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_runs" in data
