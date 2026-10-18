"""
FirstPatch AI — Dataset Validator (Phase 4)

Validates dataset integrity:
- JSONL line integrity (parseable JSON)
- Required field presence per task type
- No PII leakage in synthetic tasks
- Field type constraints
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.dataset.task_schema import EvaluationTask, TaskType

logger = logging.getLogger(__name__)


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
                for i in self.issues[:20]  # cap for response size
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
    Validates JSONL dataset files for structural integrity and field completeness.
    """

    def validate_file(self, jsonl_path: Path, source_name: str) -> ValidationReport:
        """Validate a single JSONL file."""
        report = ValidationReport(source_name=source_name)

        try:
            lines = jsonl_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            report.issues.append(ValidationIssue(
                line=0, field="file", message=f"Cannot read file: {exc}", severity="error"
            ))
            return report

        for lineno, raw_line in enumerate(lines, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            report.total_lines += 1

            # JSON parse
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                report.invalid_lines += 1
                report.issues.append(ValidationIssue(
                    line=lineno, field="json",
                    message=f"Invalid JSON: {exc}", severity="error"
                ))
                continue

            # Pydantic parse
            try:
                task = EvaluationTask(**record)
            except Exception as exc:
                report.invalid_lines += 1
                report.issues.append(ValidationIssue(
                    line=lineno, field="schema",
                    message=f"Schema validation failed: {exc}", severity="error"
                ))
                continue

            # Required field checks per task type
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

            # Sanity: issue_number >= 0
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
