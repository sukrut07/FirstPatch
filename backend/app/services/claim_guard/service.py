"""Issue Claim and Duplicate-PR Guard Service.

Prevents contributors from wasting effort on already-assigned, already-claimed,
closed, or actively addressed issues.
"""

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IssueReadinessStatus(str, Enum):
    AVAILABLE = "available"
    ALREADY_ASSIGNED = "already_assigned"
    ALREADY_CLAIMED = "already_claimed"
    HAS_OPEN_PR = "has_open_pr"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class ClaimEvidence(BaseModel):
    category: str
    source_url: Optional[str] = None
    author: Optional[str] = None
    snippet: str
    detected_at: str


class ClaimGuardReport(BaseModel):
    repository: str
    issue_number: int
    status: IssueReadinessStatus
    summary: str
    evidence: List[ClaimEvidence] = Field(default_factory=list)
    checked_at: str
    cached: bool = False


class ClaimGuardService:
    CLAIM_COMMENT_PATTERNS = [
        r"\b(?:i(?:'d| would)? like to (?:work on|take|handle|fix) this)\b",
        r"\bcan i (?:please )?(?:be assigned|take this|work on this)\b",
        r"\bassign (?:this to me|me(?: please)?)\b",
        r"\bworking on (?:a fix|this|a pr)\b",
        r"\bi am working on this\b",
    ]

    PR_LINK_PATTERNS = [
        r"(?:fixes|closes|resolves|address(?:es)?)\s+#?{issue_number}\b",
    ]

    def __init__(self, cache_ttl_seconds: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl_seconds = cache_ttl_seconds

    def check_issue_readiness(
        self,
        repository: str,
        issue_data: Optional[Dict[str, Any]],
        comments: Optional[List[Dict[str, Any]]] = None,
        open_prs: Optional[List[Dict[str, Any]]] = None,
        force_refresh: bool = False,
    ) -> ClaimGuardReport:
        now_iso = datetime.now(timezone.utc).isoformat()
        if not issue_data or "number" not in issue_data:
            return ClaimGuardReport(
                repository=repository,
                issue_number=issue_data.get("number", 0) if issue_data else 0,
                status=IssueReadinessStatus.UNKNOWN,
                summary="Insufficient or missing issue metadata to evaluate readiness.",
                evidence=[],
                checked_at=now_iso,
                cached=False,
            )

        issue_num = int(issue_data["number"])
        cache_key = f"{repository}#{issue_num}"

        # Cache check
        if not force_refresh and cache_key in self._cache:
            entry = self._cache[cache_key]
            entry_time = datetime.fromisoformat(entry["checked_at"])
            age = (datetime.now(timezone.utc) - entry_time).total_seconds()
            if age < self.cache_ttl_seconds:
                cached_report = ClaimGuardReport(**entry["report"])
                cached_report.cached = True
                return cached_report

        # 1. Check if closed
        state = str(issue_data.get("state", "open")).lower()
        if state != "open":
            ev = ClaimEvidence(
                category="issue_closed",
                source_url=issue_data.get("html_url"),
                snippet=f"Issue state is '{state}'.",
                detected_at=now_iso,
            )
            report = ClaimGuardReport(
                repository=repository,
                issue_number=issue_num,
                status=IssueReadinessStatus.CLOSED,
                summary=f"Issue #{issue_num} is closed and cannot be contributed to.",
                evidence=[ev],
                checked_at=now_iso,
            )
            self._cache[cache_key] = {"report": report.model_dump(), "checked_at": now_iso}
            return report

        # 2. Check assignees
        assignees = issue_data.get("assignees") or []
        single_assignee = issue_data.get("assignee")
        if single_assignee and single_assignee not in assignees:
            assignees.append(single_assignee)

        assignee_logins = [
            a.get("login") if isinstance(a, dict) else str(a) for a in assignees if a
        ]
        if assignee_logins:
            ev = ClaimEvidence(
                category="assigned",
                source_url=issue_data.get("html_url"),
                author=", ".join(assignee_logins),
                snippet=f"Assigned to {', '.join(assignee_logins)}.",
                detected_at=now_iso,
            )
            report = ClaimGuardReport(
                repository=repository,
                issue_number=issue_num,
                status=IssueReadinessStatus.ALREADY_ASSIGNED,
                summary=f"Issue #{issue_num} is already assigned to {', '.join(assignee_logins)}.",
                evidence=[ev],
                checked_at=now_iso,
            )
            self._cache[cache_key] = {"report": report.model_dump(), "checked_at": now_iso}
            return report

        # 3. Check open PRs referencing this issue
        if open_prs:
            target_regex = re.compile(rf"(?:fixes|closes|resolves|address(?:es)?)\s+#?{issue_num}\b", re.IGNORECASE)
            for pr in open_prs:
                title = pr.get("title", "")
                body = pr.get("body", "") or ""
                text = f"{title}\n{body}"
                if target_regex.search(text):
                    ev = ClaimEvidence(
                        category="open_pr_reference",
                        source_url=pr.get("html_url"),
                        author=pr.get("user", {}).get("login") if isinstance(pr.get("user"), dict) else None,
                        snippet=f"Open PR #{pr.get('number')} references issue #{issue_num}: '{title}'",
                        detected_at=now_iso,
                    )
                    report = ClaimGuardReport(
                        repository=repository,
                        issue_number=issue_num,
                        status=IssueReadinessStatus.HAS_OPEN_PR,
                        summary=f"Issue #{issue_num} already has an active open PR (#{pr.get('number')}).",
                        evidence=[ev],
                        checked_at=now_iso,
                    )
                    self._cache[cache_key] = {"report": report.model_dump(), "checked_at": now_iso}
                    return report

        # 4. Check comments for explicit claim intent
        if comments:
            for comment in comments:
                c_body = comment.get("body", "") or ""
                c_user = comment.get("user", {}).get("login") if isinstance(comment.get("user"), dict) else "unknown"
                for pat in self.CLAIM_COMMENT_PATTERNS:
                    if re.search(pat, c_body, re.IGNORECASE):
                        ev = ClaimEvidence(
                            category="claim_comment",
                            source_url=comment.get("html_url"),
                            author=c_user,
                            snippet=f"Comment by @{c_user}: \"{c_body.strip()[:120]}\"",
                            detected_at=now_iso,
                        )
                        report = ClaimGuardReport(
                            repository=repository,
                            issue_number=issue_num,
                            status=IssueReadinessStatus.ALREADY_CLAIMED,
                            summary=f"Issue #{issue_num} has an active claim request from @{c_user}.",
                            evidence=[ev],
                            checked_at=now_iso,
                        )
                        self._cache[cache_key] = {"report": report.model_dump(), "checked_at": now_iso}
                        return report

        # 5. Issue is available
        report = ClaimGuardReport(
            repository=repository,
            issue_number=issue_num,
            status=IssueReadinessStatus.AVAILABLE,
            summary=f"Issue #{issue_num} is open, unassigned, with no active claims or conflicting PRs.",
            evidence=[],
            checked_at=now_iso,
        )
        self._cache[cache_key] = {"report": report.model_dump(), "checked_at": now_iso}
        return report
