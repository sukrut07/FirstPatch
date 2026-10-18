"""
FirstPatch AI — Benchmark Metrics (Phase 4)

Computes objective metrics for each task type:

FILE_RELEVANCE / ISSUE_TRACING
  - Precision@k: fraction of predicted files that are correct
  - Recall@k: fraction of expected files that were predicted
  - F1@k: harmonic mean of precision and recall
  - MRR (Mean Reciprocal Rank): rank of first correct prediction
  - Hit@k: 1 if any correct file is in top-k predictions

PLAN_QUALITY
  - step_count: number of implementation steps generated
  - has_test_step: whether a test step is included
  - has_pr_step: whether a PR step is included
  - evidence_count: number of evidence references

SETUP_DIAGNOSIS
  - correct: whether the predicted diagnosis matches expected
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# File retrieval / issue tracing metrics
# ---------------------------------------------------------------------------

@dataclass
class FileRetrievalMetrics:
    precision: float = 0.0    # TP / (TP + FP)
    recall: float = 0.0       # TP / (TP + FN)
    f1: float = 0.0           # 2 * P * R / (P + R)
    mrr: float = 0.0          # Mean Reciprocal Rank
    hit_at_1: bool = False    # Any correct in top-1
    hit_at_3: bool = False    # Any correct in top-3
    hit_at_5: bool = False    # Any correct in top-5
    predicted_count: int = 0
    expected_count: int = 0
    tp: int = 0               # True positives

    def to_dict(self) -> dict[str, float | int | bool]:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "mrr": round(self.mrr, 4),
            "hit_at_1": self.hit_at_1,
            "hit_at_3": self.hit_at_3,
            "hit_at_5": self.hit_at_5,
            "predicted_count": self.predicted_count,
            "expected_count": self.expected_count,
            "true_positives": self.tp,
        }


def _normalize(path: str) -> str:
    """Normalize file path for comparison: strip leading ./, lowercase."""
    return path.lstrip("./").lower().replace("\\", "/")


def compute_file_retrieval_metrics(
    predicted: list[str],
    expected: list[str],
) -> FileRetrievalMetrics:
    """
    Compute file retrieval metrics.

    Args:
        predicted: ordered list of file paths predicted by FirstPatch AI
        expected: ground-truth list of relevant file paths
    """
    if not expected:
        return FileRetrievalMetrics(predicted_count=len(predicted))

    pred_norm = [_normalize(p) for p in predicted]
    exp_set = {_normalize(e) for e in expected}

    tp = sum(1 for p in pred_norm if p in exp_set)
    precision = tp / len(pred_norm) if pred_norm else 0.0
    recall = tp / len(exp_set) if exp_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # MRR
    mrr = 0.0
    for rank, p in enumerate(pred_norm, start=1):
        if p in exp_set:
            mrr = 1.0 / rank
            break

    hit1 = any(p in exp_set for p in pred_norm[:1])
    hit3 = any(p in exp_set for p in pred_norm[:3])
    hit5 = any(p in exp_set for p in pred_norm[:5])

    return FileRetrievalMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        mrr=mrr,
        hit_at_1=hit1,
        hit_at_3=hit3,
        hit_at_5=hit5,
        predicted_count=len(predicted),
        expected_count=len(expected),
        tp=tp,
    )


# ---------------------------------------------------------------------------
# Plan quality metrics (structural / heuristic)
# ---------------------------------------------------------------------------

@dataclass
class PlanMetrics:
    step_count: int = 0
    has_test_step: bool = False
    has_pr_step: bool = False
    has_branch_step: bool = False
    evidence_count: int = 0
    relevant_file_count: int = 0
    ai_generated: bool = False
    uncertainty_count: int = 0
    # Composite quality score 0–1 (heuristic)
    quality_score: float = 0.0

    def to_dict(self) -> dict[str, float | int | bool]:
        return {
            "step_count": self.step_count,
            "has_test_step": self.has_test_step,
            "has_pr_step": self.has_pr_step,
            "has_branch_step": self.has_branch_step,
            "evidence_count": self.evidence_count,
            "relevant_file_count": self.relevant_file_count,
            "ai_generated": self.ai_generated,
            "uncertainty_count": self.uncertainty_count,
            "quality_score": round(self.quality_score, 4),
        }


def compute_plan_metrics(plan_dict: dict) -> PlanMetrics:
    """
    Compute structural quality metrics for a ContributionPlan dict.
    """
    steps = plan_dict.get("implementation_steps", [])
    step_texts = [s.get("description", "").lower() for s in steps]

    has_test = any("test" in t for t in step_texts)
    has_pr = any("pull request" in t or " pr" in t for t in step_texts)
    has_branch = any("branch" in t for t in step_texts)

    evidence = plan_dict.get("evidence_refs", [])
    relevant_files = plan_dict.get("relevant_files", [])
    uncertainties = plan_dict.get("uncertainties", [])
    ai_generated = plan_dict.get("ai_generated", False)

    # Heuristic quality score
    score = 0.0
    if steps:
        score += min(len(steps) / 8, 1.0) * 0.3   # up to 0.30 for steps
    if has_test:
        score += 0.2
    if has_pr:
        score += 0.15
    if has_branch:
        score += 0.10
    if evidence:
        score += min(len(evidence) / 3, 1.0) * 0.15
    if relevant_files:
        score += min(len(relevant_files) / 3, 1.0) * 0.10

    return PlanMetrics(
        step_count=len(steps),
        has_test_step=has_test,
        has_pr_step=has_pr,
        has_branch_step=has_branch,
        evidence_count=len(evidence),
        relevant_file_count=len(relevant_files),
        ai_generated=ai_generated,
        uncertainty_count=len(uncertainties),
        quality_score=min(score, 1.0),
    )


# ---------------------------------------------------------------------------
# Setup diagnosis metrics
# ---------------------------------------------------------------------------

@dataclass
class DiagnosisMetrics:
    predicted: str = ""
    expected: str = ""
    correct: bool = False
    partial_match: bool = False

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "predicted": self.predicted,
            "expected": self.expected,
            "correct": self.correct,
            "partial_match": self.partial_match,
        }


def compute_diagnosis_metrics(
    predicted_text: str, expected_category: str
) -> DiagnosisMetrics:
    """
    Evaluate setup diagnosis output against ground truth category.
    Partial match if the expected keyword appears in predicted text.
    """
    pred_lower = predicted_text.lower()
    exp_lower = expected_category.lower()

    # Direct pattern match
    correct = exp_lower in pred_lower or pred_lower == exp_lower
    partial = any(word in pred_lower for word in exp_lower.split("_"))

    return DiagnosisMetrics(
        predicted=predicted_text[:200],
        expected=expected_category,
        correct=correct,
        partial_match=partial,
    )
