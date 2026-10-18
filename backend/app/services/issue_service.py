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
        preferred_languages: Optional[List[str]] = None,
        user_interests: Optional[List[str]] = None,
        repo_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        title = issue.get("title", "")
        body = issue.get("body") or ""
        labels = [l.lower() for l in issue.get("labels", [])]

        category = self.classify_category(issue)
        claim_safety = self.check_claim_safety(issue)
        stacktrace_coords = self.extract_stacktrace_coordinates(body)

        # 1. Technical Fit Score (0-100)
        beginner_labels = {"good first issue", "good-first-issue", "beginner", "easy", "starter", "first-timers-only"}
        doc_labels = {"documentation", "docs", "typo"}
        help_labels = {"help wanted", "help-wanted", "up-for-grabs"}

        has_beginner_label = any(l in beginner_labels for l in labels)
        has_doc_label = any(l in doc_labels for l in labels)
        has_help_label = any(l in help_labels for l in labels)

        tech_fit = 60.0
        if has_beginner_label:
            tech_fit += 25.0
        if has_doc_label:
            tech_fit += 15.0
        if any(term in title.lower() for term in ["refactor", "async", "performance", "race condition"]):
            if user_skill_level == "Beginner":
                tech_fit -= 25.0
        tech_fit = max(15.0, min(95.0, tech_fit))

        # 2. Interest Fit Score (0-100)
        interest_fit = 70.0
        if user_interests:
            ui_lower = [i.lower() for i in user_interests]
            combined_text = (title + " " + body + " " + " ".join(labels)).lower()
            matches = [i for i in ui_lower if i in combined_text]
            if matches:
                interest_fit = min(98.0, 70.0 + len(matches) * 12.0)
            else:
                interest_fit = 60.0

        # 3. Evidence Confidence Score (0-100)
        evidence_conf = 50.0
        if stacktrace_coords:
            evidence_conf += 35.0
        elif re.search(r'(reproduce|steps to reproduce|traceback|error|expected behavior)', body, re.I):
            evidence_conf += 20.0
        if len(body.strip()) > 250:
            evidence_conf += 15.0
        evidence_conf = max(20.0, min(98.0, evidence_conf))

        # 4. Contribution Viability Score (0-100)
        viability = 80.0
        if not claim_safety["is_safe_to_claim"]:
            viability = 35.0
        elif has_help_label or has_beginner_label:
            viability = 92.0

        # 5. Learning Value Score (0-100)
        learning_value = 75.0
        learning_outcomes = []
        if category == "Bug":
            learning_outcomes.append("Tracing runtime exceptions and writing unit test assertions")
            learning_value += 15.0
        elif category == "Documentation":
            learning_outcomes.append("Repository documentation conventions and beginner onboarding clarity")
        elif category == "Testing":
            learning_outcomes.append("Pytest test fixtures and regression coverage")
            learning_value += 10.0
        else:
            learning_outcomes.append("Core software architecture and modular refactoring")

        # Composite Weighted Fit Score: 30% Tech, 25% Interest, 20% Evidence, 15% Viability, 10% Learning
        composite_fit = (
            (tech_fit * 0.30) +
            (interest_fit * 0.25) +
            (evidence_conf * 0.20) +
            (viability * 0.15) +
            (learning_value * 0.10)
        )
        composite_fit = round(max(10.0, min(99.0, composite_fit)), 1)

        # 6. Complexity & Effort
        if has_doc_label or ("typo" in title.lower()) or (has_beginner_label and len(body) < 600):
            complexity = "Beginner"
            effort = "1-2 hours"
        elif any(term in title.lower() for term in ["refactor", "performance", "memory leak", "race condition"]):
            complexity = "Advanced"
            effort = "5-10 hours"
        else:
            complexity = "Intermediate"
            effort = "2-4 hours"

        # 7. Relevant files extraction
        found_files = set(re.findall(r'([a-zA-Z0-9_\-/]+\.(?:py|js|ts|tsx|md|json|toml))', body + " " + title))
        for st in stacktrace_coords:
            found_files.add(st["file_path"])
        relevant_files = list(found_files)[:6]

        # 8. Reasons & Prerequisites
        reasons = []
        potential_blockers = []
        if has_beginner_label:
            reasons.append("Marked with maintainer-verified beginner label ('good first issue').")
        if stacktrace_coords:
            reasons.append(f"Direct stack trace isolates {len(stacktrace_coords)} deterministic code coordinate(s).")
        if claim_safety["is_safe_to_claim"]:
            reasons.append(claim_safety["reason"])
        else:
            potential_blockers.append(claim_safety["reason"])

        prerequisite_skills = ["Core programming fundamentals", "Git branch workflow"]
        if "pytest" in (body + title).lower():
            prerequisite_skills.append("Unit testing with pytest / fixtures")

        repo_name = repo_metadata.get("name") if repo_metadata else "this project"

        # 9. Four Transparent Questions
        why_this_project = f"{repo_name} provides clean modular structure and verifiable test suites for newcomers."
        why_this_issue = f"Focused {category.lower()} task with isolated blast radius and clear boundaries."
        why_suitable_for_me = f"Aligns with your {user_skill_level} experience; estimated effort is {effort} without requiring architectural refactoring."
        what_to_verify_first = (
            f"Confirm that the behavior still reproduces locally using `pytest` before making code changes, and check if an open PR is already linked."
        )

        return {
            "fit_score": composite_fit,
            "category": category,
            "claim_safety": claim_safety,
            "technical_fit_score": round(tech_fit, 1),
            "interest_fit_score": round(interest_fit, 1),
            "evidence_confidence_score": round(evidence_conf, 1),
            "viability_score": round(viability, 1),
            "learning_value_score": round(learning_value, 1),
            "why_this_project": why_this_project,
            "why_this_issue": why_this_issue,
            "why_suitable_for_me": why_suitable_for_me,
            "what_to_verify_first": what_to_verify_first,
            "learning_outcomes": learning_outcomes,
            "stacktrace_locations": stacktrace_coords,
            "skill_match": f"{round(composite_fit)}% match for {user_skill_level}",
            "estimated_complexity": complexity,
            "estimated_effort": effort,
            "reasons": reasons if reasons else ["Well-scoped community issue."],
            "potential_blockers": potential_blockers if potential_blockers else ["Ensure clean local virtual environment is active."],
            "relevant_files": relevant_files,
            "prerequisite_skills": prerequisite_skills,
            "confidence": "High" if (has_beginner_label or len(stacktrace_coords) > 0) else "Medium",
            "missing_info": "Maintainer response time is unknown until claimed."
        }

    def generate_grounded_investigation(
        self,
        issue: Dict[str, Any],
        repo_id: str,
        commit_sha: str,
        indexed_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Synthesizes a grounded, reality-checked investigation for a single issue.
        Identifies verified source candidates, likely execution paths, known facts,
        inferred hypotheses, explicit unknowns, and minimal next action.
        """
        title = issue.get("title", "")
        body = issue.get("body") or ""
        stacktrace_coords = self.extract_stacktrace_coordinates(body)

        indexed_path_map = {f["path"].lower(): f for f in indexed_files}
        candidate_files = []

        # 1. Match from stack traces (Highest confidence)
        for st in stacktrace_coords:
            match_file = indexed_path_map.get(st["file_path"].lower())
            if match_file:
                candidate_files.append({
                    "path": match_file["path"],
                    "start_line": st["line_start"],
                    "end_line": st["line_end"],
                    "symbol": st["symbol_name"],
                    "match_type": "STACKTRACE",
                    "reason": f"Directly referenced in stack trace at line {st['target_line']}.",
                    "status": "VERIFIED"
                })

        # 2. Match from file name mentions in text
        words = re.findall(r'([a-zA-Z0-9_\-/]+\.(?:py|js|ts|tsx))', body + " " + title)
        for w in words:
            w_lower = w.lower()
            if w_lower in indexed_path_map and not any(c["path"].lower() == w_lower for c in candidate_files):
                candidate_files.append({
                    "path": indexed_path_map[w_lower]["path"],
                    "start_line": 1,
                    "end_line": 50,
                    "symbol": "Module Scope",
                    "match_type": "AST_SYMBOL",
                    "reason": "File explicitly mentioned in issue description.",
                    "status": "VERIFIED"
                })

        # 3. Match test files
        for f in indexed_files:
            if f.get("is_test") and any(c["path"].split("/")[-1].replace(".py", "") in f["path"] for c in candidate_files):
                candidate_files.append({
                    "path": f["path"],
                    "start_line": 1,
                    "end_line": 40,
                    "symbol": "Test Suite",
                    "match_type": "GRAPH_EXPANSION",
                    "reason": "Test file covering matching source module.",
                    "status": "VERIFIED"
                })

        # Fallback if no files indexed match directly
        if not candidate_files:
            candidate_files.append({
                "path": "src/ or repository entrypoint",
                "start_line": 1,
                "end_line": 20,
                "symbol": "Top-level Entrypoint",
                "match_type": "LEXICAL",
                "reason": "No direct file match in snapshot; entrypoint investigation recommended.",
                "status": "INFERRED"
            })

        # Construct Execution Path
        target_path = candidate_files[0]["path"] if candidate_files else "src/main.py"
        likely_path = [
            f"1. Entrypoint loads user parameters or environment configuration.",
            f"2. Execution dispatches to `{target_path}` around cited line bounds.",
            f"3. Failure condition is encountered when missing or malformed inputs trigger unhandled behavior.",
            f"4. Automated test suite in `tests/` should assert correct handling and prevent future regressions."
        ]

        # Reality Check Categories
        known_facts = [
            {"claim": f"Issue #{issue.get('number', 0)} is recorded with state '{issue.get('state', 'open')}'.", "status": "VERIFIED"},
            {"claim": f"Repository snapshot pinned to commit SHA `{commit_sha[:8]}`.", "status": "VERIFIED"},
        ]
        if stacktrace_coords:
            known_facts.append({"claim": f"Stack trace explicitly identifies line {stacktrace_coords[0]['target_line']} in `{stacktrace_coords[0]['file_path']}`.", "status": "VERIFIED"})

        inferred_hypotheses = [
            {"claim": f"The issue behavior is localized to `{target_path}` rather than an architectural redesign.", "status": "INFERRED"},
            {"claim": "A minimal patch with defensive input validation or error default will resolve the failure.", "status": "INFERRED"}
        ]

        explicit_unknowns = [
            {"claim": "Whether maintainers prefer a default fallback value or an explicit custom exception.", "status": "UNKNOWN"},
            {"claim": "Whether external service credentials or unmocked network access are needed for end-to-end testing.", "status": "UNKNOWN"}
        ]

        alternative_explanations = [
            "The error could stem from an environment variable missing from `.env` rather than a code defect.",
            "A recent dependency version upgrade may have changed third-party API return types."
        ]

        minimal_next_step = f"Locate `{target_path}` in the local repository and run the corresponding test file to verify reproduction."

        return {
            "issue_id": f"{repo_id}:{issue.get('number')}",
            "repository_id": repo_id,
            "commit_sha": commit_sha,
            "candidate_files": candidate_files,
            "likely_execution_path": likely_path,
            "known_facts": known_facts,
            "inferred_hypotheses": inferred_hypotheses,
            "explicit_unknowns": explicit_unknowns,
            "alternative_explanations": alternative_explanations,
            "minimal_next_step": minimal_next_step
        }

    def generate_maintainer_drafts(
        self,
        issue: Dict[str, Any],
        triage_data: Optional[Dict[str, Any]],
        repo_id: str
    ) -> List[Dict[str, str]]:
        """
        Generates 4 polite, maintainer-friendly communication templates
        that users can review, edit, and send themselves via GitHub.
        """
        number = issue.get("number", 0)
        title = issue.get("title", "")
        user_summary = triage_data.get("user_summary") if triage_data else "the behavior reported"
        repro_notes = triage_data.get("reproduction_notes") if triage_data else "reproduced locally"

        return [
            {
                "draft_type": "ask_if_wanted",
                "label": "Ask if Fix is Wanted",
                "subject": f"Inquiring before starting work on #{number}",
                "body": (
                    f"Hi maintainers! 👋\n\n"
                    f"I'm a first-time contributor interested in helping with #{number} ({title}).\n\n"
                    f"Before diving in, I wanted to check: is this issue still open and would a PR addressing "
                    f"this be welcomed? I'm planning to keep the change minimal and add regression test coverage.\n\n"
                    f"Thanks for your time and guidance!"
                )
            },
            {
                "draft_type": "request_clarification",
                "label": "Request Clarification",
                "subject": f"Clarification question on #{number}",
                "body": (
                    f"Hi team! Regarding #{number} ({title}), I'm looking into this and wanted to confirm expected behavior:\n\n"
                    f"When {user_summary}, what would be the preferred resolution?\n"
                    f"- Should we provide a sensible default fallback value, or\n"
                    f"- Raise a descriptive project-specific exception?\n\n"
                    f"Any guidance on preferred conventions in {repo_id} would be greatly appreciated!"
                )
            },
            {
                "draft_type": "reproduction_report",
                "label": "Share Reproduction Report",
                "subject": f"Local reproduction notes for #{number}",
                "body": (
                    f"Hi everyone, I was able to verify and reproduce this locally:\n\n"
                    f"**Reproduction Steps:**\n{repro_notes}\n\n"
                    f"**Observed Behavior:** {triage_data.get('actual_behavior', 'Raises unhandled exception') if triage_data else 'Confirmed unhandled error'}\n"
                    f"**Expected Behavior:** {triage_data.get('expected_behavior', 'Should handle gracefully with test coverage') if triage_data else 'Graceful handling'}\n\n"
                    f"I have a minimal test case ready and can submit a PR if this approach sounds good."
                )
            },
            {
                "draft_type": "review_response",
                "label": "Respond to Code Review",
                "subject": f"Addressing review comments on #{number}",
                "body": (
                    f"Thank you for the thoughtful review and feedback! 🙏\n\n"
                    f"I have addressed the requested changes:\n"
                    f"1. Refactored the handling to match existing project conventions.\n"
                    f"2. Added a dedicated regression test case to verify the fix.\n"
                    f"3. Verified that the test suite passes locally with zero regressions.\n\n"
                    f"Please let me know if any further adjustments are needed!"
                )
            }
        ]

issue_service = IssueIntelligenceService()
