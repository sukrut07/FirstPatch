"""
FirstPatch AI — Evaluation Task Schema (Phase 4)

Defines the internal task representation for benchmarking:
- file relevance prediction
- issue-to-file traceability
- contribution plan quality
- AI enrichment quality
- setup diagnosis accuracy

Includes full provenance metadata (commit_sha, source_url, dataset_version, license, split).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Category of evaluation task."""
    FILE_RELEVANCE = "file_relevance"
    ISSUE_TRACING = "issue_tracing"
    PLAN_QUALITY = "plan_quality"
    AI_ENRICHMENT = "ai_enrichment"
    SETUP_DIAGNOSIS = "setup_diagnosis"


class TaskDifficulty(str, Enum):
    """Relative difficulty of the evaluation task."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class EvaluationTask(BaseModel):
    """
    A single evaluation task for FirstPatch AI.

    Represents one ground-truth sample: input context, expected outputs,
    and metadata for tracking evaluation runs with full provenance.
    """
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType
    difficulty: TaskDifficulty = TaskDifficulty.MEDIUM
    dataset_source: str                         # manifest source name
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ---- Input context ----
    owner: str = ""
    repo: str = ""
    issue_number: int = 0
    issue_title: str = ""
    issue_body: str = ""
    repository_snapshot: list[str] = Field(default_factory=list)   # known file paths
    primary_language: Optional[str] = None

    # ---- Provenance & Governance ----
    commit_sha: str = ""                        # Target base commit SHA
    source_url: str = ""                        # Origin URL of issue / task
    dataset_version: str = "1.0.0"              # Version of dataset snapshot
    license: str = ""                           # License of source code / task
    split: str = "test"                         # train / val / test

    # ---- Ground truth ----
    expected_relevant_files: list[str] = Field(default_factory=list)
    expected_patch_files: list[str] = Field(default_factory=list)   # SWE-bench oracle
    expected_diagnosis: Optional[str] = None                        # diagnosis tasks
    reference_summary: Optional[str] = None                        # plan/AI tasks

    # ---- Metadata ----
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class TaskResult(BaseModel):
    """
    Result of running FirstPatch AI against one EvaluationTask.
    """
    task_id: str
    task_type: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evaluation_mode: str = "deterministic_baseline"  # deterministic_baseline | live_ai | mock_ai

    # ---- Predicted outputs ----
    predicted_files: list[str] = Field(default_factory=list)
    predicted_diagnosis: Optional[str] = None
    predicted_summary: Optional[str] = None
    ai_generated: bool = False
    is_fallback: bool = False
    is_mock: bool = False
    latency_ms: float = 0.0

    # ---- Verification & Evidence Quality ----
    evidence_validity_rate: Optional[float] = None
    unsupported_claim_rate: Optional[float] = None

    # ---- Computed metrics (filled in by evaluator) ----
    metrics: dict[str, Any] = Field(default_factory=dict)
    passed: Optional[bool] = None
    error: Optional[str] = None

    class Config:
        use_enum_values = True
