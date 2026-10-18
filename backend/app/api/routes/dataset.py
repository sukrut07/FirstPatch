"""
FirstPatch AI — Phase 4 API Routes: Dataset & Benchmark

Endpoints:
  GET  /api/dataset/manifest          — Dataset source registry and local availability
  GET  /api/dataset/describe/{name}   — Acquisition instructions for a specific source
  POST /api/dataset/generate-synthetic — Write the synthetic evaluation set to disk
  POST /api/dataset/validate/{name}   — Validate a locally available dataset
  POST /api/benchmark/run             — Run benchmark evaluation with concurrency guard
  GET  /api/benchmark/runs            — List recent benchmark runs (paginated)
  GET  /api/benchmark/runs/{run_id}   — Fetch a specific run
  GET  /api/benchmark/summary         — Aggregate stats across runs
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.benchmark.evaluator import BenchmarkEvaluator, EvaluationMode
from app.services.benchmark.result_store import BenchmarkResultStore
from app.services.dataset.manifest import load_dataset_manifest
from app.services.dataset.pipeline import DatasetPipeline
from app.services.dataset.task_schema import TaskType
from app.services.dataset.validator import DatasetValidator
from app.services.mentor.ai_provider import get_ai_provider

router = APIRouter(prefix="/api/dataset", tags=["dataset"])
benchmark_router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])

logger = logging.getLogger(__name__)

# Shared singletons
_result_store = BenchmarkResultStore()
_validator = DatasetValidator()
_benchmark_lock = asyncio.Lock()

# Safe identifier pattern to prevent path traversal
SAFE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _validate_safe_source_name(name: str) -> None:
    """Validate that source_name does not contain path traversal characters."""
    if not name or len(name) > 64 or not SAFE_NAME_PATTERN.match(name) or ".." in name:
        raise HTTPException(
            status_code=400,
            detail="Invalid source name format. Path traversal characters not permitted.",
        )


# ---------------------------------------------------------------------------
# Dataset endpoints
# ---------------------------------------------------------------------------

@router.get("/manifest", summary="Dataset registry with local availability")
async def get_manifest() -> dict[str, Any]:
    """Return all registered dataset sources with their local availability status."""
    manifest = load_dataset_manifest()
    return manifest.summary()


@router.get("/describe/{source_name}", summary="Acquisition instructions for a dataset source")
async def describe_source(source_name: str) -> dict[str, Any]:
    """
    Return step-by-step instructions for acquiring a specific dataset.
    Does not perform any download.
    """
    _validate_safe_source_name(source_name)
    manifest = load_dataset_manifest()
    pipeline = DatasetPipeline(manifest)
    desc = pipeline.describe_acquisition(source_name)
    if "error" in desc:
        raise HTTPException(status_code=404, detail=desc["error"])
    return desc


@router.post("/generate-synthetic", summary="Generate built-in synthetic evaluation set")
async def generate_synthetic() -> dict[str, Any]:
    """
    Write the synthetic evaluation set to disk.
    Safe to call repeatedly — idempotent.
    Returns task summary.
    """
    manifest = load_dataset_manifest()
    pipeline = DatasetPipeline(manifest)
    tasks = pipeline.generate_synthetic()
    return {
        "status": "generated",
        "task_count": len(tasks),
        "task_types": list({t.task_type if isinstance(t.task_type, str) else t.task_type.value for t in tasks}),
        "source": "synthetic_eval_v1",
    }


@router.post("/validate/{source_name}", summary="Validate a locally available dataset")
async def validate_dataset(source_name: str) -> dict[str, Any]:
    """
    Run structural validation on a locally available dataset.
    Returns a ValidationReport.
    """
    _validate_safe_source_name(source_name)
    manifest = load_dataset_manifest()
    source = manifest.get(source_name)
    if not source:
        raise HTTPException(status_code=404, detail=f"Unknown dataset source: {source_name}")

    if not source.local_path or not source.local_path.exists():
        return {
            "source_name": source_name,
            "status": source.status.value,
            "message": "Dataset not available locally. Call /generate-synthetic or follow acquisition instructions.",
        }

    report = _validator.validate_directory(source.local_path, source_name)
    return report.to_dict()


# ---------------------------------------------------------------------------
# Benchmark endpoints
# ---------------------------------------------------------------------------

class BenchmarkRunRequest(BaseModel):
    dataset_source: str = Field(
        default="synthetic_eval_v1",
        max_length=64,
        description="Name of the dataset source to evaluate against.",
    )
    evaluation_mode: str = Field(
        default="deterministic_baseline",
        description="Evaluation mode: deterministic_baseline, live_ai, or mock_ai.",
    )
    task_type: Optional[str] = Field(
        default=None,
        description="Optionally filter to a specific task type.",
    )
    max_tasks: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of tasks to evaluate (bounded between 1 and 500).",
    )
    notes: str = Field(default="", max_length=500, description="Optional run notes.")


@benchmark_router.post("/run", summary="Run benchmark evaluation")
async def run_benchmark(request: BenchmarkRunRequest) -> dict[str, Any]:
    """
    Run the benchmark evaluation pipeline against a dataset source.
    Enforces concurrency limits and strict evaluation mode separation.
    """
    _validate_safe_source_name(request.dataset_source)

    valid_modes = [m.value for m in EvaluationMode]
    if request.evaluation_mode not in valid_modes:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid evaluation_mode '{request.evaluation_mode}'. Valid: {valid_modes}",
        )

    mode = EvaluationMode(request.evaluation_mode)

    if _benchmark_lock.locked():
        raise HTTPException(
            status_code=429,
            detail="A benchmark evaluation is already in progress. Please wait for it to complete.",
        )

    async with _benchmark_lock:
        from app.core.config import get_settings
        settings = get_settings()

        manifest = load_dataset_manifest()
        pipeline = DatasetPipeline(manifest)

        # Auto-generate synthetic set if needed
        if request.dataset_source == "synthetic_eval_v1":
            source = manifest.get("synthetic_eval_v1")
            if not source or not source.local_path or not source.local_path.exists():
                pipeline.generate_synthetic()
                manifest = load_dataset_manifest()
                pipeline = DatasetPipeline(manifest)

        task_type_filter: Optional[TaskType] = None
        if request.task_type:
            try:
                task_type_filter = TaskType(request.task_type)
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unknown task_type '{request.task_type}'. "
                           f"Valid: {[t.value for t in TaskType]}",
                )

        tasks = pipeline.load_tasks(
            source_name=request.dataset_source,
            max_tasks=request.max_tasks,
        )

        if not tasks:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No tasks found for source '{request.dataset_source}'. "
                    "Try POST /api/dataset/generate-synthetic first."
                ),
            )

        ai_provider = get_ai_provider()

        evaluator = BenchmarkEvaluator(
            result_store=_result_store,
            ai_provider=ai_provider,
            ai_provider_name=settings.ai_provider,
            ai_model_name=settings.google_ai_model if settings.ai_provider == "google_ai_studio" else settings.ollama_model,
            mode=mode,
        )

        run = evaluator.evaluate(
            tasks=tasks,
            dataset_source=request.dataset_source,
            task_type_filter=task_type_filter,
            notes=request.notes,
        )

        return {
            "run_id": run.run_id,
            "status": "completed",
            "evaluation_mode": run.evaluation_mode,
            "dataset_source": run.dataset_source,
            "total_tasks": run.total_tasks,
            "completed_tasks": run.completed_tasks,
            "failed_tasks": run.failed_tasks,
            "aggregate_metrics": run.aggregate_metrics,
            "ai_provider": run.ai_provider,
            "ai_model": run.ai_model,
            "evaluator_version": run.evaluator_version,
            "prompt_version": run.prompt_version,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }


@benchmark_router.get("/runs", summary="List recent benchmark runs")
async def list_runs(
    dataset_source: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List recent benchmark evaluation runs with pagination."""
    if dataset_source:
        _validate_safe_source_name(dataset_source)
    runs = _result_store.list_runs(dataset_source=dataset_source, limit=limit, offset=offset)
    all_runs = _result_store.list_runs(dataset_source=dataset_source, limit=1000)
    return {
        "total": len(all_runs),
        "limit": limit,
        "offset": offset,
        "returned": len(runs),
        "runs": [
            {
                "run_id": r.run_id,
                "dataset_source": r.dataset_source,
                "evaluation_mode": r.evaluation_mode,
                "task_type": r.task_type,
                "total_tasks": r.total_tasks,
                "completed_tasks": r.completed_tasks,
                "aggregate_metrics": r.aggregate_metrics,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ],
    }


@benchmark_router.get("/runs/{run_id}", summary="Fetch a specific benchmark run")
async def get_run(run_id: str) -> dict[str, Any]:
    """Return the full detail of a specific benchmark run."""
    _validate_safe_source_name(run_id)
    run = _result_store.load(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return run.model_dump()


@benchmark_router.get("/summary", summary="Aggregate benchmark statistics")
async def get_summary(
    dataset_source: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    """Return aggregate statistics across all benchmark runs."""
    if dataset_source:
        _validate_safe_source_name(dataset_source)
    return _result_store.aggregate_summary(dataset_source=dataset_source)
