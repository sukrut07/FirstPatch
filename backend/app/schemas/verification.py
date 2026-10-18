"""
FirstPatch AI — Verification Schemas (Phase 3)

Defines data contracts for isolated test execution:
- ExecutionStatus state machine
- Allowed RuntimeProfiles
- VerificationRunRequest
- VerificationTestCounts
- VerificationRunRecord
- VerificationInfrastructureHealth
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExecutionStatus(str, Enum):
    """
    Explicit lifecycle states for verification runs.
    Valid transitions:
      QUEUED -> PREPARING -> RUNNING -> PASSED | FAILED | TIMED_OUT | CANCELLED
      QUEUED | PREPARING -> BLOCKED | UNSUPPORTED | UNAVAILABLE
    """
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    CANCELLED = "cancelled"


# Allowed state transitions
VALID_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.QUEUED: {
        ExecutionStatus.PREPARING,
        ExecutionStatus.BLOCKED,
        ExecutionStatus.UNSUPPORTED,
        ExecutionStatus.UNAVAILABLE,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.PREPARING: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.BLOCKED,
        ExecutionStatus.UNSUPPORTED,
        ExecutionStatus.UNAVAILABLE,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.RUNNING: {
        ExecutionStatus.PASSED,
        ExecutionStatus.FAILED,
        ExecutionStatus.TIMED_OUT,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.PASSED: set(),
    ExecutionStatus.FAILED: set(),
    ExecutionStatus.TIMED_OUT: set(),
    ExecutionStatus.BLOCKED: set(),
    ExecutionStatus.UNSUPPORTED: set(),
    ExecutionStatus.UNAVAILABLE: set(),
    ExecutionStatus.CANCELLED: set(),
}


class RuntimeProfile(str, Enum):
    """Allowlisted execution runtime profiles."""
    PYTHON_PYTEST = "python_pytest"
    NODE_JEST = "node_jest"
    NODE_NPM_TEST = "node_npm_test"


class VerificationRunRequest(BaseModel):
    """Request to execute tests in an isolated sandbox."""
    model_config = ConfigDict(frozen=True)

    owner: str = Field(..., description="GitHub repository owner")
    repo: str = Field(..., description="GitHub repository name")
    commit_sha: str = Field(..., description="Exact commit SHA of the snapshot to test")
    runtime: RuntimeProfile = Field(
        default=RuntimeProfile.PYTHON_PYTEST,
        description="Preconfigured runtime profile",
    )
    test_target: str = Field(
        default="tests",
        description="Allowlisted test target or path (e.g. 'tests' or 'tests/test_main.py')",
        max_length=150,
    )
    timeout_seconds: int = Field(
        default=45,
        ge=5,
        le=120,
        description="Wall-clock execution limit in seconds (5 to 120)",
    )
    session_id: Optional[UUID] = Field(
        default=None,
        description="Optional contribution session ID to associate results with",
    )

    @field_validator("owner", "repo")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError(f"Invalid characters in repository identifier: {v}")
        return v

    @field_validator("commit_sha")
    @classmethod
    def validate_commit_sha(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-fA-F0-9]{7,40}$", v):
            raise ValueError(f"Invalid commit SHA format: {v}")
        return v

    @field_validator("test_target")
    @classmethod
    def sanitize_test_target(cls, v: str) -> str:
        v = v.strip()
        # Prevent shell metacharacters, directory traversal, pipe, semicolon
        if any(c in v for c in [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r", "\0"]):
            raise ValueError("Test target contains invalid characters or shell metacharacters")
        if ".." in v or v.startswith("/") or v.startswith("\\"):
            raise ValueError("Path traversal ('..' or absolute paths) in test target is prohibited")
        return v


class VerificationTestCounts(BaseModel):
    """Granular test execution statistics."""
    collected: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0


class VerificationRunRecord(BaseModel):
    """Immutable or auditable record of an isolated test execution run."""
    run_id: UUID = Field(default_factory=uuid4)
    session_id: Optional[UUID] = None
    owner: str
    repo: str
    commit_sha: str
    runtime: RuntimeProfile
    test_target: str
    status: ExecutionStatus = ExecutionStatus.QUEUED
    exit_code: Optional[int] = None
    counts: Optional[VerificationTestCounts] = None
    stdout: str = Field(default="", description="Bounded standard output (max 50KB)")
    stderr: str = Field(default="", description="Bounded standard error (max 50KB)")
    error_summary: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    cleanup_performed: bool = False
    cleanup_error: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)

    @property
    def is_finished(self) -> bool:
        return self.status in {
            ExecutionStatus.PASSED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMED_OUT,
            ExecutionStatus.BLOCKED,
            ExecutionStatus.UNSUPPORTED,
            ExecutionStatus.UNAVAILABLE,
            ExecutionStatus.CANCELLED,
        }


class VerificationInfrastructureHealth(BaseModel):
    """Reports status of the sandboxing container infrastructure."""
    runtime_available: bool
    runtime_name: str
    isolation_level: str
    supported_profiles: list[RuntimeProfile]
    message: str
    host_execution_permitted: bool = False
