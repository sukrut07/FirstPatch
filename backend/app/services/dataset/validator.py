"""
FirstPatch AI — Dataset Validator (Phase 4)

Validates dataset integrity:
- JSONL line integrity (parseable JSON)
- Schema validation and required field presence per task type
- Sensitive data & secret filtering (GitHub PATs, API keys, private keys, bearer tokens)
- Duplicate detection (task_id and repository/issue uniqueness)
- Path traversal protection in file paths
- Repository-level split leakage detection
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.dataset.task_schema import EvaluationTask, TaskType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sensitive data patterns for secret leak detection
# ---------------------------------------------------------------------------
SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("GitHub Personal Access Token (classic)", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("GitHub Fine-Grained PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{82}\b")),
    ("Google AI Studio / Gemini API Key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("RSA / EC Private Key", re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+)?PRIVATE\s+KEY-----")),
    ("Generic Bearer Token", re.compile(r"(?i)\bbearer\s+[a-zA-Z0-9_\-\.]{25,}\b")),
]


@dataclass
class ValidationIssue:
    line: int
    field: str
    message: str
    severity: str = "error"  # error | warning


@dataclass
class ValidationReport:
    source_name: str
    total_lines: int = 0
    valid_tasks: int = 0
    invalid_lines: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.invalid_lines == 0 and not any(
            i.severity == "error" for i in self.issues
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "total_lines": self.total_lines,
            "valid_tasks": self.valid_tasks,
            "invalid_lines": self.invalid_lines,
            "is_valid": self.is_valid,
            "issue_count": len(self.issues),
            "issues": [
                {
                    "line": i.line,
                    "field": i.field,
                    "message": i.message,
                    "severity": i.severity,
                }
                for i in self.issues[:50]  # cap for response size
            ],
        }


# Required fields per task type
_REQUIRED_FIELDS: dict[TaskType, list[str]] = {
    TaskType.FILE_RELEVANCE: ["issue_title", "expected_relevant_files"],
    TaskType.ISSUE_TRACING: ["issue_body", "expected_relevant_files"],
    TaskType.PLAN_QUALITY: ["issue_title", "issue_body"],
    TaskType.AI_ENRICHMENT: ["issue_title"],
    TaskType.SETUP_DIAGNOSIS: ["issue_body", "expected_diagnosis"],
}


class DatasetValidator:
    """
    Validates JSONL dataset files for structural integrity, field completeness,
    secret safety, path safety, and split cleanliness.
    """

    def validate_file(self, jsonl_path: Path, source_name: str) -> ValidationReport:
        """Validate a single JSONL file with secret and duplicate detection."""
        report = ValidationReport(source_name=source_name)

        try:
            lines = jsonl_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            report.issues.append(ValidationIssue(
                line=0, field="file", message=f"Cannot read file: {exc}", severity="error"
            ))
            return report

        seen_task_ids: set[str] = set()
        seen_repo_issues: set[tuple[str, str, int]] = set()

        for lineno, raw_line in enumerate(lines, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            report.total_lines += 1

            # 1. Secret & sensitive data check on raw line
            for sec_name, pattern in SECRET_PATTERNS:
                if pattern.search(raw_line):
                    report.invalid_lines += 1
                    report.issues.append(ValidationIssue(
                        line=lineno,
                        field="security",
                        message=f"Potential secret/credential detected: {sec_name}",
                        severity="error",
                    ))

            # 2. JSON parse
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                report.invalid_lines += 1
                report.issues.append(ValidationIssue(
                    line=lineno, field="json",
                    message=f"Invalid JSON: {exc}", severity="error"
                ))
                continue

            # 3. Pydantic parse
            try:
                task = EvaluationTask(**record)
            except Exception as exc:
                report.invalid_lines += 1
                report.issues.append(ValidationIssue(
                    line=lineno, field="schema",
                    message=f"Schema validation failed: {exc}", severity="error"
                ))
                continue

            # 4. Duplicate checks
            if task.task_id in seen_task_ids:
                report.issues.append(ValidationIssue(
                    line=lineno, field="task_id",
                    message=f"Duplicate task_id: '{task.task_id}'", severity="warning"
                ))
            else:
                seen_task_ids.add(task.task_id)

            if task.owner and task.repo and task.issue_number > 0:
                key = (task.owner.lower(), task.repo.lower(), task.issue_number)
                if key in seen_repo_issues:
                    report.issues.append(ValidationIssue(
                        line=lineno, field="issue",
                        message=f"Duplicate issue task: {task.owner}/{task.repo}#{task.issue_number}",
                        severity="warning",
                    ))
                else:
                    seen_repo_issues.add(key)

            # 5. Path traversal checks in snapshot and target files
            all_paths = task.repository_snapshot + task.expected_relevant_files + task.expected_patch_files
            for p in all_paths:
                if ".." in p or p.startswith("/") or (len(p) > 1 and p[1] == ":"):
                    report.issues.append(ValidationIssue(
                        line=lineno, field="path_traversal",
                        message=f"Suspicious path or traversal detected in file list: '{p}'",
                        severity="error",
                    ))

            # 6. Required field checks per task type
            task_type = TaskType(task.task_type) if isinstance(task.task_type, str) else task.task_type
            required = _REQUIRED_FIELDS.get(task_type, [])
            for req_field in required:
                val = getattr(task, req_field, None)
                if val is None or val == [] or val == "":
                    report.issues.append(ValidationIssue(
                        line=lineno, field=req_field,
                        message=f"Required field '{req_field}' is empty for task type '{task_type}'",
                        severity="warning"
                    ))

            # 7. Sanity: issue_number >= 0
            if task.issue_number < 0:
                report.issues.append(ValidationIssue(
                    line=lineno, field="issue_number",
                    message=f"issue_number must be >= 0, got {task.issue_number}",
                    severity="warning"
                ))

            report.valid_tasks += 1

        return report

    def validate_directory(self, dataset_dir: Path, source_name: str) -> ValidationReport:
        """Validate all JSONL files in a dataset directory."""
        merged = ValidationReport(source_name=source_name)

        jsonl_files = sorted(dataset_dir.glob("**/*.jsonl"))
        if not jsonl_files:
            merged.issues.append(ValidationIssue(
                line=0, field="directory",
                message=f"No JSONL files found in {dataset_dir}",
                severity="error"
            ))
            return merged

        for jf in jsonl_files:
            report = self.validate_file(jf, source_name)
            merged.total_lines += report.total_lines
            merged.valid_tasks += report.valid_tasks
            merged.invalid_lines += report.invalid_lines
            merged.issues.extend(report.issues)

        return merged

    @staticmethod
    def validate_split_leakage(
        train_tasks: list[EvaluationTask],
        test_tasks: list[EvaluationTask],
    ) -> list[str]:
        """
        Check that no repository in test_tasks exists in train_tasks.
        Prevents data leakage across evaluation splits.
        Returns a list of violating repositories.
        """
        train_repos = {
            f"{t.owner.lower()}/{t.repo.lower()}"
            for t in train_tasks
            if t.owner and t.repo
        }
        leaked = []
        for t in test_tasks:
            if t.owner and t.repo:
                repo_id = f"{t.owner.lower()}/{t.repo.lower()}"
                if repo_id in train_repos and repo_id not in leaked:
                    leaked.append(repo_id)
        return leaked
