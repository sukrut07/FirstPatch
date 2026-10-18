import re
import json
from typing import List, Dict, Any, Optional

class IssueIntelligenceService:
    def __init__(self):
        pass

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

        # 1. Label Analysis
        beginner_labels = {"good first issue", "good-first-issue", "beginner", "easy", "starter", "first-timers-only"}
        doc_labels = {"documentation", "docs", "typo"}
        bug_labels = {"bug", "fix", "defect"}
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

        # 2. Body clarity & reproduction steps
        body_len = len(body.strip())
        if body_len < 40:
            fit_score -= 20
            potential_blockers.append("Very short issue description; requirements may be ambiguous.")
        elif body_len > 300:
            fit_score += 10
            reasons.append("Detailed issue description provided with context.")

        if re.search(r'(reproduce|steps to reproduce|traceback|error|expected behavior)', body, re.I):
            fit_score += 10
            reasons.append("Contains explicit reproduction steps or error traceback.")
        else:
            potential_blockers.append("No explicit reproduction steps found in the issue text.")

        # 3. Prerequisites detection
        if re.search(r'(pytest|fixture|mock|unittest)', body + title, re.I):
            prerequisite_skills.append("Unit testing with pytest / fixtures")
        if re.search(r'(async|await|coroutine|event loop)', body + title, re.I):
            prerequisite_skills.append("Asynchronous programming (async/await)")
            if user_skill_level == "Beginner":
                fit_score -= 10
                potential_blockers.append("Involves asynchronous control flow, which has a steeper learning curve.")
        if re.search(r'(docker|container|compose)', body + title, re.I):
            prerequisite_skills.append("Docker containerization")

        # 4. Complexity estimation
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

        # 5. Skill alignment adjustment
        if user_skill_level == "Beginner" and complexity == "Beginner":
            fit_score += 15
        elif user_skill_level == "Advanced" and complexity == "Advanced":
            fit_score += 15

        # 6. Relevant file heuristic extraction
        found_files = set(re.findall(r'([a-zA-Z0-9_\-/]+\.(?:py|js|ts|tsx|md|json|toml))', body + " " + title))
        relevant_files = list(found_files)[:5]

        # Clamp score between 10 and 99
        fit_score = max(10.0, min(99.0, fit_score))

        return {
            "fit_score": round(fit_score, 1),
            "skill_match": f"{round(fit_score)}% match for {user_skill_level}",
            "estimated_complexity": complexity,
            "estimated_effort": effort,
            "reasons": reasons if reasons else ["General open issue in the repository."],
            "potential_blockers": potential_blockers if potential_blockers else ["Ensure local environment is installed."],
            "relevant_files": relevant_files,
            "prerequisite_skills": prerequisite_skills if prerequisite_skills else ["Core programming fundamentals", "Git branch workflow"],
            "confidence": "High" if has_beginner_label or body_len > 400 else "Medium",
            "missing_info": "Maintainer response time is unknown until claimed."
        }

issue_service = IssueIntelligenceService()
