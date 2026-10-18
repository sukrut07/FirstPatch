"""
FirstPatch AI — Phase 2 Repository Intelligence Exceptions
"""
from typing import Optional


class RepositoryIntelligenceError(Exception):
    """Base exception for all Phase 2 repository intelligence errors."""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SnapshotIncompleteError(RepositoryIntelligenceError):
    """Raised when repository snapshot cannot be fully retrieved."""
    pass


class StaleSnapshotError(RepositoryIntelligenceError):
    """Raised when an operation refers to a commit SHA that doesn't match the current snapshot."""
    pass


class EvidenceValidationError(RepositoryIntelligenceError):
    """Raised when deterministic evidence validation fails."""
    pass


class SourceCodeAnalysisError(RepositoryIntelligenceError):
    """Raised when source-code structural parsing fails unexpectedly."""
    pass


class SecurityBoundaryError(RepositoryIntelligenceError):
    """Raised when a security rule (path traversal, SSRF, command execution) is violated."""
    pass
