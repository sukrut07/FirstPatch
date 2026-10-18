"""Abstention and Evidence Confidence Decision Engine.

Allows FirstPatch AI to explicitly decline to recommend actions when evidence is
statistically or structurally insufficient, preventing hallucinated recommendations.
Also supports risk-coverage evaluation across varying threshold percentiles.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CandidateRecommendation(BaseModel):
    file_path: str
    symbol_name: Optional[str] = None
    retrieval_score: float
    has_verified_evidence: bool = False
    evidence_ids: List[str] = Field(default_factory=list)


class AbstentionDecision(BaseModel):
    should_abstain: bool
    confidence_score: float
    score_margin: float
    verified_evidence_ratio: float
    selected_candidate: Optional[CandidateRecommendation] = None
    top_candidates: List[CandidateRecommendation] = Field(default_factory=list)
    reason: str


class RiskCoveragePoint(BaseModel):
    coverage_level: float  # e.g. 1.0, 0.7, 0.5
    answered_tasks_count: int
    total_tasks_count: int
    metric_name: str
    metric_value: float


class AbstentionEngine:
    def __init__(
        self,
        min_score_threshold: float = 0.25,
        min_margin_threshold: float = 0.05,
        min_verified_ratio: float = 0.5,
    ):
        self.min_score_threshold = min_score_threshold
        self.min_margin_threshold = min_margin_threshold
        self.min_verified_ratio = min_verified_ratio

    def evaluate_recommendations(
        self,
        candidates: List[CandidateRecommendation],
    ) -> AbstentionDecision:
        if not candidates:
            return AbstentionDecision(
                should_abstain=True,
                confidence_score=0.0,
                score_margin=0.0,
                verified_evidence_ratio=0.0,
                selected_candidate=None,
                top_candidates=[],
                reason="Unable to identify any relevant candidate locations in the repository snapshot.",
            )

        # Sort candidates descending by score
        sorted_cand = sorted(candidates, key=lambda c: c.retrieval_score, reverse=True)
        top1 = sorted_cand[0]
        top2 = sorted_cand[1] if len(sorted_cand) > 1 else None

        score_margin = (top1.retrieval_score - top2.retrieval_score) if top2 else top1.retrieval_score

        top_k = sorted_cand[:3]
        verified_count = sum(1 for c in top_k if c.has_verified_evidence)
        verified_ratio = verified_count / len(top_k)

        # Confidence heuristic from empirical signals
        confidence = (0.5 * min(1.0, top1.retrieval_score)) + (0.3 * min(1.0, score_margin * 2.0)) + (0.2 * verified_ratio)

        # Abstention decision
        should_abstain = False
        reasons = []

        if top1.retrieval_score < self.min_score_threshold:
            should_abstain = True
            reasons.append(f"Top retrieval score ({top1.retrieval_score:.2f}) below threshold ({self.min_score_threshold:.2f}).")

        if top2 and score_margin < self.min_margin_threshold and not top1.has_verified_evidence:
            should_abstain = True
            reasons.append(f"Top candidates ambiguous (margin {score_margin:.2f} < {self.min_margin_threshold:.2f}) without verified evidence.")

        if verified_ratio < self.min_verified_ratio and not top1.has_verified_evidence:
            should_abstain = True
            reasons.append("Insufficient verified repository evidence supporting top candidate.")

        if should_abstain:
            reason_str = (
                "Unable to identify a sufficiently supported code location. "
                + " ".join(reasons)
                + " Inspect top candidates manually or ask maintainers for clarification."
            )
            selected = None
        else:
            reason_str = f"Sufficiently supported candidate identified: '{top1.file_path}' (confidence: {confidence:.2f})."
            selected = top1

        return AbstentionDecision(
            should_abstain=should_abstain,
            confidence_score=round(confidence, 3),
            score_margin=round(score_margin, 3),
            verified_evidence_ratio=round(verified_ratio, 3),
            selected_candidate=selected,
            top_candidates=top_k,
            reason=reason_str,
        )

    @staticmethod
    def evaluate_risk_coverage(
        task_evaluations: List[Dict[str, Any]],
        coverage_levels: Optional[List[float]] = None,
    ) -> List[RiskCoveragePoint]:
        """Calculates retrieval metric (e.g. Hit@1 / Recall) across given coverage percentiles."""
        if coverage_levels is None:
            coverage_levels = [1.0, 0.7, 0.5]

        total = len(task_evaluations)
        if total == 0:
            return []

        # Sort tasks by confidence descending
        sorted_tasks = sorted(task_evaluations, key=lambda t: t.get("confidence", 0.0), reverse=True)

        points: List[RiskCoveragePoint] = []
        for cov in coverage_levels:
            k = max(1, int(round(total * cov)))
            subset = sorted_tasks[:k]
            hits = sum(1 for t in subset if t.get("is_hit", False))
            hit_rate = round(hits / k, 3)

            points.append(
                RiskCoveragePoint(
                    coverage_level=cov,
                    answered_tasks_count=k,
                    total_tasks_count=total,
                    metric_name="HitRate@1",
                    metric_value=hit_rate,
                )
            )

        return points
