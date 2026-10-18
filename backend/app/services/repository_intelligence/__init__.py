"""
FirstPatch AI — Phase 2 Repository Intelligence Module

This package provides:
- Pinned repository snapshots and file inventories
- Source-code structure extraction (Python AST, JS/TS, fallbacks)
- Deterministic evidence extraction and reality checking
- Real GitHub issue-to-code mapping
- Contribution plan generation and plan validation
- Static test discovery
- Security boundaries (SSRF, path traversal, credential redaction)
- Stable Phase 1 integration contract
"""
from app.services.repository_intelligence.code_structure import (
    CodeStructureAnalyzer,
    should_analyze_file,
)
from app.services.repository_intelligence.contribution_plan import (
    ContributionPlanService,
    PlanValidator,
)
from app.services.repository_intelligence.evidence_extractor import EvidenceExtractor
from app.services.repository_intelligence.evidence_validator import EvidenceValidator
from app.services.repository_intelligence.exceptions import (
    EvidenceValidationError,
    RepositoryIntelligenceError,
    SecurityBoundaryError,
    SnapshotIncompleteError,
    SourceCodeAnalysisError,
    StaleSnapshotError,
)
from app.services.repository_intelligence.issue_mapper import IssueToCodeMapper
from app.services.repository_intelligence.schemas import (
    ClaimRecord,
    CodeStructureReport,
    CodeSymbol,
    EvidenceBundle,
    EvidenceValidationResult,
    FileStructure,
    FileType,
    PlanStageEnum,
    PlanValidationReport,
    RepoFileEntry,
    RepositorySnapshot,
    SourceMappingResult,
    StructuredContributionPlan,
    StructuredPlanStage,
    SymbolType,
    TestDiscoveryReport,
)
from app.services.repository_intelligence.security import (
    redact_sensitive_text,
    validate_repo_path,
)
from app.services.repository_intelligence.service import (
    RepositoryIntelligenceService,
    get_repository_intelligence_service,
)
from app.services.repository_intelligence.snapshot import (
    RepositorySnapshotService,
    classify_file,
)
from app.services.repository_intelligence.test_discovery import TestDiscoveryService

__all__ = [
    # Services
    "RepositoryIntelligenceService",
    "get_repository_intelligence_service",
    "RepositorySnapshotService",
    "CodeStructureAnalyzer",
    "EvidenceValidator",
    "EvidenceExtractor",
    "IssueToCodeMapper",
    "ContributionPlanService",
    "PlanValidator",
    "TestDiscoveryService",
    # Functions
    "classify_file",
    "should_analyze_file",
    "validate_repo_path",
    "redact_sensitive_text",
    # Schemas
    "FileType",
    "SymbolType",
    "PlanStageEnum",
    "RepoFileEntry",
    "RepositorySnapshot",
    "CodeSymbol",
    "FileStructure",
    "CodeStructureReport",
    "ClaimRecord",
    "EvidenceValidationResult",
    "EvidenceBundle",
    "SourceMappingResult",
    "TestDiscoveryReport",
    "StructuredPlanStage",
    "StructuredContributionPlan",
    "PlanValidationReport",
    # Exceptions
    "RepositoryIntelligenceError",
    "SnapshotIncompleteError",
    "StaleSnapshotError",
    "EvidenceValidationError",
    "SourceCodeAnalysisError",
    "SecurityBoundaryError",
]
