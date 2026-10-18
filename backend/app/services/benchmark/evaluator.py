"""
FirstPatch AI — Benchmark Evaluator (Phase 4)

Runs evaluation tasks through the FirstPatch AI pipeline and
computes objective metrics.

Design constraints:
- Uses the deterministic file-matching engine (no AI required for tests)
- AI enrichment is measured separately and marked ai_generated=True
- All evaluation is non-destructive (read-only against GitHub API)
- Results are persisted to BenchmarkResultStore
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.benchmark.metrics import (
    compute_diagnosis_metrics,
    compute_file_retrieval_metrics,
    compute_plan_metrics,
)
from app.services.benchmark.result_store import BenchmarkResultStore, BenchmarkRun
from app.services.dataset.task_schema import EvaluationTask, TaskResult, TaskType

logger = logging.getLogger(__name__)


class BenchmarkEvaluator:
    """
    Evaluates FirstPatch AI against a list of EvaluationTask instances.

    For file_relevance and issue_tracing tasks, uses the keyword-based
    file matcher from MentorService (deterministic, no API required).

    For plan_quality tasks, evaluates the structural quality of the
    generated ContributionPlan.

    For setup_diagnosis tasks, evaluates the DiagnosticsService output.
    """

    def __init__(
        self,
        result_store: Optional[BenchmarkResultStore] = None,
        ai_provider_name: str = "deterministic_fallback",
        ai_model_name: str = "none",
    ):
        self._store = result_store or BenchmarkResultStore()
        self._ai_provider_name = ai_provider_name
        self._ai_model_name = ai_model_name

    # ------------------------------------------------------------------
    # Main evaluation entry point
    # ------------------------------------------------------------------

    def evaluate(
        self,
        tasks: list[EvaluationTask],
        dataset_source: str = "unknown",
        task_type_filter: Optional[TaskType] = None,
        notes: str = "",
    ) -> BenchmarkRun:
        """
        Run evaluation over a list of tasks.
        Returns a persisted BenchmarkRun.
        """
        if task_type_filter:
            tasks = [t for t in tasks if t.task_type == task_type_filter.value or t.task_type == task_type_filter]

        run = BenchmarkRun(
            dataset_source=dataset_source,
            task_type=task_type_filter.value if task_type_filter else None,
            total_tasks=len(tasks),
            ai_provider=self._ai_provider_name,
            ai_model=self._ai_model_name,
            notes=notes,
        )

        task_results: list[dict[str, Any]] = []
        f1_scores: list[float] = []
        recall_scores: list[float] = []
        mrr_scores: list[float] = []
        plan_quality_scores: list[float] = []
        diagnosis_correct: list[bool] = []

        for task in tasks:
            result = self._evaluate_one(task)
            task_results.append({
                "task_id": result.task_id,
                "task_type": result.task_type,
                "metrics": result.metrics,
                "latency_ms": result.latency_ms,
                "ai_generated": result.ai_generated,
                "error": result.error,
            })

            if result.error:
                run.failed_tasks += 1
            else:
                run.completed_tasks += 1

            # Collect aggregate metrics by task type
            tt = task.task_type if isinstance(task.task_type, str) else task.task_type.value
            if tt in ("file_relevance", "issue_tracing"):
                f1_scores.append(result.metrics.get("f1", 0.0))
                recall_scores.append(result.metrics.get("recall", 0.0))
                mrr_scores.append(result.metrics.get("mrr", 0.0))
            elif tt == "plan_quality":
                plan_quality_scores.append(result.metrics.get("quality_score", 0.0))
            elif tt == "setup_diagnosis":
                diagnosis_correct.append(result.metrics.get("correct", False))

        # Aggregate
        agg: dict[str, Any] = {
            "total_tasks": run.total_tasks,
            "completed_tasks": run.completed_tasks,
            "failed_tasks": run.failed_tasks,
        }
        if f1_scores:
            agg["mean_f1"] = round(_safe_mean(f1_scores), 4)
            agg["mean_recall"] = round(_safe_mean(recall_scores), 4)
            agg["mean_mrr"] = round(_safe_mean(mrr_scores), 4)
        if plan_quality_scores:
            agg["mean_plan_quality"] = round(_safe_mean(plan_quality_scores), 4)
        if diagnosis_correct:
            agg["diagnosis_accuracy"] = round(
                sum(1 for c in diagnosis_correct if c) / len(diagnosis_correct), 4
            )

        run.aggregate_metrics = agg
        run.task_results = task_results
        run.completed_at = datetime.now(timezone.utc)

        self._store.save(run)
        logger.info(
            "Benchmark run %s complete: %d/%d tasks, agg=%s",
            run.run_id, run.completed_tasks, run.total_tasks, agg
        )
        return run

    # ------------------------------------------------------------------
    # Per-task evaluation
    # ------------------------------------------------------------------

    def _evaluate_one(self, task: EvaluationTask) -> TaskResult:
        """Evaluate a single task. Returns TaskResult with metrics."""
        start = time.perf_counter()
        try:
            tt = task.task_type if isinstance(task.task_type, str) else task.task_type.value

            if tt in ("file_relevance", "issue_tracing"):
                return self._eval_file_retrieval(task, start)
            elif tt == "plan_quality":
                return self._eval_plan_quality(task, start)
            elif tt == "setup_diagnosis":
                return self._eval_diagnosis(task, start)
            elif tt == "ai_enrichment":
                return self._eval_ai_enrichment(task, start)
            else:
                return TaskResult(
                    task_id=task.task_id,
                    task_type=tt,
                    latency_ms=_elapsed(start),
                    error=f"Unknown task type: {tt}",
                )
        except Exception as exc:
            logger.exception("Error evaluating task %s: %s", task.task_id, exc)
            return TaskResult(
                task_id=task.task_id,
                task_type=str(task.task_type),
                latency_ms=_elapsed(start),
                error=str(exc),
            )

    def _eval_file_retrieval(self, task: EvaluationTask, start: float) -> TaskResult:
        """
        Evaluate file retrieval using the deterministic keyword matcher.
        Simulates what MentorService._identify_relevant_files() would produce
        given only the task's repository_snapshot and issue text.
        """
        predicted = _keyword_match_files(
            issue_text=f"{task.issue_title} {task.issue_body}",
            snapshot=task.repository_snapshot,
        )
        metrics = compute_file_retrieval_metrics(
            predicted=predicted,
            expected=task.expected_relevant_files,
        )
        return TaskResult(
            task_id=task.task_id,
            task_type=str(task.task_type),
            predicted_files=predicted,
            latency_ms=_elapsed(start),
            metrics=metrics.to_dict(),
            passed=metrics.f1 > 0.0,
        )

    def _eval_plan_quality(self, task: EvaluationTask, start: float) -> TaskResult:
        """
        Evaluate plan quality by generating a minimal synthetic plan dict
        (deterministic, no API required).
        """
        # Build a minimal plan dict representing what our planner would produce
        predicted_files = _keyword_match_files(
            issue_text=f"{task.issue_title} {task.issue_body}",
            snapshot=task.repository_snapshot,
        )
        plan_dict = _synthetic_plan(task, predicted_files)
        metrics = compute_plan_metrics(plan_dict)
        return TaskResult(
            task_id=task.task_id,
            task_type=str(task.task_type),
            predicted_files=predicted_files,
            latency_ms=_elapsed(start),
            metrics=metrics.to_dict(),
            passed=metrics.quality_score >= 0.5,
        )

    def _eval_diagnosis(self, task: EvaluationTask, start: float) -> TaskResult:
        """
        Evaluate setup diagnosis by running the deterministic pattern matcher.
        Uses ComprehensiveDiagnosticsService with a DiagnosticRequest.
        """
        from app.schemas import DiagnosticRequest
        from app.services.mentor.diagnostics import ComprehensiveDiagnosticsService

        request = DiagnosticRequest(
            owner="eval",
            repo="eval",
            error_description=task.issue_body,
            command_output="",
            config_snippets=[],
        )
        response = ComprehensiveDiagnosticsService.diagnose(request)

        # Use the primary finding's likely_cause as the predicted category
        predicted_text = ""
        if response.findings:
            predicted_text = response.findings[0].likely_cause or ""

        expected = task.expected_diagnosis or ""
        metrics = compute_diagnosis_metrics(predicted_text, expected)

        return TaskResult(
            task_id=task.task_id,
            task_type=str(task.task_type),
            predicted_diagnosis=predicted_text,
            latency_ms=_elapsed(start),
            metrics=metrics.to_dict(),
            passed=metrics.correct or metrics.partial_match,
        )

    def _eval_ai_enrichment(self, task: EvaluationTask, start: float) -> TaskResult:
        """
        For AI enrichment tasks: evaluate structural quality of the issue context
        (no live AI call — measures pre-AI context quality).
        """
        predicted_files = _keyword_match_files(
            issue_text=f"{task.issue_title} {task.issue_body}",
            snapshot=task.repository_snapshot,
        )
        plan_dict = _synthetic_plan(task, predicted_files)
        metrics = compute_plan_metrics(plan_dict)
        return TaskResult(
            task_id=task.task_id,
            task_type=str(task.task_type),
            predicted_files=predicted_files,
            latency_ms=_elapsed(start),
            metrics={**metrics.to_dict(), "ai_generated": False, "is_fallback": True},
            is_fallback=True,
            passed=metrics.quality_score >= 0.4,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _keyword_match_files(issue_text: str, snapshot: list[str]) -> list[str]:
    """
    Deterministic keyword-based file matching (mirrors MentorService logic).
    Returns up to 5 file paths ranked by keyword match count.
    """
    import re
    text_lower = issue_text.lower()
    stop_words = {
        "the", "a", "an", "is", "it", "in", "on", "at", "to", "for",
        "of", "and", "or", "but", "not", "with", "this", "that", "have",
        "has", "be", "are", "was", "were", "will", "would", "could", "should",
        "when", "where", "how", "what", "why", "which", "who",
    }
    words = re.findall(r"\b[a-z][a-z_]{2,}\b", text_lower)
    keywords = [w for w in words if w not in stop_words and len(w) > 3]

    # Explicit file mentions
    relevant: list[str] = []
    for ef in re.findall(r"[\w/\.-]+\.[a-zA-Z0-9]+", text_lower):
        for known in snapshot:
            if known.lower().endswith(ef) or ef in known.lower():
                if known not in relevant:
                    relevant.append(known)

    # Keyword scoring
    scored: list[tuple[str, int]] = []
    for path in snapshot:
        if path in relevant:
            continue
        path_lower = path.lower()
        score = sum(1 for kw in keywords if kw in path_lower)
        if score > 0:
            scored.append((path, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    for p, _ in scored:
        if len(relevant) >= 5:
            break
        relevant.append(p)

    return relevant[:5]


def _synthetic_plan(task: EvaluationTask, files: list[str]) -> dict:
    """Build a minimal plan dict for plan quality evaluation."""
    has_tests = any("test" in f.lower() for f in task.repository_snapshot)
    steps = [
        {"description": "Read the full issue and all comments carefully"},
        {"description": "Fork, clone, and set up your development environment"},
        {"description": f"Create a new branch: git checkout -b fix/issue-{task.issue_number}"},
    ]
    if files:
        steps.append({"description": f"Locate and read relevant source files: {', '.join(files[:3])}"})
    steps.append({"description": "Implement the fix or feature as described in the issue"})
    if has_tests:
        steps.append({"description": "Add or update tests to cover your change"})
    steps.append({"description": "Run the test suite and verify all existing tests pass"})
    steps.append({"description": f"Open a pull request referencing issue #{task.issue_number}"})

    return {
        "implementation_steps": steps,
        "relevant_files": files,
        "evidence_refs": [{"type": "issue"}, {"type": "file"}] if files else [{"type": "issue"}],
        "uncertainties": [],
        "ai_generated": False,
    }


def _elapsed(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _safe_mean(values: list[float]) -> float:
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else 0.0
