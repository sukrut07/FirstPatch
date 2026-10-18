"""Contributor Understanding Gate Service.

Generates repository-specific comprehension questions strictly from VERIFIED claims
and evaluates answers through deterministic grounding checks and optional semantic rubrics.
"""

from typing import Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field
from app.services.trust.claims import Claim, ClaimType, Verdict, VerdictStatus


class Question(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid4()))
    prompt: str
    target_evidence_ids: List[str] = Field(default_factory=list)
    claim_id: str
    grounding_keywords: List[str] = Field(default_factory=list)


class AnswerEvaluation(BaseModel):
    question_id: str
    user_answer: str
    grounded: bool
    matched_keywords: List[str] = Field(default_factory=list)
    semantic_score: Optional[float] = None
    evaluation_notes: str


class UnderstandingReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: str(uuid4()))
    repository: str
    snapshot_sha: str
    questions: List[Question]
    evaluations: List[AnswerEvaluation]
    grounded_count: int
    total_questions: int
    model_status: str  # "active", "fallback", "mock", "unavailable"
    summary: str
    cautionary_note: str = "This score reflects grounding in repository facts, not a certification of human comprehension."


class UnderstandingGateService:
    def generate_questions(
        self,
        claims: List[Claim],
        verdicts: List[Verdict],
        max_questions: int = 3,
    ) -> List[Question]:
        """Generates questions strictly from VERIFIED claims."""
        verdict_by_id = {v.claim_id: v for v in verdicts}
        questions: List[Question] = []

        for c in claims:
            v = verdict_by_id.get(c.claim_id)
            if not v or v.status != VerdictStatus.VERIFIED:
                continue

            witness = v.witness or {}
            args = c.arguments

            if c.claim_type == ClaimType.SYMBOL_IN_FILE:
                path = witness.get("path", args.get("path", "file"))
                sym = witness.get("symbol_name", args.get("symbol_name", "symbol"))
                st = witness.get("start_line")
                end = witness.get("end_line")
                line_info = f" around lines {st}–{end}" if st and end else ""
                questions.append(
                    Question(
                        prompt=f"In file `{path}`, how does symbol `{sym}`{line_info} relate to the proposed contribution?",
                        target_evidence_ids=c.evidence_refs,
                        claim_id=c.claim_id,
                        grounding_keywords=[sym.lower(), path.split("/")[-1].lower()],
                    )
                )

            elif c.claim_type == ClaimType.TEST_IMPORTS:
                test_path = witness.get("test_path", args.get("test_path"))
                target = witness.get("target_module", args.get("target_module"))
                questions.append(
                    Question(
                        prompt=f"Test suite `{test_path}` imports `{target}`. What specific edge cases does this test exercise?",
                        target_evidence_ids=c.evidence_refs,
                        claim_id=c.claim_id,
                        grounding_keywords=[target.lower(), test_path.split("/")[-1].lower()],
                    )
                )

            elif c.claim_type == ClaimType.IMPORTED_BY:
                src = witness.get("source_path", args.get("source_path"))
                mod = witness.get("imported_module", args.get("imported_module"))
                questions.append(
                    Question(
                        prompt=f"Why is `{src}` importing `{mod}`, and how could changing `{mod}` impact `{src}`?",
                        target_evidence_ids=c.evidence_refs,
                        claim_id=c.claim_id,
                        grounding_keywords=[mod.lower(), src.split("/")[-1].lower()],
                    )
                )

            elif c.claim_type == ClaimType.FILE_EXISTS:
                path = witness.get("path", args.get("path", "file"))
                questions.append(
                    Question(
                        prompt=f"Why is `{path}` relevant to this issue, and what role does it play in the repository?",
                        target_evidence_ids=c.evidence_refs,
                        claim_id=c.claim_id,
                        grounding_keywords=[path.split("/")[-1].lower()],
                    )
                )

            if len(questions) >= max_questions:
                break

        # Fallback if fewer than 3 verified items
        if not questions:
            questions.append(
                Question(
                    prompt="Describe the core problem described in the issue and identify the main module responsible.",
                    target_evidence_ids=[],
                    claim_id="fallback_generic",
                    grounding_keywords=["issue", "module", "fix"],
                )
            )

        return questions[:max_questions]

    def evaluate_answers(
        self,
        repository: str,
        snapshot_sha: str,
        questions: List[Question],
        user_answers: Dict[str, str],
        model_status: str = "fallback",
    ) -> UnderstandingReceipt:
        evaluations: List[AnswerEvaluation] = []
        grounded_count = 0

        for q in questions:
            ans = user_answers.get(q.question_id, "").strip()
            ans_lower = ans.lower()

            matched = [k for k in q.grounding_keywords if k in ans_lower]
            # Grounded if at least 1 keyword present and answer length > 15 chars
            is_grounded = len(matched) >= 1 and len(ans) >= 15

            if is_grounded:
                grounded_count += 1
                note = f"Answer mentions relevant repository facts: {', '.join(matched)}."
            else:
                note = "Answer did not reference verified file or symbol keywords from cited evidence."

            evaluations.append(
                AnswerEvaluation(
                    question_id=q.question_id,
                    user_answer=ans,
                    grounded=is_grounded,
                    matched_keywords=matched,
                    semantic_score=1.0 if is_grounded else 0.0,
                    evaluation_notes=note,
                )
            )

        total = len(questions)
        summary = f"{grounded_count} of {total} answers were grounded in cited code."

        return UnderstandingReceipt(
            repository=repository,
            snapshot_sha=snapshot_sha,
            questions=questions,
            evaluations=evaluations,
            grounded_count=grounded_count,
            total_questions=total,
            model_status=model_status,
            summary=summary,
        )
