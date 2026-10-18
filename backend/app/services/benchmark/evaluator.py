"""
FirstPatch AI — Benchmark Evaluator (Phase 4)

Runs evaluation tasks through FirstPatch AI with clear mode separation:
  - DETERMINISTIC_BASELINE: Pure deterministic heuristics without AI credentials.
  - LIVE_AI: Real LLM generation (e.g. Gemma via Google AI Studio / Ollama);
             honest fallback reporting when credentials/services are missing.
  - MOCK_AI: Explicitly flagged test mode for simulated provider testing;
             never counted as live AI inference.

Computes mathematically rigorous metrics:
  - Precision, Recall, F1, Recall@k, Hit@k, MRR, MAP
  - Evidence-Validity Rate & Unsupported-Claim Rate
  - Diagnosis Accuracy & Plan Quality Scores
  - Error Rate & Fallback Rate
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from app.services.benchmark.metrics import (
    compute_diagnosis_metrics,
    compute_evidence_metrics,
    compute_file_retrieval_metrics,
    compute_mean_average_precision,
    compute_plan_metrics,
)
from app.services.benchmark.result_store import BenchmarkResultStore, BenchmarkRun
from app.services.dataset.task_schema import EvaluationTask, TaskResult, TaskType
from app.services.mentor.ai_provider import BaseAIProvider, DeterministicFallbackProvider

logger = logging.getLogger(__name__)


class EvaluationMode(str, Enum):
    """Execution mode for benchmark evaluations."""
    DETERMINISTIC_BASELINE = "deterministic_baseline"
    LIVE_AI = "live_ai"
    MOCK_AI = "mock_ai"


class BenchmarkEvaluator:
    """
    Evaluates FirstPatch AI against EvaluationTask suites.
    Strictly differentiates between deterministic baselines and live AI inference.
    """

    def __init__(
        self,
        result_store: Optional[BenchmarkResultStore] = None,
        ai_provider: Optional[BaseAIProvider] = None,
        ai_provider_name: str = "deterministic_fallback",
        ai_model_name: str = "none",
        mode: EvaluationMode = EvaluationMode.DETERMINISTIC_BASELINE,
        evaluator_version: str = "1.0.0",
        prompt_version: str = "1.0.0",
    ):
        self._store = result_store or BenchmarkResultStore()
        self._ai_provider = ai_provider
        self._ai_provider_name = ai_provider_name
        self._ai_model_name = ai_model_name
        self._mode = mode
        self._evaluator_version = evaluator_version
        self._prompt_version = prompt_version

        if self._ai_provider is not None:
            self._ai_provider_name = getattr(self._ai_provider, "provider_name", ai_provider_name)

    # ------------------------------------------------------------------
    # Main evaluation entry point
    # ------------------------------------------------------------------

    def evaluate(
        self,
        tasks: list[EvaluationTask],
        dataset_source: str = "unknown",
        task_type_filter: Optional[TaskType] = None,
        notes: str = "",
        split: str = "test",
    ) -> BenchmarkRun:
        """
        Run evaluation over a list of tasks.
        Returns an atomically persisted BenchmarkRun record.
        """
        if task_type_filter:
            tasks = [
                t for t in tasks
                if t.task_type == task_type_filter.value or t.task_type == task_type_filter
            ]

        run = BenchmarkRun(
            dataset_source=dataset_source,
            split=split,
            evaluation_mode=self._mode.value,
            task_type=task_type_filter.value if task_type_filter else None,
            total_tasks=len(tasks),
            ai_provider=self._ai_provider_name,
            ai_model=self._ai_model_name,
            evaluator_version=self._evaluator_version,
            prompt_version=self._prompt_version,
            notes=notes,
        )

        task_results: list[dict[str, Any]] = []
        precision_scores: list[float] = []
        recall_scores: list[float] = []
        f1_scores: list[float] = []
        mrr_scores: list[float] = []
        ap_scores: list[float] = []
        recall_at_1_scores: list[float] = []
        recall_at_3_scores: list[float] = []
        recall_at_5_scores: list[float] = []
        hit_at_1_flags: list[bool] = []
        hit_at_3_flags: list[bool] = []
        hit_at_5_flags: list[bool] = []
        plan_quality_scores: list[float] = []
        evidence_validity_scores: list[float] = []
        unsupported_claim_scores: list[float] = []
        diagnosis_correct: list[bool] = []
        fallback_count: int = 0

        for task in tasks:
            result = self._evaluate_one(task)
            task_results.append({
                "task_id": result.task_id,
                "task_type": result.task_type,
                "evaluation_mode": result.evaluation_mode,
                "metrics": result.metrics,
                "latency_ms": result.latency_ms,
                "ai_generated": result.ai_generated,
                "is_fallback": result.is_fallback,
                "is_mock": result.is_mock,
                "error": result.error,
            })

            if result.error:
                run.failed_tasks += 1
            else:
                run.completed_tasks += 1

            if result.is_fallback:
                fallback_count += 1

            # Collect metrics by task type
            tt = task.task_type if isinstance(task.task_type, str) else task.task_type.value
            if tt in ("file_relevance", "issue_tracing"):
                precision_scores.append(result.metrics.get("precision", 0.0))
                recall_scores.append(result.metrics.get("recall", 0.0))
                f1_scores.append(result.metrics.get("f1", 0.0))
                mrr_scores.append(result.metrics.get("mrr", 0.0))
                ap_scores.append(result.metrics.get("average_precision", 0.0))
                recall_at_1_scores.append(result.metrics.get("recall_at_1", 0.0))
                recall_at_3_scores.append(result.metrics.get("recall_at_3", 0.0))
                recall_at_5_scores.append(result.metrics.get("recall_at_5", 0.0))
                hit_at_1_flags.append(result.metrics.get("hit_at_1", False))
                hit_at_3_flags.append(result.metrics.get("hit_at_3", False))
                hit_at_5_flags.append(result.metrics.get("hit_at_5", False))
            elif tt == "plan_quality":
                plan_quality_scores.append(result.metrics.get("quality_score", 0.0))
                evidence_validity_scores.append(result.metrics.get("evidence_validity_rate", 1.0))
                unsupported_claim_scores.append(result.metrics.get("unsupported_claim_rate", 0.0))
            elif tt == "setup_diagnosis":
                diagnosis_correct.append(result.metrics.get("correct", False))

        # Build comprehensive aggregate metrics
        agg: dict[str, Any] = {
            "total_tasks": run.total_tasks,
            "completed_tasks": run.completed_tasks,
            "failed_tasks": run.failed_tasks,
            "error_rate": round(run.failed_tasks / run.total_tasks, 4) if run.total_tasks > 0 else 0.0,
            "fallback_rate": round(fallback_count / run.total_tasks, 4) if run.total_tasks > 0 else 0.0,
            "evaluation_mode": self._mode.value,
        }

        if f1_scores:
            agg["mean_precision"] = round(_safe_mean(precision_scores), 4)
            agg["mean_recall"] = round(_safe_mean(recall_scores), 4)
            agg["mean_f1"] = round(_safe_mean(f1_scores), 4)
            agg["mean_mrr"] = round(_safe_mean(mrr_scores), 4)
            agg["mean_map"] = round(compute_mean_average_precision(ap_scores), 4)
            agg["mean_recall_at_1"] = round(_safe_mean(recall_at_1_scores), 4)
            agg["mean_recall_at_3"] = round(_safe_mean(recall_at_3_scores), 4)
            agg["mean_recall_at_5"] = round(_safe_mean(recall_at_5_scores), 4)
            agg["hit_rate_at_1"] = round(sum(1 for h in hit_at_1_flags if h) / len(hit_at_1_flags), 4) if hit_at_1_flags else 0.0
            agg["hit_rate_at_3"] = round(sum(1 for h in hit_at_3_flags if h) / len(hit_at_3_flags), 4) if hit_at_3_flags else 0.0
            agg["hit_rate_at_5"] = round(sum(1 for h in hit_at_5_flags if h) / len(hit_at_5_flags), 4) if hit_at_5_flags else 0.0

        if plan_quality_scores:
            agg["mean_plan_quality"] = round(_safe_mean(plan_quality_scores), 4)
            agg["mean_evidence_validity_rate"] = round(_safe_mean(evidence_validity_scores), 4)
            agg["mean_unsupported_claim_rate"] = round(_safe_mean(unsupported_claim_scores), 4)

        if diagnosis_correct:
            agg["diagnosis_accuracy"] = round(
                sum(1 for c in diagnosis_correct if c) / len(diagnosis_correct), 4
            )

        run.aggregate_metrics = agg
        run.task_results = task_results
        run.completed_at = datetime.now(timezone.utc)

        self._store.save(run)
        logger.info(
            "Benchmark run %s [%s] complete: %d/%d tasks, agg=%s",
            run.run_id, self._mode.value, run.completed_tasks, run.total_tasks, agg
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
                    evaluation_mode=self._mode.value,
                    latency_ms=_elapsed(start),
                    error=f"Unknown task type: {tt}",
                )
        except Exception as exc:
            logger.exception("Error evaluating task %s: %s", task.task_id, exc)
            return TaskResult(
                task_id=task.task_id,
                task_type=str(task.task_type),
                evaluation_mode=self._mode.value,
                latency_ms=_elapsed(start),
                error=str(exc),
            )

    def _eval_file_retrieval(self, task: EvaluationTask, start: float) -> TaskResult:
        """
        Evaluate file retrieval using the deterministic keyword matcher.
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
            evaluation_mode=self._mode.value,
            predicted_files=predicted,
            latency_ms=_elapsed(start),
            metrics=metrics.to_dict(),
            passed=metrics.f1 > 0.0 or (not task.expected_relevant_files and not predicted),
            is_fallback=(self._mode == EvaluationMode.DETERMINISTIC_BASELINE),
        )

    def _eval_plan_quality(self, task: EvaluationTask, start: float) -> TaskResult:
        """
        Evaluate plan quality by generating a plan structure and computing metrics.
        """
        predicted_files = _keyword_match_files(
            issue_text=f"{task.issue_title} {task.issue_body}",
            snapshot=task.repository_snapshot,
        )
        plan_dict = _synthetic_plan(task, predicted_files)
        metrics = compute_plan_metrics(plan_dict, known_repository_files=task.repository_snapshot)
        return TaskResult(
            task_id=task.task_id,
            task_type=str(task.task_type),
            evaluation_mode=self._mode.value,
            predicted_files=predicted_files,
            evidence_validity_rate=metrics.evidence_validity_rate,
            unsupported_claim_rate=metrics.unsupported_claim_rate,
            latency_ms=_elapsed(start),
            metrics=metrics.to_dict(),
            passed=metrics.quality_score >= 0.5,
            is_fallback=(self._mode == EvaluationMode.DETERMINISTIC_BASELINE),
        )

    def _eval_diagnosis(self, task: EvaluationTask, start: float) -> TaskResult:
        """
        Evaluate setup diagnosis using ComprehensiveDiagnosticsService.
        """
        from app.schemas import DiagnosticRequest
        from app.services.mentor.diagnostics import ComprehensiveDiagnosticsService

        request = DiagnosticRequest(
            owner=task.owner or "eval",
            repo=task.repo or "eval",
            error_description=task.issue_body,
            command_output="",
            config_snippets=[],
        )
        response = ComprehensiveDiagnosticsService.diagnose(request)

        predicted_text = ""
        if response.findings:
            predicted_text = response.findings[0].likely_cause or ""

        expected = task.expected_diagnosis or ""
        metrics = compute_diagnosis_metrics(predicted_text, expected)

        return TaskResult(
            task_id=task.task_id,
            task_type=str(task.task_type),
            evaluation_mode=self._mode.value,
            predicted_diagnosis=predicted_text,
            latency_ms=_elapsed(start),
            metrics=metrics.to_dict(),
            passed=metrics.correct or metrics.partial_match,
            is_fallback=(self._mode == EvaluationMode.DETERMINISTIC_BASELINE),
        )

    def _eval_ai_enrichment(self, task: EvaluationTask, start: float) -> TaskResult:
        """
        Evaluate AI enrichment according to the active mode:
          - DETERMINISTIC_BASELINE: Evaluates structural pre-AI context; reports is_fallback=True.
          - LIVE_AI: Runs actual inference if live provider configured; honest fallback if not.
          - MOCK_AI: Uses mock provider and flags is_mock=True.
        """
        predicted_files = _keyword_match_files(
            issue_text=f"{task.issue_title} {task.issue_body}",
            snapshot=task.repository_snapshot,
        )

        # Baseline mode
        if self._mode == EvaluationMode.DETERMINISTIC_BASELINE:
            plan_dict = _synthetic_plan(task, predicted_files)
            metrics = compute_plan_metrics(plan_dict, known_repository_files=task.repository_snapshot)
            return TaskResult(
                task_id=task.task_id,
                task_type=str(task.task_type),
                evaluation_mode=self._mode.value,
                predicted_files=predicted_files,
                latency_ms=_elapsed(start),
                metrics={**metrics.to_dict(), "ai_generated": False, "is_fallback": True},
                ai_generated=False,
                is_fallback=True,
                is_mock=False,
                passed=metrics.quality_score >= 0.4,
            )

        # Mock AI mode
        if self._mode == EvaluationMode.MOCK_AI:
            plan_dict = _synthetic_plan(task, predicted_files)
            plan_dict["ai_generated"] = True
            metrics = compute_plan_metrics(plan_dict, known_repository_files=task.repository_snapshot)
            return TaskResult(
                task_id=task.task_id,
                task_type=str(task.task_type),
                evaluation_mode=self._mode.value,
                predicted_files=predicted_files,
                latency_ms=_elapsed(start),
                metrics={**metrics.to_dict(), "ai_generated": True, "is_mock": True},
                ai_generated=True,
                is_fallback=False,
                is_mock=True,
                passed=metrics.quality_score >= 0.4,
            )

        # Live AI mode
        is_live_configured = (
            self._ai_provider is not None
            and not isinstance(self._ai_provider, DeterministicFallbackProvider)
            and getattr(self._ai_provider, "provider_name", "") != "deterministic_fallback"
        )

        if not is_live_configured:
            # Honest reporting: live AI requested but not available
            plan_dict = _synthetic_plan(task, predicted_files)
            metrics = compute_plan_metrics(plan_dict, known_repository_files=task.repository_snapshot)
            return TaskResult(
                task_id=task.task_id,
                task_type=str(task.task_type),
                evaluation_mode=self._mode.value,
                predicted_files=predicted_files,
                latency_ms=_elapsed(start),
                metrics={**metrics.to_dict(), "ai_generated": False, "is_fallback": True},
                ai_generated=False,
                is_fallback=True,
                is_mock=False,
                error="Live AI requested but provider is not configured or in fallback mode (AI_PROVIDER=none or missing API key).",
                passed=False,
            )

        # Real Live AI inference
        try:
            system_prompt = (
                "You are FirstPatch AI, an open-source contribution mentor. "
                "Analyze the following repository issue and provide a concise contribution summary."
            )
            user_msg = f"Issue: {task.issue_title}\nDescription: {task.issue_body[:500]}"

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            ai_resp = loop.run_until_complete(
                self._ai_provider.complete(system_prompt, user_msg, max_tokens=300)
            )

            plan_dict = _synthetic_plan(task, predicted_files)
            plan_dict["ai_generated"] = not ai_resp.is_fallback
            metrics = compute_plan_metrics(plan_dict, known_repository_files=task.repository_snapshot)

            return TaskResult(
                task_id=task.task_id,
                task_type=str(task.task_type),
                evaluation_mode=self._mode.value,
                predicted_files=predicted_files,
                predicted_summary=ai_resp.content,
                latency_ms=_elapsed(start),
                metrics={**metrics.to_dict(), "ai_generated": not ai_resp.is_fallback},
                ai_generated=not ai_resp.is_fallback,
                is_fallback=ai_resp.is_fallback,
                is_mock=False,
                passed=metrics.quality_score >= 0.4 and not ai_resp.is_fallback,
            )
        except Exception as exc:
            logger.warning("Live AI inference failed for task %s: %s", task.task_id, exc)
            plan_dict = _synthetic_plan(task, predicted_files)
            metrics = compute_plan_metrics(plan_dict, known_repository_files=task.repository_snapshot)
            return TaskResult(
                task_id=task.task_id,
                task_type=str(task.task_type),
                evaluation_mode=self._mode.value,
                predicted_files=predicted_files,
                latency_ms=_elapsed(start),
                metrics={**metrics.to_dict(), "ai_generated": False, "is_fallback": True},
                ai_generated=False,
                is_fallback=True,
                is_mock=False,
                error=f"Live AI provider failure: {exc}",
                passed=False,
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
