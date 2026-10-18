import re
import json
from typing import List, Dict, Any, Optional

class IssueIntelligenceService:
    def __init__(self):
        pass

    def classify_category(self, issue: Dict[str, Any]) -> str:
        """Classifies issue category deterministically from labels and title."""
        title = issue.get("title", "").lower()
        labels = [l.lower() for l in issue.get("labels", [])]

        if any(l in ["doc", "docs", "documentation", "typo", "readme"] for l in labels) or "typo" in title or "documentation" in title:
            return "Documentation"
        if any(l in ["bug", "defect", "fix", "regression", "crash", "error"] for l in labels) or any(w in title for w in ["crash", "fix", "error", "bug", "fails"]):
            return "Bug"
        if any(l in ["test", "tests", "testing", "coverage"] for l in labels) or "test" in title:
            return "Testing"
        if any(l in ["feature", "enhancement", "proposal", "request"] for l in labels) or "feature" in title:
            return "Feature"
        if any(l in ["refactor", "cleanup", "chore"] for l in labels) or "refactor" in title:
            return "Refactoring"
        return "Maintenance"

    def check_claim_safety(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Claim-Safety Check: Inspects assignees, linked PRs, and discussion comments
        to prevent beginners from wasting effort on already-claimed tasks.
        """
        body = issue.get("body") or ""
        assignee = issue.get("assignee")
        comments_count = issue.get("comments_count", 0)

        # 1. Check if assigned
        if assignee:
            return {
                "status": "POSSIBLY_CLAIMED",
                "is_safe_to_claim": False,
                "reason": f"Issue is currently assigned to @{assignee}. Contact maintainer before starting work."
            }

        # 2. Check for linked PR or claim statements in body
        claim_patterns = [
            (r'(?i)(working on a (pr|fix)|i am working on this|i\'ll take this|submitting a pr|pr in progress)', "Contributor expressed intent to submit a PR in discussion."),
            (r'(?i)(fixed in #\d+|pr #\d+|pull request #\d+)', "Mentions an existing pull request addressing this issue.")
        ]
        for pat, reason in claim_patterns:
            if re.search(pat, body):
                return {
                    "status": "LINKED_OPEN_PR",
                    "is_safe_to_claim": False,
                    "reason": reason
                }

        # 3. Check for description completeness
        if len(body.strip()) < 30:
            return {
                "status": "NEEDS_CLARIFICATION",
                "is_safe_to_claim": False,
                "reason": "Issue description is very brief. Ask maintainers for reproduction steps first."
            }

        return {
            "status": "ACTIONABLE_SIGNAL_FOUND",
            "is_safe_to_claim": True,
            "reason": "No active assignees or linked open PRs detected. High availability for first contribution."
        }

    def extract_stacktrace_coordinates(self, text: str) -> List[Dict[str, Any]]:
        """
        Parses Python and JavaScript/TypeScript stack traces directly from issue text
        to extract exact file paths, line coordinates, and function names.
        """
        matches = []

        # Python stack trace: File "path/to/file.py", line 42, in function_name
        py_pattern = r'File\s+["\']([^"\']+\.py)["\'],\s+line\s+(\d+)(?:,\s+in\s+(\w+))?'
        for m in re.finditer(py_pattern, text):
            file_path = m.group(1).lstrip("./")
            line_no = int(m.group(2))
            fn_name = m.group(3) or "function"
            matches.append({
                "file_path": file_path,
                "line_start": max(1, line_no - 5),
                "line_end": line_no + 10,
                "target_line": line_no,
                "symbol_name": fn_name,
                "match_type": "STACKTRACE",
                "confidence": "High"
            })

        # Node / JS stack trace: at Object.<anonymous> (path/to/file.js:42:15)
        node_pattern = r'at\s+(?:([a-zA-Z0-9_\.]+)\s+\()?([a-zA-Z0-9_\-/\\]+\.(?:js|ts|tsx)):(\d+):\d+\)?'
        for m in re.finditer(node_pattern, text):
            fn_name = m.group(1) or "anonymous"
            file_path = m.group(2).lstrip("./")
            line_no = int(m.group(3))
            matches.append({
                "file_path": file_path,
                "line_start": max(1, line_no - 5),
                "line_end": line_no + 10,
                "target_line": line_no,
                "symbol_name": fn_name,
                "match_type": "STACKTRACE",
                "confidence": "High"
            })

        return matches

    def evaluate_issue(
        self,
        issue: Dict[str, Any],
        user_skill_level: str = "Beginner",
        preferred_languages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        title = issue.get("title", "")
        body = issue.get("body") or ""
        labels = [l.lower() for l in issue.get("labels", [])]
        comments_count = issue.get("comments_count", 0)

        fit_score = 50.0
        reasons = []
        potential_blockers = []
        prerequisite_skills = []

        category = self.classify_category(issue)
        claim_safety = self.check_claim_safety(issue)
        stacktrace_coords = self.extract_stacktrace_coordinates(body)

        # 1. Label Analysis
        beginner_labels = {"good first issue", "good-first-issue", "beginner", "easy", "starter", "first-timers-only"}
        doc_labels = {"documentation", "docs", "typo"}
        help_labels = {"help wanted", "help-wanted", "up-for-grabs"}

        has_beginner_label = any(l in beginner_labels for l in labels)
        has_doc_label = any(l in doc_labels for l in labels)
        has_help_label = any(l in help_labels for l in labels)

        if has_beginner_label:
            fit_score += 25
            reasons.append("Marked with maintainer-verified beginner label ('good first issue').")
        if has_doc_label:
            fit_score += 15
            reasons.append("Focuses on documentation or syntax clarity, lowering setup barriers.")
        if has_help_label:
            fit_score += 10
            reasons.append("Maintainers have explicitly tagged this as open for community help.")

        # 2. Body clarity & stack traces
        body_len = len(body.strip())
        if body_len < 40:
            fit_score -= 20
            potential_blockers.append("Very short issue description; requirements may be ambiguous.")
        elif body_len > 300:
            fit_score += 10
            reasons.append("Detailed issue description provided with context.")

        if stacktrace_coords:
            fit_score += 20
            reasons.append(f"Contains {len(stacktrace_coords)} deterministic stack trace file/line reference(s).")
        elif re.search(r'(reproduce|steps to reproduce|traceback|error|expected behavior)', body, re.I):
            fit_score += 10
            reasons.append("Contains explicit reproduction steps or error traceback.")
        else:
            potential_blockers.append("No explicit reproduction steps found in the issue text.")

        # 3. Claim Safety Adjustment
        if not claim_safety["is_safe_to_claim"]:
            fit_score -= 15
            potential_blockers.append(claim_safety["reason"])
        else:
            fit_score += 10
            reasons.append(claim_safety["reason"])

        # 4. Prerequisites detection
        if re.search(r'(pytest|fixture|mock|unittest)', body + title, re.I):
            prerequisite_skills.append("Unit testing with pytest / fixtures")
        if re.search(r'(async|await|coroutine|event loop)', body + title, re.I):
            prerequisite_skills.append("Asynchronous programming (async/await)")
            if user_skill_level == "Beginner":
                fit_score -= 10
                potential_blockers.append("Involves asynchronous control flow, which has a steeper learning curve.")
        if re.search(r'(docker|container|compose)', body + title, re.I):
            prerequisite_skills.append("Docker containerization")

        # 5. Complexity estimation
        if has_doc_label or ("typo" in title.lower()) or (has_beginner_label and body_len < 600):
            complexity = "Beginner"
            effort = "1-2 hours"
        elif any(term in title.lower() for term in ["refactor", "performance", "memory leak", "race condition"]):
            complexity = "Advanced"
            effort = "5-10 hours"
            if user_skill_level == "Beginner":
                fit_score -= 25
        else:
            complexity = "Intermediate"
            effort = "2-4 hours"

        # 6. Skill alignment adjustment
        if user_skill_level == "Beginner" and complexity == "Beginner":
            fit_score += 15
        elif user_skill_level == "Advanced" and complexity == "Advanced":
            fit_score += 15

        # 7. Relevant file heuristic extraction + stack traces
        found_files = set(re.findall(r'([a-zA-Z0-9_\-/]+\.(?:py|js|ts|tsx|md|json|toml))', body + " " + title))
        for st in stacktrace_coords:
            found_files.add(st["file_path"])
        relevant_files = list(found_files)[:6]

        fit_score = max(10.0, min(99.0, fit_score))

        return {
            "fit_score": round(fit_score, 1),
            "category": category,
            "claim_safety": claim_safety,
            "stacktrace_locations": stacktrace_coords,
            "skill_match": f"{round(fit_score)}% match for {user_skill_level}",
            "estimated_complexity": complexity,
            "estimated_effort": effort,
            "reasons": reasons if reasons else ["General open issue in the repository."],
            "potential_blockers": potential_blockers if potential_blockers else ["Ensure local environment is installed."],
            "relevant_files": relevant_files,
            "prerequisite_skills": prerequisite_skills if prerequisite_skills else ["Core programming fundamentals", "Git branch workflow"],
            "confidence": "High" if (has_beginner_label or len(stacktrace_coords) > 0) else "Medium",
            "missing_info": "Maintainer response time is unknown until claimed."
        }

issue_service = IssueIntelligenceService()
