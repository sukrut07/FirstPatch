import re
import uuid
from typing import Dict, Any, List, Optional
from backend.app.database import get_db, get_iso_now

class PRReviewSimulatorService:
    def __init__(self):
        pass

    def analyze_diff(
        self,
        diff_text: str,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        findings = []
        lines = diff_text.split("\n")

        # 1. Check for committed secrets / credentials
        secret_patterns = [
            (r'(?i)(api[_-]?key|secret|token|password|auth)\s*[:=]\s*["\'][a-zA-Z0-9_\-\.]{12,}["\']', "Potential hardcoded credential or secret detected."),
            (r'BEGIN (RSA|OPENSSH|PRIVATE) KEY', "Private cryptographic key detected in diff.")
        ]
        for idx, line in enumerate(lines, start=1):
            if line.startswith("+"):
                for pat, msg in secret_patterns:
                    if re.search(pat, line):
                        findings.append({
                            "id": str(uuid.uuid4()),
                            "severity": "critical",
                            "confidence": "high",
                            "line_number": idx,
                            "title": "Secret / Credential Leak Risk",
                            "explanation": msg,
                            "suggested_fix": "Extract credential to environment variables and add the file to .gitignore."
                        })

        # 2. Check for leftover debugging statements
        debug_patterns = [
            (r'\bprint\(', "Python `print()` call detected. Use logging instead."),
            (r'\bconsole\.log\(', "JavaScript `console.log()` statement detected. Remove before merging."),
            (r'\bdebugger\b', "JavaScript `debugger;` statement detected."),
            (r'\bimport\s+pdb\b', "Python debugger `pdb` import detected.")
        ]
        for idx, line in enumerate(lines, start=1):
            if line.startswith("+"):
                for pat, msg in debug_patterns:
                    if re.search(pat, line):
                        findings.append({
                            "id": str(uuid.uuid4()),
                            "severity": "warning",
                            "confidence": "high",
                            "line_number": idx,
                            "title": "Debug Artifact Left in Code",
                            "explanation": msg,
                            "suggested_fix": "Remove or replace with a structured logging statement."
                        })

        # 3. Check for broad exceptions / silent swallow
        for idx, line in enumerate(lines, start=1):
            if line.startswith("+"):
                if re.search(r'except\s*:\s*pass', line) or re.search(r'catch\s*\([^)]*\)\s*\{\s*\}', line):
                    findings.append({
                        "id": str(uuid.uuid4()),
                        "severity": "warning",
                        "confidence": "high",
                        "line_number": idx,
                        "title": "Silent Error Suppression",
                        "explanation": "Catching all exceptions silently can mask unexpected bugs and make debugging harder.",
                        "suggested_fix": "Catch specific exceptions and log the error message."
                    })

        # 4. Check if test files are modified when source code is added
        has_src_change = any(line.startswith("+++ b/") and not ("test" in line.lower()) for line in lines)
        has_test_change = any("test" in line.lower() for line in lines if line.startswith("+++ b/"))

        if has_src_change and not has_test_change:
            findings.append({
                "id": str(uuid.uuid4()),
                "severity": "convention",
                "confidence": "medium",
                "line_number": 1,
                "title": "Missing Unit Test Coverage",
                "explanation": "Source code was modified, but no corresponding test files were added or updated in this diff.",
                "suggested_fix": "Add a test function in `tests/` verifying the new behavior or bug fix."
            })

        # Maintainer questions simulation
        maintainer_questions = [
            "Why was this specific approach chosen over existing repository patterns?",
            "Could this change cause regression or break backwards compatibility for existing consumers?",
            "Have you run the local test suite and verified that all existing tests pass?"
        ]

        # Persist findings if workspace_id is provided
        if workspace_id:
            now = get_iso_now()
            with get_db() as conn:
                cursor = conn.cursor()
                for f in findings:
                    cursor.execute("""
                    INSERT INTO review_findings (
                        id, workspace_id, severity, confidence, file_path, line_number,
                        title, explanation, suggested_fix, is_verified, dismissed, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?)
                    """, (
                        f["id"], workspace_id, f["severity"], f["confidence"], "diff",
                        f.get("line_number", 1), f["title"], f["explanation"],
                        f.get("suggested_fix", ""), now
                    ))

        return {
            "findings_count": len(findings),
            "findings": findings,
            "maintainer_questions": maintainer_questions,
            "overall_status": "READY_WITH_NOTES" if not any(f["severity"] == "critical" for f in findings) else "ACTION_REQUIRED"
        }

review_simulator = PRReviewSimulatorService()
