"""Repository Review Memory.

Ingests a bounded sample of historical PR review comments, extracts deterministic
review themes (tests requested, typing, naming, breaking changes, etc.), and ensures
that review guidance is strictly evidence-backed (minimum 2 independent comments).
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReviewComment(BaseModel):
    repository: str
    pr_number: int
    file_path: Optional[str] = None
    excerpt: str
    comment_url: Optional[str] = None
    timestamp: str


class ReviewThemeResult(BaseModel):
    theme: str
    description: str
    frequency: int
    sample_size: int
    supporting_comments: List[ReviewComment] = Field(default_factory=list)
    descriptive_summary: str
    is_supported: bool  # True iff >= min_evidence_threshold (default 2)


class ReviewMemoryService:
    THEME_PATTERNS = {
        "tests_requested": {
            "name": "Additional Tests Requested",
            "regex": r"\b(?:add|write|missing|need|include)\b.*?\b(?:unit\s+)?tests?\b",
        },
        "naming_conventions": {
            "name": "Naming & Style Conventions",
            "regex": r"\b(?:rename|naming|variable\s+name|function\s+name|camelcase|snake_case)\b",
        },
        "documentation_updates": {
            "name": "Documentation & Changelog",
            "regex": r"\b(?:docstring|docs?|documentation|changelog|readme|update\s+docs)\b",
        },
        "type_annotations": {
            "name": "Type Annotations & Hints",
            "regex": r"\b(?:typing|type\s+hints?|annotations?|mypy|signature)\b",
        },
        "backward_compatibility": {
            "name": "Backward Compatibility & Breaking Changes",
            "regex": r"\b(?:backward|breaking\s+change|deprecat|backwards\s+compatible)\b",
        },
        "error_handling": {
            "name": "Error & Exception Handling",
            "regex": r"\b(?:error\s+handling|raise|catch|exception|try-except|graceful)\b",
        },
        "edge_cases": {
            "name": "Edge Cases & Null Checks",
            "regex": r"\b(?:edge\s+case|boundary|null|none\s+check|empty\s+list)\b",
        },
        "pr_scope": {
            "name": "PR Scope Too Broad",
            "regex": r"\b(?:too\s+large|split\s+this|separate\s+pr|narrow\s+the\s+scope)\b",
        },
    }

    def __init__(self, max_comments_cap: int = 500, min_evidence_threshold: int = 2):
        self.max_comments_cap = max_comments_cap
        self.min_evidence_threshold = min_evidence_threshold

    def analyze_comments(
        self,
        repository: str,
        raw_comments: List[Dict[str, Any]],
        filter_file_path: Optional[str] = None,
    ) -> List[ReviewThemeResult]:
        # Bounded intake
        bounded_raw = raw_comments[: self.max_comments_cap]

        parsed: List[ReviewComment] = []
        seen_comment_signatures = set()
        for c in bounded_raw:
            body = (c.get("body") or "").strip()
            if not body:
                continue
            path = c.get("path")
            if filter_file_path and path and filter_file_path.lower() not in path.lower():
                continue

            # Deduplicate: exact duplicate comments do not count as independent evidence
            sig = (
                c.get("pr_number") or c.get("pull_request_number") or 0,
                path or "",
                body.strip().lower(),
            )
            if sig in seen_comment_signatures:
                continue
            seen_comment_signatures.add(sig)

            parsed.append(
                ReviewComment(
                    repository=repository,
                    pr_number=c.get("pr_number") or c.get("pull_request_number") or 0,
                    file_path=path,
                    excerpt=body[:200],
                    comment_url=c.get("html_url") or c.get("url"),
                    timestamp=c.get("created_at", ""),
                )
            )

        total_sample = len(parsed)
        if total_sample == 0:
            return []

        results: List[ReviewThemeResult] = []

        for theme_key, meta in self.THEME_PATTERNS.items():
            pattern = re.compile(meta["regex"], re.IGNORECASE)
            matching: List[ReviewComment] = []
            seen_prs = set()

            for comm in parsed:
                if pattern.search(comm.excerpt):
                    matching.append(comm)
                    if comm.pr_number:
                        seen_prs.add(comm.pr_number)

            count = len(matching)
            distinct_prs = len(seen_prs) if seen_prs else count
            is_sup = count >= self.min_evidence_threshold

            summary = (
                f"Among the {total_sample} reviewed PR comments sampled, "
                f"'{meta['name']}' was flagged in {count} comments across {distinct_prs} PR(s)."
            )

            results.append(
                ReviewThemeResult(
                    theme=theme_key,
                    description=meta["name"],
                    frequency=count,
                    sample_size=total_sample,
                    supporting_comments=matching,
                    descriptive_summary=summary,
                    is_supported=is_sup,
                )
            )

        # Sort by frequency descending
        results.sort(key=lambda r: r.frequency, reverse=True)
        return results
