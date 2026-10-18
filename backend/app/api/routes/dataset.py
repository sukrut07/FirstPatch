"""
FirstPatch AI — Phase 4 API Routes: Dataset & Benchmark

Endpoints:
  GET  /api/dataset/manifest          — Dataset source registry and local availability
  GET  /api/dataset/describe/{name}   — Acquisition instructions for a specific source
  POST /api/dataset/generate-synthetic — Write the synthetic evaluation set to disk
  POST /api/dataset/validate/{name}   — Validate a locally available dataset
  POST /api/benchmark/run             — Run benchmark evaluation
  GET  /api/benchmark/runs            — List recent benchmark runs
  GET  /api/benchmark/runs/{run_id}   — Fetch a specific run
  GET  /api/benchmark/summary         — Aggregate stats across runs
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.benchmark.evaluator import BenchmarkEvaluator
from app.services.benchmark.result_store import BenchmarkResultStore
from app.services.dataset.manifest import load_dataset_manifest
from app.services.dataset.pipeline import DatasetPipeline
from app.services.dataset.task_schema import TaskType
from app.services.dataset.validator import DatasetValidator

router = APIRouter(prefix="/api/dataset", tags=["dataset"])
benchmark_router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])

logger = logging.getLogger(__name__)

# Shared singletons
_result_store = BenchmarkResultStore()
_validator = DatasetValidator()


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
        description="Name of the dataset source to evaluate against.",
    )
    task_type: Optional[str] = Field(
        default=None,
        description="Optionally filter to a specific task type.",
    )
    max_tasks: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of tasks to evaluate.",
    )
    notes: str = Field(default="", description="Optional run notes.")


@benchmark_router.post("/run", summary="Run benchmark evaluation")
async def run_benchmark(request: BenchmarkRunRequest) -> dict[str, Any]:
    """
    Run the benchmark evaluation pipeline against a dataset source.

    Uses the deterministic file-matching engine by default.
    AI provider metrics are noted in the run record.
    """
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
                       f"Valid: {[t.value for t in TaskType]}"
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

    evaluator = BenchmarkEvaluator(
        result_store=_result_store,
        ai_provider_name=settings.ai_provider,
        ai_model_name=settings.google_ai_model if settings.ai_provider == "google_ai_studio" else settings.ollama_model,
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
        "dataset_source": run.dataset_source,
        "total_tasks": run.total_tasks,
        "completed_tasks": run.completed_tasks,
        "failed_tasks": run.failed_tasks,
        "aggregate_metrics": run.aggregate_metrics,
        "ai_provider": run.ai_provider,
        "ai_model": run.ai_model,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@benchmark_router.get("/runs", summary="List recent benchmark runs")
async def list_runs(
    dataset_source: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """List recent benchmark evaluation runs."""
    runs = _result_store.list_runs(dataset_source=dataset_source, limit=limit)
    return {
        "total": len(runs),
        "runs": [
            {
                "run_id": r.run_id,
                "dataset_source": r.dataset_source,
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
    run = _result_store.load(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return run.model_dump()


@benchmark_router.get("/summary", summary="Aggregate benchmark statistics")
async def get_summary(
    dataset_source: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    """Return aggregate statistics across all benchmark runs."""
    return _result_store.aggregate_summary(dataset_source=dataset_source)
