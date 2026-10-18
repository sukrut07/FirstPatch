"""
FirstPatch AI — Benchmark Result Store (Phase 4)

Persists BenchmarkRun records as JSONL in the datasets directory.
No external database required — JSONL is portable and inspectable.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).resolve().parents[5] / "datasets" / "_benchmark_results"


class BenchmarkRun(BaseModel):
    """Persisted record of one complete benchmark evaluation run."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    dataset_source: str = ""
    task_type: Optional[str] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    ai_provider: str = "deterministic_fallback"
    ai_model: str = "none"
    aggregate_metrics: dict[str, Any] = Field(default_factory=dict)
    task_results: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""

    class Config:
        use_enum_values = True


class BenchmarkResultStore:
    """
    Reads and writes BenchmarkRun records as JSONL.

    File layout:
      datasets/_benchmark_results/<dataset_source>/<run_id>.jsonl
    """

    def __init__(self, results_dir: Optional[Path] = None):
        self._root = results_dir or RESULTS_DIR
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, run: BenchmarkRun) -> Path:
        """Persist a BenchmarkRun. Returns the file path."""
        source_dir = self._root / (run.dataset_source or "unknown")
        source_dir.mkdir(parents=True, exist_ok=True)
        dest = source_dir / f"{run.run_id}.json"
        dest.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Benchmark run saved: %s", dest)
        return dest

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load(self, run_id: str) -> Optional[BenchmarkRun]:
        """Load a specific run by ID (searches all source dirs)."""
        for json_file in self._root.glob(f"**/{run_id}.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                return BenchmarkRun(**data)
            except Exception as exc:
                logger.warning("Could not parse run file %s: %s", json_file, exc)
        return None

    def list_runs(
        self,
        dataset_source: Optional[str] = None,
        limit: int = 50,
    ) -> list[BenchmarkRun]:
        """List recent benchmark runs, optionally filtered by source."""
        pattern = f"{dataset_source}/*.json" if dataset_source else "**/*.json"
        files = sorted(self._root.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
        runs: list[BenchmarkRun] = []
        for f in files[:limit]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                runs.append(BenchmarkRun(**data))
            except Exception as exc:
                logger.debug("Skipping unreadable run file %s: %s", f, exc)
        return runs

    def latest(self, dataset_source: Optional[str] = None) -> Optional[BenchmarkRun]:
        """Return the most recent BenchmarkRun."""
        runs = self.list_runs(dataset_source=dataset_source, limit=1)
        return runs[0] if runs else None

    def aggregate_summary(self, dataset_source: Optional[str] = None) -> dict[str, Any]:
        """
        Compute summary statistics across all runs for a source.
        """
        runs = self.list_runs(dataset_source=dataset_source, limit=200)
        if not runs:
            return {"total_runs": 0, "dataset_source": dataset_source}

        completed = [r for r in runs if r.completed_at is not None]
        avg_f1 = _safe_mean([
            r.aggregate_metrics.get("mean_f1", 0.0) for r in completed
        ])
        avg_recall = _safe_mean([
            r.aggregate_metrics.get("mean_recall", 0.0) for r in completed
        ])
        avg_quality = _safe_mean([
            r.aggregate_metrics.get("mean_plan_quality", 0.0) for r in completed
        ])

        return {
            "total_runs": len(runs),
            "completed_runs": len(completed),
            "dataset_source": dataset_source,
            "mean_f1": round(avg_f1, 4),
            "mean_recall": round(avg_recall, 4),
            "mean_plan_quality": round(avg_quality, 4),
            "latest_run_id": runs[0].run_id if runs else None,
        }


def _safe_mean(values: list[float]) -> float:
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else 0.0
