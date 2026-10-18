"""API Routes for FirstPatch AI Trust Layer, Proof-Carrying Contributions,
Policy Radar, Claim Guard, Understanding Gate, Receipts, and Review Memory.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.trust.claims import Claim, Verdict
from app.services.trust.fact_store import FactStore
from app.services.trust.kernel import CheckerKernel
from app.services.trust.render import RenderedContributionPackage, TrustedRenderer
from app.services.trust.receipt import (
    ReceiptVerificationReport,
    verify_receipt_chain,
)
from app.services.policy_radar.service import PolicyRadarReport, PolicyRadarService
from app.services.claim_guard.service import ClaimGuardReport, ClaimGuardService
from app.services.understanding_gate.service import (
    Question,
    UnderstandingGateService,
    UnderstandingReceipt,
)
from app.services.trust.pr_pack import PRPackage, PRPackageGenerator
from app.services.trust.review_memory import ReviewMemoryService, ReviewThemeResult
from app.services.trust.blast_radius import BlastRadiusAnalyzer, BlastRadiusReport
from app.services.trust.fuzz import KernelMutationFuzzer, MutationSuiteReport

router = APIRouter(prefix="/api/trust", tags=["Trust & Proof-Carrying Contributions"])

# Global shared services for trust layer
fact_store = FactStore()
kernel = CheckerKernel(fact_store)
renderer = TrustedRenderer()
policy_radar = PolicyRadarService()
claim_guard = ClaimGuardService()
understanding_gate = UnderstandingGateService()
pr_pack_generator = PRPackageGenerator()
review_memory = ReviewMemoryService()
blast_radius_analyzer = BlastRadiusAnalyzer()
fuzzer = KernelMutationFuzzer(kernel)


# --- Request/Response Schemas ---

class EvaluateClaimsRequest(BaseModel):
    repository: str
    authoritative_sha: str
    claims: List[Claim]
    raw_model_explanation: Optional[str] = None


class EvaluateClaimsResponse(BaseModel):
    repository: str
    authoritative_sha: str
    verdicts: List[Verdict]
    rendered_package: Optional[RenderedContributionPackage] = None


class PolicyRadarRequest(BaseModel):
    repository: str
    files: Dict[str, str] = Field(description="Map of repo filename -> content")
    closed_prs: Optional[List[Dict[str, Any]]] = None


class ClaimGuardRequest(BaseModel):
    repository: str
    issue_data: Dict[str, Any]
    comments: Optional[List[Dict[str, Any]]] = None
    open_prs: Optional[List[Dict[str, Any]]] = None
    force_refresh: bool = False


class UnderstandingQuestionsRequest(BaseModel):
    claims: List[Claim]
    verdicts: List[Verdict]
    max_questions: int = 3


class UnderstandingEvaluateRequest(BaseModel):
    repository: str
    snapshot_sha: str
    questions: List[Question]
    user_answers: Dict[str, str]
    model_status: str = "fallback"


class PRPackRequest(BaseModel):
    repository: str
    snapshot_sha: str
    issue_number: int
    issue_title: str
    policy_report: Optional[PolicyRadarReport] = None
    rendered_plan: Optional[RenderedContributionPackage] = None
    verification_record: Optional[Dict[str, Any]] = None
    understanding_receipt: Optional[UnderstandingReceipt] = None
    receipt_events: Optional[List[Dict[str, Any]]] = None
    user_diff: Optional[str] = None
    custom_pr_template: Optional[str] = None


class ReceiptVerifyRequest(BaseModel):
    events: List[Dict[str, Any]]


class BlastRadiusRequest(BaseModel):
    target_path: str
    files: Dict[str, str]
    target_symbol: Optional[str] = None


class ReviewMemoryRequest(BaseModel):
    repository: str
    comments: List[Dict[str, Any]]
    filter_file_path: Optional[str] = None


class StoreFactRequest(BaseModel):
    repository: str
    commit_sha: str
    files: Optional[Dict[str, str]] = None
    symbols: Optional[List[Dict[str, Any]]] = None
    imports: Optional[List[Dict[str, Any]]] = None
    policies: Optional[List[Dict[str, Any]]] = None
    issues: Optional[List[Dict[str, Any]]] = None
    verification_runs: Optional[List[Dict[str, Any]]] = None


# --- Endpoints ---

@router.post("/facts/store", status_code=status.HTTP_201_CREATED)
def store_facts(req: StoreFactRequest):
    """Seed or update immutable ground-truth facts in the FactStore."""
    if req.files:
        for p, content in req.files.items():
            try:
                fact_store.store_file(req.repository, req.commit_sha, p, content)
            except ValueError as ex:
                raise HTTPException(status_code=400, detail=str(ex))

    if req.symbols:
        for s in req.symbols:
            fact_store.store_symbol(
                repo_id=req.repository,
                commit_sha=req.commit_sha,
                path=s["path"],
                symbol_name=s["symbol_name"],
                symbol_type=s["symbol_type"],
                start_line=s["start_line"],
                end_line=s["end_line"],
                confidence=s.get("confidence", "high"),
            )

    if req.imports:
        for imp in req.imports:
            fact_store.store_import(
                repo_id=req.repository,
                commit_sha=req.commit_sha,
                source_path=imp["source_path"],
                imported_module=imp["imported_module"],
                imported_name=imp.get("imported_name"),
                confidence=imp.get("confidence", "high"),
            )

    if req.policies:
        for pol in req.policies:
            fact_store.store_policy_fact(
                repo_id=req.repository,
                commit_sha=req.commit_sha,
                policy_type=pol["policy_type"],
                value=pol["value"],
                source_file=pol.get("source_file"),
                line_range=pol.get("line_range"),
                raw_text=pol.get("raw_text"),
            )

    if req.issues:
        for iss in req.issues:
            fact_store.store_issue_fact(
                repo_id=req.repository,
                issue_number=iss["issue_number"],
                state=iss["state"],
                is_assigned=iss["is_assigned"],
                assignees=iss.get("assignees", []),
                has_open_pr=iss.get("has_open_pr", False),
                claim_comment=iss.get("claim_comment"),
                timestamp=iss.get("timestamp", ""),
            )

    if req.verification_runs:
        for vr in req.verification_runs:
            fact_store.store_verification_run(
                run_id=vr["run_id"],
                repo_id=req.repository,
                commit_sha=req.commit_sha,
                driver=vr["driver"],
                status=vr["status"],
                exit_code=vr.get("exit_code"),
                output_hash=vr["output_hash"],
                passed_tests=vr.get("passed_tests", 0),
                failed_tests=vr.get("failed_tests", 0),
                timestamp=vr["timestamp"],
            )

    return {"message": "Facts stored successfully.", "repository": req.repository, "sha": req.commit_sha}


@router.post("/evaluate", response_model=EvaluateClaimsResponse)
def evaluate_claims(req: EvaluateClaimsRequest):
    """Evaluates untrusted claims deterministically against the kernel and authoritative snapshot."""
    verdicts = kernel.evaluate_claims(req.claims, req.repository, req.authoritative_sha)
    rendered = renderer.render_plan(
        repository=req.repository,
        snapshot_sha=req.authoritative_sha,
        claims=req.claims,
        verdicts=verdicts,
        raw_model_explanation=req.raw_model_explanation,
    )
    return EvaluateClaimsResponse(
        repository=req.repository,
        authoritative_sha=req.authoritative_sha,
        verdicts=verdicts,
        rendered_package=rendered,
    )


@router.post("/policy-radar", response_model=PolicyRadarReport)
def inspect_policy_radar(req: PolicyRadarRequest):
    """Scans contribution guides, AI policies, and PR metrics to determine welcomeness."""
    return policy_radar.analyze_repository_policies(
        repository=req.repository,
        files_dict=req.files,
        closed_prs=req.closed_prs,
    )


@router.post("/claim-guard", response_model=ClaimGuardReport)
def check_claim_guard(req: ClaimGuardRequest):
    """Checks if an issue is already assigned, claimed in comments, or has an open PR."""
    return claim_guard.check_issue_readiness(
        repository=req.repository,
        issue_data=req.issue_data,
        comments=req.comments,
        open_prs=req.open_prs,
        force_refresh=req.force_refresh,
    )


@router.post("/understanding/questions", response_model=List[Question])
def generate_understanding_questions(req: UnderstandingQuestionsRequest):
    """Generates comprehension questions strictly from verified claims."""
    return understanding_gate.generate_questions(
        claims=req.claims,
        verdicts=req.verdicts,
        max_questions=req.max_questions,
    )


@router.post("/understanding/evaluate", response_model=UnderstandingReceipt)
def evaluate_understanding(req: UnderstandingEvaluateRequest):
    """Deterministically evaluates contributor answers against cited code facts."""
    return understanding_gate.evaluate_answers(
        repository=req.repository,
        snapshot_sha=req.snapshot_sha,
        questions=req.questions,
        user_answers=req.user_answers,
        model_status=req.model_status,
    )


@router.post("/receipt/verify", response_model=ReceiptVerificationReport)
def verify_receipt(req: ReceiptVerifyRequest):
    """Verifies SHA-256 cryptographic hash-chain integrity of a contribution flight record."""
    return verify_receipt_chain(req.events)


@router.post("/pr-pack", response_model=PRPackage)
def generate_pr_package(req: PRPackRequest):
    """Assembles a policy-compliant PR package with verified evidence, test results, and disclosures."""
    return pr_pack_generator.generate_package(
        repository=req.repository,
        snapshot_sha=req.snapshot_sha,
        issue_number=req.issue_number,
        issue_title=req.issue_title,
        policy_report=req.policy_report,
        rendered_plan=req.rendered_plan,
        verification_record=req.verification_record,
        understanding_receipt=req.understanding_receipt,
        receipt_events=None,
        user_diff=req.user_diff,
        custom_pr_template=req.custom_pr_template,
    )


@router.post("/blast-radius", response_model=BlastRadiusReport)
def analyze_blast_radius(req: BlastRadiusRequest):
    """Traces AST imports and dependent test suites for a proposed change."""
    return blast_radius_analyzer.analyze_impact(
        target_path=req.target_path,
        files_dict=req.files,
        target_symbol=req.target_symbol,
    )


@router.post("/review-memory", response_model=List[ReviewThemeResult])
def extract_review_themes(req: ReviewMemoryRequest):
    """Extracts deterministic reviewer guidance themes supported by >=2 comment references."""
    return review_memory.analyze_comments(
        repository=req.repository,
        raw_comments=req.comments,
        filter_file_path=req.filter_file_path,
    )


@router.post("/fuzz-kernel", response_model=MutationSuiteReport)
def run_kernel_fuzz(req: EvaluateClaimsRequest):
    """Executes controlled adversarial claim mutations against the kernel to prove catch rate."""
    return fuzzer.run_mutation_suite(
        base_valid_claims=req.claims,
        repository=req.repository,
        authoritative_sha=req.authoritative_sha,
    )
