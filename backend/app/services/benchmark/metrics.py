"""
FirstPatch AI — Benchmark Metrics (Phase 4)

Computes mathematically rigorous, independent metrics for FirstPatch AI tasks:

FILE RETRIEVAL & ISSUE TRACING:
  - Precision: TP / |predicted|
  - Recall: TP / |expected|
  - F1: 2 * Precision * Recall / (Precision + Recall)
  - Recall@k (k=1, 3, 5): TP@k / |expected|
  - Hit@k (k=1, 3, 5): 1 if any correct file in top-k
  - MRR (Reciprocal Rank): 1 / rank of first relevant file
  - AP (Average Precision): sum(P@k * rel(k)) / |expected|
  - MAP (Mean Average Precision): mean(AP) across all queries

EVIDENCE & HALLUCINATION METRICS:
  - Evidence-Validity Rate: valid_evidence_refs / total_evidence_refs
  - Unsupported-Claim Rate: unsupported_claims / total_claims

PLAN QUALITY:
  - Structural completeness, presence of test/PR steps, evidence density

SETUP DIAGNOSIS:
  - Exact match and partial category alignment

VERIFICATION RELIABILITY:
  - False verification-pass rate: fraction of runs claiming pass without valid tests
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence


# ---------------------------------------------------------------------------
# Path normalization
# ---------------------------------------------------------------------------

def _normalize(path: str) -> str:
    """Normalize file path for exact comparison: strip leading ./, lowercase, forward slash."""
    return path.strip().lstrip("./").lower().replace("\\", "/")


# ---------------------------------------------------------------------------
# File retrieval / issue tracing metrics
# ---------------------------------------------------------------------------

@dataclass
class FileRetrievalMetrics:
    """
    Evaluation metrics for file relevance prediction and issue-to-code tracing.

    Formulas and Denominators:
      - Precision = TP / |predicted|               (0.0 if |predicted| == 0)
      - Recall    = TP / |expected|                (0.0 if |expected| == 0)
      - F1        = 2*P*R / (P + R)                (0.0 if P+R == 0)
      - Recall@k  = TP@k / |expected|              (0.0 if |expected| == 0)
      - Hit@k     = 1 if any TP in top-k else 0
      - MRR       = 1 / rank of first TP           (0.0 if no TP in predictions)
      - AP        = sum(P@k * rel(k)) / |expected| (0.0 if |expected| == 0)

    Expected Range: [0.0, 1.0] for all floating point metrics.
    """
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    mrr: float = 0.0
    average_precision: float = 0.0    # Single-task AP for MAP computation
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    recall_at_5: float = 0.0
    hit_at_1: bool = False
    hit_at_3: bool = False
    hit_at_5: bool = False
    predicted_count: int = 0
    expected_count: int = 0
    tp: int = 0                       # Total True Positives

    def to_dict(self) -> dict[str, float | int | bool]:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "mrr": round(self.mrr, 4),
            "average_precision": round(self.average_precision, 4),
            "recall_at_1": round(self.recall_at_1, 4),
            "recall_at_3": round(self.recall_at_3, 4),
            "recall_at_5": round(self.recall_at_5, 4),
            "hit_at_1": self.hit_at_1,
            "hit_at_3": self.hit_at_3,
            "hit_at_5": self.hit_at_5,
            "predicted_count": self.predicted_count,
            "expected_count": self.expected_count,
            "true_positives": self.tp,
        }


def compute_file_retrieval_metrics(
    predicted: Sequence[str],
    expected: Sequence[str],
) -> FileRetrievalMetrics:
    """
    Compute full file retrieval metrics against independent ground truth.

    Args:
        predicted: ordered list of file paths predicted by FirstPatch AI
        expected: ground-truth list of relevant file paths
    """
    pred_count = len(predicted)
    exp_count = len(expected)

    if exp_count == 0:
        return FileRetrievalMetrics(predicted_count=pred_count, expected_count=0)

    pred_norm = [_normalize(p) for p in predicted]
    exp_set = {_normalize(e) for e in expected}

    # True positives overall
    tp = sum(1 for p in pred_norm if p in exp_set)
    precision = tp / pred_count if pred_count > 0 else 0.0
    recall = tp / exp_count if exp_count > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # MRR (Reciprocal Rank of first relevant file)
    mrr = 0.0
    for rank, p in enumerate(pred_norm, start=1):
        if p in exp_set:
            mrr = 1.0 / rank
            break

    # Recall@k and Hit@k helper
    def _tp_at_k(k: int) -> int:
        return sum(1 for p in pred_norm[:k] if p in exp_set)

    tp_1 = _tp_at_k(1)
    tp_3 = _tp_at_k(3)
    tp_5 = _tp_at_k(5)

    recall_at_1 = tp_1 / exp_count
    recall_at_3 = tp_3 / exp_count
    recall_at_5 = tp_5 / exp_count

    hit1 = tp_1 > 0
    hit3 = tp_3 > 0
    hit5 = tp_5 > 0

    # Average Precision (AP):
    # AP = (1 / |expected|) * sum_{k=1}^{|predicted|} (P@k * rel(k))
    cum_tp = 0
    sum_prec = 0.0
    for k, p in enumerate(pred_norm, start=1):
        if p in exp_set:
            cum_tp += 1
            precision_at_k = cum_tp / k
            sum_prec += precision_at_k

    average_precision = sum_prec / exp_count if exp_count > 0 else 0.0

    return FileRetrievalMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        mrr=mrr,
        average_precision=average_precision,
        recall_at_1=recall_at_1,
        recall_at_3=recall_at_3,
        recall_at_5=recall_at_5,
        hit_at_1=hit1,
        hit_at_3=hit3,
        hit_at_5=hit5,
        predicted_count=pred_count,
        expected_count=exp_count,
        tp=tp,
    )


def compute_mean_average_precision(ap_scores: Sequence[float]) -> float:
    """Compute MAP across multiple queries. Range [0.0, 1.0]."""
    if not ap_scores:
        return 0.0
    return sum(ap_scores) / len(ap_scores)


# ---------------------------------------------------------------------------
# Evidence validity & hallucination metrics
# ---------------------------------------------------------------------------

@dataclass
class EvidenceMetrics:
    """
    Measures grounding and absence of hallucination in AI/deterministic plans.

    Definitions:
      - evidence_validity_rate: valid_evidence / total_evidence (1.0 if total == 0)
      - unsupported_claim_rate: 1.0 - evidence_validity_rate (0.0 if total == 0)
    """
    total_citations: int = 0
    valid_citations: int = 0
    evidence_validity_rate: float = 1.0
    unsupported_claim_rate: float = 0.0

    def to_dict(self) -> dict[str, float | int]:
        return {
            "total_citations": self.total_citations,
            "valid_citations": self.valid_citations,
            "evidence_validity_rate": round(self.evidence_validity_rate, 4),
            "unsupported_claim_rate": round(self.unsupported_claim_rate, 4),
        }


def compute_evidence_metrics(
    cited_files: Sequence[str],
    known_repository_files: Sequence[str],
) -> EvidenceMetrics:
    """
    Compute evidence validity and unsupported claim rates.

    Args:
        cited_files: files or symbols referenced by the generated plan
        known_repository_files: authoritative repository file inventory
    """
    if not cited_files:
        return EvidenceMetrics(
            total_citations=0,
            valid_citations=0,
            evidence_validity_rate=1.0,
            unsupported_claim_rate=0.0,
        )

    known_set = {_normalize(f) for f in known_repository_files}
    valid = sum(1 for c in cited_files if _normalize(c) in known_set)
    total = len(cited_files)

    validity_rate = valid / total if total > 0 else 1.0
    unsupported_rate = (total - valid) / total if total > 0 else 0.0

    return EvidenceMetrics(
        total_citations=total,
        valid_citations=valid,
        evidence_validity_rate=validity_rate,
        unsupported_claim_rate=unsupported_rate,
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
    evidence_validity_rate: float = 1.0
    unsupported_claim_rate: float = 0.0
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
            "evidence_validity_rate": round(self.evidence_validity_rate, 4),
            "unsupported_claim_rate": round(self.unsupported_claim_rate, 4),
            "quality_score": round(self.quality_score, 4),
        }


def compute_plan_metrics(
    plan_dict: dict,
    known_repository_files: Optional[Sequence[str]] = None,
) -> PlanMetrics:
    """
    Compute structural quality metrics for a ContributionPlan dictionary.
    Optionally evaluates evidence grounding if known_repository_files is provided.
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

    # Evidence validity calculation
    ev_metrics = EvidenceMetrics()
    if known_repository_files is not None and relevant_files:
        ev_metrics = compute_evidence_metrics(relevant_files, known_repository_files)

    # Heuristic quality score [0.0, 1.0]
    score = 0.0
    if steps:
        score += min(len(steps) / 8, 1.0) * 0.25   # up to 0.25 for steps
    if has_test:
        score += 0.20
    if has_pr:
        score += 0.15
    if has_branch:
        score += 0.10
    if evidence:
        score += min(len(evidence) / 3, 1.0) * 0.15
    if relevant_files:
        score += min(len(relevant_files) / 3, 1.0) * 0.15

    return PlanMetrics(
        step_count=len(steps),
        has_test_step=has_test,
        has_pr_step=has_pr,
        has_branch_step=has_branch,
        evidence_count=len(evidence),
        relevant_file_count=len(relevant_files),
        ai_generated=ai_generated,
        uncertainty_count=len(uncertainties),
        evidence_validity_rate=ev_metrics.evidence_validity_rate,
        unsupported_claim_rate=ev_metrics.unsupported_claim_rate,
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
    partial = any(word in pred_lower for word in exp_lower.split("_") if len(word) > 2)

    return DiagnosisMetrics(
        predicted=predicted_text[:200],
        expected=expected_category,
        correct=correct,
        partial_match=partial,
    )


# ---------------------------------------------------------------------------
# Verification reliability metrics
# ---------------------------------------------------------------------------

def compute_false_verification_pass_rate(runs: Sequence[dict]) -> float:
    """
    Calculate the rate of runs that reported PASSED without genuine test validation.

    A false pass occurs when:
      - Status is PASSED, but total_tests == 0 (no tests actually ran)
      - Status is PASSED, but failed_tests > 0 (contradictory count)
      - Status is PASSED, but execution was mocked without explicit test isolation
    """
    if not runs:
        return 0.0

    false_passes = 0
    for r in runs:
        status = r.get("status", "")
        counts = r.get("test_counts", {})
        total = counts.get("total", 0)
        failed = counts.get("failed", 0)
        driver_status = r.get("driver_status", "AVAILABLE")

        if status == "PASSED":
            if total == 0 or failed > 0 or driver_status == "UNAVAILABLE":
                false_passes += 1

    return false_passes / len(runs)
