"""Contribution Policy Radar Service.

Analyzes repository contribution policies, AI guidelines, issue assignment rules,
and historical community responsiveness to guide contributors ethically.
"""

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AIPolicyStatus(str, Enum):
    BANNED = "banned"
    DISCLOSURE_REQUIRED = "disclosure_required"
    ALLOWED = "allowed"
    NOT_FOUND = "not_found"
    UNCLEAR = "unclear"


class WelcomenessRating(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    UNKNOWN = "unknown"


class PolicyEvidence(BaseModel):
    source_file: str
    line_number: Optional[int] = None
    snippet: str
    rule_category: str


class PolicyRadarReport(BaseModel):
    repository: str
    ai_policy: AIPolicyStatus
    requires_assignment_first: Optional[bool] = None
    external_merge_ratio: Optional[float] = None
    median_first_response_hours: Optional[float] = None
    welcomeness: WelcomenessRating
    evidence_refs: List[PolicyEvidence] = Field(default_factory=list)
    collection_timestamp: str
    sample_sizes: Dict[str, int] = Field(default_factory=dict)
    contributor_guidance: str
    learn_mode_recommended: bool = False


class PolicyRadarService:
    POLICY_FILENAMES = [
        "CONTRIBUTING.md",
        "contributing.md",
        "CONTRIBUTING.rst",
        ".github/CONTRIBUTING.md",
        ".github/contributing.md",
        "AI.md",
        "AI_POLICY.md",
        "docs/CONTRIBUTING.md",
        "AGENTS.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
    ]

    AI_BAN_PATTERNS = [
        r"\b(?:no|do not|never|prohibit(?:ed)?|ban(?:ned)?)\b.*?\b(?:ai|llm|copilot|chatgpt|automated)\b.*?\b(?:pr|pull request|contribution|code)\b",
        r"\b(?:ai|llm|chatgpt|copilot)\b.*?\b(?:contributions?|code|pr|pull request)s?\b.*?\b(?:prohibited|forbidden|rejected|not accepted|banned)\b",
        r"\bwe do not accept (?:ai|llm|generated) (?:code|pr|pull request)s?\b",
    ]

    AI_DISCLOSURE_PATTERNS = [
        r"\bdisclose\b.*?\b(?:ai|llm|copilot|automated)\b",
        r"\bstate if (?:ai|llm|copilot) was used\b",
        r"\bmention in the PR if you used (?:ai|llm|copilot)\b",
        r"\bdeclare any ai assistance\b",
    ]

    AI_ALLOWED_PATTERNS = [
        r"\bai (?:assistance|generated code) is (?:welcome|allowed|accepted|permitted)\b",
        r"\bfeel free to use ai tools\b",
    ]

    ASSIGNMENT_PATTERNS = [
        r"\bask to be assigned before working\b",
        r"\bplease wait to be assigned\b",
        r"\bdo not open a pr without being assigned\b",
        r"\bcomment.*?to be assigned\b",
        r"\bissues must be assigned first\b",
    ]

    def analyze_repository_policies(
        self,
        repository: str,
        files_dict: Dict[str, str],
        closed_prs: Optional[List[Dict[str, Any]]] = None,
    ) -> PolicyRadarReport:
        evidence_list: List[PolicyEvidence] = []
        ai_policy = AIPolicyStatus.NOT_FOUND
        requires_assignment = None

        has_ban_match = False
        has_disclosure_match = False
        has_allowed_match = False

        # Scan files for policy rules
        for filename, content in files_dict.items():
            fn_lower = filename.lower().replace("\\", "/")
            if not any(target in fn_lower for target in ["contribut", "ai", "pr_template", "pull_request_template", "agents"]):
                continue

            lines = content.splitlines()
            for idx, line in enumerate(lines, start=1):
                ll = line.lower()

                # Check assignment
                for p in self.ASSIGNMENT_PATTERNS:
                    if re.search(p, ll):
                        requires_assignment = True
                        evidence_list.append(
                            PolicyEvidence(
                                source_file=filename,
                                line_number=idx,
                                snippet=line.strip(),
                                rule_category="assignment_first",
                            )
                        )
                        break

                # Check AI ban
                for p in self.AI_BAN_PATTERNS:
                    if re.search(p, ll):
                        has_ban_match = True
                        evidence_list.append(
                            PolicyEvidence(
                                source_file=filename,
                                line_number=idx,
                                snippet=line.strip(),
                                rule_category="ai_ban",
                            )
                        )
                        break

                # Check AI disclosure
                for p in self.AI_DISCLOSURE_PATTERNS:
                    if re.search(p, ll):
                        has_disclosure_match = True
                        evidence_list.append(
                            PolicyEvidence(
                                source_file=filename,
                                line_number=idx,
                                snippet=line.strip(),
                                rule_category="ai_disclosure",
                            )
                        )
                        break

                # Check AI allowed
                for p in self.AI_ALLOWED_PATTERNS:
                    if re.search(p, ll):
                        has_allowed_match = True
                        evidence_list.append(
                            PolicyEvidence(
                                source_file=filename,
                                line_number=idx,
                                snippet=line.strip(),
                                rule_category="ai_allowed",
                            )
                        )
                        break

        # Resolve AI policy status with deterministic priority & ambiguity checks
        if has_ban_match and (has_allowed_match or has_disclosure_match):
            ai_policy = AIPolicyStatus.UNCLEAR
        elif has_ban_match:
            ai_policy = AIPolicyStatus.BANNED
        elif has_disclosure_match:
            ai_policy = AIPolicyStatus.DISCLOSURE_REQUIRED
        elif has_allowed_match:
            ai_policy = AIPolicyStatus.ALLOWED
        else:
            ai_policy = AIPolicyStatus.NOT_FOUND

        # Analyze historical PR metrics if provided
        external_merge_ratio = None
        median_first_resp = None
        sample_size = len(closed_prs) if closed_prs else 0

        # Strict requirement: fewer than 10 PRs must produce external_merge_ratio = None
        if closed_prs and sample_size >= 10:
            merged_count = sum(1 for pr in closed_prs if pr.get("merged") or pr.get("merged_at"))
            external_merge_ratio = round(merged_count / sample_size, 3)

            # Response times
            resp_times = []
            for pr in closed_prs:
                hours = pr.get("first_response_hours")
                if hours is not None:
                    resp_times.append(float(hours))
            if resp_times:
                resp_times.sort()
                mid = len(resp_times) // 2
                median_first_resp = resp_times[mid] if len(resp_times) % 2 != 0 else (resp_times[mid - 1] + resp_times[mid]) / 2

        # Welcomeness classification
        welcomeness = WelcomenessRating.UNKNOWN
        if ai_policy == AIPolicyStatus.BANNED:
            welcomeness = WelcomenessRating.RED
        elif external_merge_ratio is not None:
            if external_merge_ratio >= 0.5:
                welcomeness = WelcomenessRating.GREEN
            elif external_merge_ratio >= 0.2:
                welcomeness = WelcomenessRating.YELLOW
            else:
                welcomeness = WelcomenessRating.RED
        elif ai_policy in (AIPolicyStatus.ALLOWED, AIPolicyStatus.DISCLOSURE_REQUIRED):
            welcomeness = WelcomenessRating.GREEN

        # Guidance and Learn Mode determination
        learn_mode = False
        if ai_policy == AIPolicyStatus.BANNED:
            learn_mode = True
            guidance = (
                "⚠️ AI-generated contributions are explicitly prohibited in this repository. "
                "FirstPatch AI has switched to 'Learn Mode': code generation is disabled to protect your reputation "
                "and respect maintainers. You will receive repository explanations and a self-authoring checklist."
            )
        elif ai_policy == AIPolicyStatus.DISCLOSURE_REQUIRED:
            guidance = (
                "ℹ️ This repository requires explicit disclosure of AI assistance. "
                "The PR package generator will automatically insert standard disclosure statements."
            )
        elif ai_policy == AIPolicyStatus.NOT_FOUND:
            guidance = (
                "⚠️ No explicit AI contribution policy was detected. "
                "Exercise caution and prioritize human understanding before submitting changes."
            )
        elif ai_policy == AIPolicyStatus.UNCLEAR:
            guidance = (
                "⚠️ Conflicting statements regarding AI contributions were detected. "
                "We recommend clarifying with maintainers in the issue discussion before opening a PR."
            )
        else:
            guidance = "✅ Contribution policy permits AI assistance when properly validated."

        if requires_assignment:
            guidance += " Note: Maintainers request that you ask to be assigned to an issue before opening a PR."

        return PolicyRadarReport(
            repository=repository,
            ai_policy=ai_policy,
            requires_assignment_first=requires_assignment,
            external_merge_ratio=external_merge_ratio,
            median_first_response_hours=median_first_resp,
            welcomeness=welcomeness,
            evidence_refs=evidence_list,
            collection_timestamp=datetime.now(timezone.utc).isoformat(),
            sample_sizes={"closed_prs": sample_size},
            contributor_guidance=guidance,
            learn_mode_recommended=learn_mode,
        )
