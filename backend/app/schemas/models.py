"""
FirstPatch AI — Shared Pydantic v2 Schemas

These schemas define the API contract between frontend and backend.
Every displayed fact must be traceable to an EvidenceRef.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class EvidenceType(str, Enum):
    REPOSITORY_METADATA = "repository_metadata"
    README_STATEMENT = "readme_statement"
    CONFIG_DECLARATION = "config_declaration"
    AST_FUNCTION = "ast_function"
    AST_IMPORT = "ast_import"
    EXISTING_TEST = "existing_test"
    GITHUB_ISSUE_FIELD = "github_issue_field"
    DIRECTORY_STRUCTURE = "directory_structure"
    EXECUTED_COMMAND = "executed_command"
    INFERRED = "inferred"  # Model interpretation, not source-derived


class EvidenceStatus(str, Enum):
    VERIFIED = "verified"       # Retrieved from source
    INFERRED = "inferred"       # Model-generated interpretation
    UNAVAILABLE = "unavailable" # Could not retrieve
    STALE = "stale"             # Cached but may be outdated


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    PARTIAL = "partial"         # Some information missing


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    UNKNOWN = "unknown"


class AIProviderStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    NOT_CONFIGURED = "not_configured"
    AI_ACTIVE = "ai_active"
    FALLBACK_ACTIVE = "fallback_active"
    AI_UNAVAILABLE = "ai_unavailable"


# ---------------------------------------------------------------------------
# Evidence Model — Core to all analysis
# ---------------------------------------------------------------------------


class EvidenceRef(BaseModel):
    """
    A traceable reference to a specific piece of information.
    Every displayed fact must link to an EvidenceRef.
    """
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    owner: str
    repo: str
    commit_sha: Optional[str] = None
    file_path: Optional[str] = None
    github_url: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    evidence_type: EvidenceType
    excerpt: Optional[str] = Field(
        None,
        description="Safe excerpt of the content. Max 500 chars to limit storage.",
        max_length=500,
    )
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    status: EvidenceStatus = EvidenceStatus.VERIFIED
    confidence_note: Optional[str] = Field(
        None,
        description="Human-readable note about confidence or uncertainty.",
    )


# ---------------------------------------------------------------------------
# Repository Analysis
# ---------------------------------------------------------------------------


class RepositoryIdentity(BaseModel):
    owner: str = Field(..., description="GitHub repository owner (user or org)")
    repo: str = Field(..., description="Repository name")

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def github_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"


class DetectedFramework(BaseModel):
    name: str
    confidence: str = Field(..., description="'certain' | 'likely' | 'possible'")
    evidence: list[EvidenceRef] = Field(default_factory=list)


class TestLocation(BaseModel):
    path: str
    framework: Optional[str] = None
    evidence: Optional[EvidenceRef] = None


class RepositoryOverview(BaseModel):
    model_config = ConfigDict(frozen=False)

    identity: RepositoryIdentity
    full_name: str
    description: Optional[str] = None
    primary_language: Optional[str] = None
    topics: list[str] = Field(default_factory=list)
    default_branch: str = "main"
    commit_sha: Optional[str] = Field(
        None, description="SHA of the analyzed commit snapshot"
    )
    stars: int = 0
    forks: int = 0
    open_issues_count: int = 0
    archived: bool = False
    license_name: Optional[str] = None
    github_url: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Analysis outputs
    readme_summary: Optional[str] = None
    detected_frameworks: list[DetectedFramework] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    test_locations: list[TestLocation] = Field(default_factory=list)
    directory_snapshot: list[str] = Field(
        default_factory=list,
        description="Top-level directory listing (not a full tree clone)",
    )
    detected_languages: dict[str, float] = Field(
        default_factory=dict,
        description="Language -> percentage (from GitHub API)",
    )

    # Meta
    analysis_status: AnalysisStatus = AnalysisStatus.PENDING
    analysis_warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    analyzed_at: Optional[datetime] = None
    cache_expires_at: Optional[datetime] = None


class AnalyzeRepositoryRequest(BaseModel):
    url: str = Field(..., description="Public GitHub repository URL")

    @field_validator("url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL must not be empty")
        if "github.com" not in v:
            raise ValueError("Only GitHub repositories are supported at this time")
        return v


class AnalyzeRepositoryResponse(BaseModel):
    repository: RepositoryOverview
    session_id: UUID = Field(default_factory=uuid4)
    analysis_duration_ms: Optional[int] = None


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------


class IssueLabel(BaseModel):
    name: str
    color: Optional[str] = None
    description: Optional[str] = None


class GitHubIssue(BaseModel):
    number: int
    title: str
    state: str
    body: Optional[str] = None
    labels: list[IssueLabel] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    author: Optional[str] = None
    comment_count: int = 0
    github_url: str
    is_pull_request: bool = False

    @property
    def is_good_first_issue(self) -> bool:
        return any(
            "good first issue" in label.name.lower() or "beginner" in label.name.lower()
            for label in self.labels
        )


class IssueMatchCriterion(BaseModel):
    name: str
    passed: bool
    score: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    evidence: Optional[EvidenceRef] = None
    missing_data: bool = False


class MatchedIssue(BaseModel):
    issue: GitHubIssue
    total_score: float = Field(..., ge=0.0, le=1.0)
    difficulty: DifficultyLevel = DifficultyLevel.UNKNOWN
    difficulty_explanation: str = ""
    criteria: list[IssueMatchCriterion] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    relevant_files: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    ai_enrichment: Optional[str] = Field(
        None,
        description="AI-generated explanation (clearly labelled as model-generated)",
    )
    ai_enrichment_available: bool = False


class IssueMatchRequest(BaseModel):
    owner: str
    repo: str
    skills: list[str] = Field(default_factory=list)
    preferred_languages: list[str] = Field(default_factory=list)
    experience_level: DifficultyLevel = DifficultyLevel.BEGINNER
    available_hours: Optional[float] = None
    learning_preferences: list[str] = Field(default_factory=list)


class IssueMatchResponse(BaseModel):
    owner: str
    repo: str
    matched_issues: list[MatchedIssue]
    total_issues_considered: int
    scoring_explanation: str
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Contribution Plan
# ---------------------------------------------------------------------------


class ImplementationStep(BaseModel):
    order: int
    description: str
    rationale: str
    relevant_files: list[str] = Field(default_factory=list)
    evidence: Optional[EvidenceRef] = None
    is_verified: bool = False


class ContributionPlan(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    owner: str
    repo: str
    issue_number: int
    issue_title: str
    issue_url: str

    summary: str
    relevant_files: list[str] = Field(default_factory=list)
    implementation_steps: list[ImplementationStep] = Field(default_factory=list)
    suggested_tests: list[str] = Field(default_factory=list)
    prerequisite_concepts: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    uncertainties: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    ai_generated: bool = False
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PlanRequest(BaseModel):
    owner: str
    repo: str
    issue_number: int
    contributor_skills: list[str] = Field(default_factory=list)
    experience_level: DifficultyLevel = DifficultyLevel.BEGINNER


# ---------------------------------------------------------------------------
# Setup Diagnostics
# ---------------------------------------------------------------------------


class DiagnosticRequest(BaseModel):
    owner: str
    repo: str
    error_description: str = Field(..., max_length=2000)
    command_output: Optional[str] = Field(None, max_length=5000)
    config_snippets: list[str] = Field(
        default_factory=list,
        description="Relevant config file contents (not full files)",
    )

    @field_validator("error_description", "command_output", mode="before")
    @classmethod
    def sanitize_text(cls, v: Any) -> Any:
        """Treat as data, not instructions."""
        return v  # Passed to AI as data with explicit framing


class DiagnosticFinding(BaseModel):
    likely_cause: str
    supporting_evidence: list[str] = Field(default_factory=list)
    safe_diagnostic_steps: list[str] = Field(default_factory=list)
    suggested_fix: Optional[str] = None
    verification_steps: list[str] = Field(default_factory=list)
    confidence: str = Field(..., description="'high' | 'medium' | 'low' | 'unknown'")
    is_verified: bool = False


class DiagnosticResponse(BaseModel):
    owner: str
    repo: str
    findings: list[DiagnosticFinding]
    disclaimer: str = (
        "These suggestions are based on repository analysis and common patterns. "
        "They have not been executed or verified. Always review suggested commands "
        "before running them."
    )
    ai_generated: bool = False


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_RUN = "not_run"
    UNAVAILABLE = "unavailable"


class VerificationCheck(BaseModel):
    name: str
    description: str
    status: CheckStatus = CheckStatus.NOT_RUN
    result_detail: Optional[str] = None
    ran_at: Optional[datetime] = None
    evidence: Optional[EvidenceRef] = None


class VerificationStatus(BaseModel):
    session_id: UUID
    owner: str
    repo: str
    checks: list[VerificationCheck] = Field(default_factory=list)
    overall_ready: bool = False
    blockers: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.PASSED)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.FAILED)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    ai_provider: str
    ai_provider_status: AIProviderStatus
    github_authenticated: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
