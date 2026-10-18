"""
FirstPatch AI — Phase 2 Repository Intelligence Schemas

Pydantic v2 schemas defining typed contracts for:
- Repository snapshots and file inventory
- Code structure analysis (AST symbols, imports, routes)
- Evidence extraction and deterministic validation
- Real GitHub issue-to-code mapping
- Contribution plan validation and test discovery
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.schemas.models import (
    EvidenceRef,
    EvidenceStatus,
    EvidenceType,
)


class FileType(str, Enum):
    SOURCE = "source"
    TEST = "test"
    CONFIG = "config"
    MANIFEST = "manifest"
    DOC = "doc"
    ASSET = "asset"
    OTHER = "other"


class SymbolType(str, Enum):
    FUNCTION = "function"
    ASYNC_FUNCTION = "async_function"
    CLASS = "class"
    METHOD = "method"
    IMPORT = "import"
    ROUTE = "route"
    TEST_CASE = "test_case"
    CONFIG_ITEM = "config_item"


class PlanStageEnum(str, Enum):
    UNDERSTAND = "understand"
    EXPLORE = "explore"
    PLAN = "plan"
    ATTEMPT = "attempt"
    VERIFY = "verify"
    PREPARE_PR = "prepare_pr"


class RepoFileEntry(BaseModel):
    """Metadata for a single file in the pinned repository snapshot."""
    path: str
    size: int = 0
    sha256_hash: Optional[str] = None
    file_type: FileType = FileType.OTHER
    is_truncated: bool = False


class RepositorySnapshot(BaseModel):
    """
    Immutable representation of a repository pinned to a specific commit SHA.
    All Phase 2 analyses refer to this snapshot.
    """
    owner: str
    repo: str
    canonical_url: str
    default_branch: str
    commit_sha: str = Field(..., description="Pinned commit SHA for deterministic analysis")
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    files: list[RepoFileEntry] = Field(default_factory=list)
    language_percentages: dict[str, float] = Field(default_factory=dict)
    dependency_manifests: list[str] = Field(default_factory=list)
    test_configs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    is_partial: bool = False

    @property
    def file_paths(self) -> set[str]:
        return {f.path for f in self.files}

    def has_file(self, path: str) -> bool:
        return path in self.file_paths


class CodeSymbol(BaseModel):
    """An extracted symbol from source-code structural analysis."""
    snapshot_sha: str
    file_path: str
    name: str
    symbol_type: SymbolType
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    excerpt: str = Field(..., max_length=1000)
    docstring: Optional[str] = None
    parameters: list[str] = Field(default_factory=list)
    decorators: list[str] = Field(default_factory=list)


class FileStructure(BaseModel):
    """Structural analysis of a single repository file."""
    file_path: str
    language: str
    symbols: list[CodeSymbol] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    routes: list[CodeSymbol] = Field(default_factory=list)
    test_cases: list[CodeSymbol] = Field(default_factory=list)
    parse_errors: list[str] = Field(default_factory=list)


class CodeStructureReport(BaseModel):
    """Collection of structural analysis results for the repository snapshot."""
    snapshot_sha: str
    files: dict[str, FileStructure] = Field(default_factory=dict)
    total_symbols: int = 0
    parse_warnings: list[str] = Field(default_factory=list)

    def find_symbols(self, query: str) -> list[CodeSymbol]:
        """Search extracted symbols across all analyzed files."""
        query_lower = query.lower()
        results: list[CodeSymbol] = []
        for file_struct in self.files.values():
            for symbol in file_struct.symbols:
                if query_lower in symbol.name.lower():
                    results.append(symbol)
        return results


class ClaimRecord(BaseModel):
    """
    A factual claim about repository code or behavior that requires validation.
    """
    claim_id: UUID = Field(default_factory=uuid4)
    claim_text: str
    evidence_type: EvidenceType
    commit_sha: Optional[str] = None
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    excerpt: Optional[str] = None
    status: EvidenceStatus = EvidenceStatus.UNAVAILABLE
    confidence_note: Optional[str] = None


class EvidenceValidationResult(BaseModel):
    """Deterministic result of checking a ClaimRecord against repository reality."""
    claim_id: UUID
    is_valid: bool
    status: EvidenceStatus
    reason: str
    matched_excerpt: Optional[str] = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceBundle(BaseModel):
    """Bundle of validated claims and their repository provenance."""
    snapshot_sha: str
    claims: list[ClaimRecord] = Field(default_factory=list)
    validation_results: list[EvidenceValidationResult] = Field(default_factory=list)
    verified_count: int = 0
    inferred_count: int = 0
    unknown_count: int = 0


class SourceMappingResult(BaseModel):
    """Result of mapping a GitHub issue to relevant repository source files."""
    issue_number: int
    relevant_files: list[str] = Field(default_factory=list)
    matched_symbols: list[CodeSymbol] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confidence: str = Field("unknown", description="'high' | 'medium' | 'low' | 'none'")
    heuristic_reasons: list[str] = Field(default_factory=list)
    missing_evidence_notes: list[str] = Field(default_factory=list)
    has_reliable_mapping: bool = False


class TestDiscoveryReport(BaseModel):
    """Static discovery of repository test setups without code execution."""
    __test__ = False  # Prevent pytest from treating this Pydantic schema as a test case
    test_frameworks: list[str] = Field(default_factory=list)
    test_directories: list[str] = Field(default_factory=list)
    test_config_files: list[str] = Field(default_factory=list)
    discovered_test_files: list[str] = Field(default_factory=list)
    discovered_test_cases: list[str] = Field(default_factory=list)
    execution_command_suggestions: list[str] = Field(default_factory=list)
    is_statically_discovered: bool = True
    execution_performed: bool = False
    disclaimer: str = (
        "All test information was discovered via static source and configuration analysis. "
        "No test commands or repository scripts have been executed."
    )


class StructuredPlanStage(BaseModel):
    """A single stage in a structured contribution plan."""
    stage: PlanStageEnum
    title: str
    description: str
    relevant_files: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StructuredContributionPlan(BaseModel):
    """Multi-stage contribution plan with deterministic evidence grounding."""
    session_id: UUID = Field(default_factory=uuid4)
    owner: str
    repo: str
    commit_sha: str
    issue_number: int
    issue_title: str
    issue_url: str
    summary: str
    stages: list[StructuredPlanStage] = Field(default_factory=list)
    relevant_files: list[str] = Field(default_factory=list)
    suggested_tests: list[str] = Field(default_factory=list)
    prerequisite_concepts: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    ai_generated: bool = False
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlanValidationReport(BaseModel):
    """Result of deterministically validating a contribution plan against reality."""
    is_valid: bool
    passed_checks: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    invalid_file_refs: list[str] = Field(default_factory=list)
    invalid_symbol_refs: list[str] = Field(default_factory=list)
