"""
FirstPatch AI — Test Output Parsers (Phase 3)

Parses stdout and stderr from allowlisted test runners (pytest, jest/npm test)
into structured test counts, failure summaries, and collection diagnostics.

Guarantees:
- Never invents numbers: if counts cannot be reliably determined, leaves them 0/None.
- Bounds summaries to avoid memory amplification.
- Distinguishes collection errors from test assertion failures.
"""
from __future__ import annotations

import re
from typing import Optional

from app.schemas.verification import VerificationTestCounts


class PytestOutputParser:
    """Parser for pytest console output."""

    # Pytest summary line matches "=... in X.XXs =="
    _SUMMARY_LINE_RE = re.compile(r"=+ (.*?) in \d+\.\d+s =+", re.IGNORECASE)

    # Pytest collected line: "collected 12 items"
    _COLLECTED_RE = re.compile(r"collected\s+(\d+)\s+item", re.IGNORECASE)

    # Collection error marker
    _COLLECTION_ERROR_RE = re.compile(
        r"(ERROR collecting|ModuleNotFoundError|ImportError|SyntaxError|=== ERRORS ===)",
        re.IGNORECASE,
    )

    @classmethod
    def parse(cls, stdout: str, stderr: str) -> tuple[VerificationTestCounts, Optional[str]]:
        """
        Parses pytest output into VerificationTestCounts and an optional error summary.
        """
        combined = f"{stdout}\n{stderr}"
        counts = VerificationTestCounts()

        # Parse collected count
        collected_match = cls._COLLECTED_RE.search(combined)
        if collected_match:
            try:
                counts.collected = int(collected_match.group(1))
            except (ValueError, IndexError):
                counts.collected = 0

        # Parse summary line
        summary_line_match = cls._SUMMARY_LINE_RE.search(combined)
        if summary_line_match:
            summary_content = summary_line_match.group(1)

            # Match items in any order: e.g. "1 failed, 3 passed, 1 skipped"
            passed_m = re.search(r"(\d+)\s+passed", summary_content, re.IGNORECASE)
            if passed_m:
                counts.passed = int(passed_m.group(1))

            failed_m = re.search(r"(\d+)\s+failed", summary_content, re.IGNORECASE)
            if failed_m:
                counts.failed = int(failed_m.group(1))

            skipped_m = re.search(r"(\d+)\s+skipped", summary_content, re.IGNORECASE)
            if skipped_m:
                counts.skipped = int(skipped_m.group(1))

            errors_m = re.search(r"(\d+)\s+error(?:s)?", summary_content, re.IGNORECASE)
            if errors_m:
                counts.errors = int(errors_m.group(1))

            if counts.collected == 0:
                counts.collected = counts.passed + counts.failed + counts.skipped + counts.errors

        # Check for collection errors or explicit failures
        error_summary = cls._extract_error_summary(combined, counts)

        return counts, error_summary

    @classmethod
    def _extract_error_summary(cls, text: str, counts: VerificationTestCounts) -> Optional[str]:
        """Extract a bounded error summary (up to 1000 characters)."""
        if counts.failed == 0 and counts.errors == 0:
            # Check if there is an unhandled collection crash
            if cls._COLLECTION_ERROR_RE.search(text):
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                error_lines = [l for l in lines if any(k in l for k in ["Error", "ERROR", "Traceback", "FAILED"])]
                if error_lines:
                    return "\n".join(error_lines[:5])[:1000]
            return None

        # Extract FAILURES / ERRORS section if present
        lines = text.splitlines()
        failure_lines: list[str] = []
        capturing = False

        for line in lines:
            if "=== FAILURES ===" in line or "=== ERRORS ===" in line:
                capturing = True
            elif capturing and (line.startswith("=== short test summary") or line.startswith("=== 1 passed") or line.startswith("=== 1 failed")):
                capturing = False

            if capturing and line.strip():
                failure_lines.append(line.rstrip())
                if len(failure_lines) >= 20:
                    break

        if failure_lines:
            summary = "\n".join(failure_lines)
            return summary[:1000]

        # Fallback to lines containing FAILED
        fallback = [l.strip() for l in lines if l.strip().startswith("FAILED ") or "AssertionError" in l]
        if fallback:
            return "\n".join(fallback[:5])[:1000]

        return "Test execution reported failures or errors."


class JestNpmOutputParser:
    """Parser for Jest and npm test console output."""

    # Jest summary pattern:
    # "Tests:       2 failed, 10 passed, 12 total"
    _JEST_TESTS_RE = re.compile(
        r"Tests:\s*(?:(?P<failed>\d+)\s+failed,\s*)?"
        r"(?:(?P<skipped>\d+)\s+skipped,\s*)?"
        r"(?:(?P<passed>\d+)\s+passed,\s*)?"
        r"(?P<total>\d+)\s+total",
        re.IGNORECASE,
    )

    @classmethod
    def parse(cls, stdout: str, stderr: str) -> tuple[VerificationTestCounts, Optional[str]]:
        """Parses Jest or npm test output into VerificationTestCounts."""
        combined = f"{stdout}\n{stderr}"
        counts = VerificationTestCounts()

        match = cls._JEST_TESTS_RE.search(combined)
        if match:
            groups = match.groupdict()
            counts.failed = int(groups["failed"]) if groups.get("failed") else 0
            counts.skipped = int(groups["skipped"]) if groups.get("skipped") else 0
            counts.passed = int(groups["passed"]) if groups.get("passed") else 0
            counts.collected = int(groups["total"]) if groups.get("total") else 0

        error_summary = None
        if counts.failed > 0 or "FAIL" in combined:
            lines = combined.splitlines()
            fail_lines = [l.strip() for l in lines if l.strip().startswith("●") or "FAIL " in l or "Expected:" in l or "Received:" in l]
            if fail_lines:
                error_summary = "\n".join(fail_lines[:10])[:1000]
            else:
                error_summary = "Jest / npm test reported failures."

        return counts, error_summary
