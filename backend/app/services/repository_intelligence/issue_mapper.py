"""
FirstPatch AI — Phase 2 Real GitHub Issue-to-Code Mapping

Bridges GitHub issues to concrete source code locations in the pinned repository snapshot.
Integrates with the 7-criterion deterministic readiness scoring while grounding
relevant files with verified AST symbols, line numbers, and evidence references.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from app.schemas.models import (
    EvidenceRef,
    GitHubIssue,
    IssueMatchRequest,
    IssueMatchResponse,
    MatchedIssue,
    RepositoryOverview,
)
from app.services.github.client import GitHubService
from app.services.issue_matching.engine import (
    _parse_github_issue,
    _score_issue,
    _SCORING_EXPLANATION,
)
from app.services.repository_intelligence.evidence_extractor import EvidenceExtractor
from app.services.repository_intelligence.schemas import (
    CodeStructureReport,
    CodeSymbol,
    RepositorySnapshot,
    SourceMappingResult,
)

logger = logging.getLogger(__name__)

_STOP_WORDS = {
    "the", "a", "an", "is", "it", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "not", "with", "this", "that", "have",
    "has", "be", "are", "was", "were", "will", "would", "could",
    "should", "when", "where", "how", "what", "why", "which", "who",
    "fix", "bug", "issue", "error", "problem", "please", "help",
}


class IssueToCodeMapper:
    """
    Deterministically maps candidate issues to source files using
    AST symbols, file paths, and structural relationships.
    """

    def __init__(self, github: GitHubService):
        self.github = github

    def map_issue_to_source(
        self,
        issue: GitHubIssue,
        snapshot: RepositorySnapshot,
        code_report: Optional[CodeStructureReport] = None,
    ) -> SourceMappingResult:
        """
        Map an issue to repository source files.
        Returns matched files, AST symbols, line ranges, and confidence.
        Honest: returns has_reliable_mapping=False if evidence is insufficient.
        """
        title = issue.title or ""
        body = issue.body or ""
        combined_text = f"{title}\n{body}"

        heuristic_reasons: list[str] = []
        missing_evidence_notes: list[str] = []
        evidence_refs: list[EvidenceRef] = []
        matched_symbols: list[CodeSymbol] = []
        relevant_files_set: set[str] = set()

        # Step 1: Extract keywords, potential paths, and identifiers from issue text
        keywords = _extract_keywords(combined_text)
        explicit_path_mentions = _find_explicit_paths(combined_text, snapshot.file_paths)

        # Add explicitly mentioned paths if they exist in snapshot
        for path in explicit_path_mentions:
            relevant_files_set.add(path)
            ref, _ = EvidenceExtractor.from_file_presence(
                snapshot,
                path,
                claim_text=f"File '{path}' is explicitly mentioned in issue #{issue.number} description",
            )
            evidence_refs.append(ref)
            heuristic_reasons.append(f"Explicit path mention in issue text: '{path}'")

        # Step 2: Match against extracted AST symbols
        if code_report and keywords:
            for kw in keywords:
                # Find matching symbols
                found_syms = code_report.find_symbols(kw)
                for sym in found_syms:
                    if sym.name.lower() == kw.lower() or f"{kw}_" in sym.name.lower():
                        matched_symbols.append(sym)
                        relevant_files_set.add(sym.file_path)
                        ref, _ = EvidenceExtractor.from_symbol(
                            sym,
                            snapshot.owner,
                            snapshot.repo,
                            snapshot.default_branch,
                        )
                        evidence_refs.append(ref)
                        heuristic_reasons.append(
                            f"Matched AST symbol '{sym.name}' ({sym.symbol_type.value}) "
                            f"in '{sym.file_path}#L{sym.start_line}-L{sym.end_line}'"
                        )

        # Step 3: Match against file paths if no symbols matched
        if not relevant_files_set:
            for file_entry in snapshot.files:
                path_lower = file_entry.path.lower()
                base_name = path_lower.split("/")[-1].split(".")[0]
                if any(kw == base_name or (len(kw) > 4 and kw in base_name) for kw in keywords):
                    relevant_files_set.add(file_entry.path)
                    ref, _ = EvidenceExtractor.from_file_presence(
                        snapshot,
                        file_entry.path,
                        claim_text=f"File path '{file_entry.path}' matches issue keyword",
                    )
                    evidence_refs.append(ref)
                    heuristic_reasons.append(f"Keyword match against filename: '{file_entry.path}'")

        # Step 4: Assess mapping confidence honestly
        has_reliable_mapping = False
        confidence = "none"

        if explicit_path_mentions:
            confidence = "high"
            has_reliable_mapping = True
        elif matched_symbols:
            confidence = "medium"
            has_reliable_mapping = True
        elif relevant_files_set:
            confidence = "low"
            has_reliable_mapping = False
            missing_evidence_notes.append(
                "Files were identified by heuristic keyword matching on filenames only. "
                "No exact AST symbols or explicit path mentions were confirmed."
            )
        else:
            confidence = "none"
            has_reliable_mapping = False
            missing_evidence_notes.append(
                "Could not establish a reliable connection between issue text "
                "and repository source files. Manual exploration is required."
            )

        return SourceMappingResult(
            issue_number=issue.number,
            relevant_files=sorted(list(relevant_files_set))[:5],
            matched_symbols=matched_symbols[:10],
            evidence_refs=evidence_refs[:10],
            confidence=confidence,
            heuristic_reasons=heuristic_reasons,
            missing_evidence_notes=missing_evidence_notes,
            has_reliable_mapping=has_reliable_mapping,
        )

    def rank_issues_with_evidence(
        self,
        request: IssueMatchRequest,
        snapshot: RepositorySnapshot,
        repo_overview: RepositoryOverview,
        raw_issues: list[dict[str, Any]],
        code_report: Optional[CodeStructureReport] = None,
    ) -> IssueMatchResponse:
        """
        Rank candidate issues using the 7-criterion deterministic scoring engine,
        enhanced with concrete source file mappings from the pinned snapshot.
        """
        warnings: list[str] = []

        if not raw_issues:
            return IssueMatchResponse(
                owner=request.owner,
                repo=request.repo,
                matched_issues=[],
                total_issues_considered=0,
                scoring_explanation=_SCORING_EXPLANATION,
                warnings=["No open issues found in this repository."],
            )

        matched: list[MatchedIssue] = []

        for raw in raw_issues:
            issue = _parse_github_issue(raw, request.owner, request.repo)
            # Rule: Exclude pull requests from beginner issue discovery
            if issue.is_pull_request:
                continue

            # Standard 7-criterion scoring preservation
            scored_issue = _score_issue(issue, request, repo_overview)

            # Map to source code
            mapping = self.map_issue_to_source(issue, snapshot, code_report)
            if mapping.relevant_files:
                scored_issue.relevant_files = mapping.relevant_files

            matched.append(scored_issue)

        # Sort: highest score first, then most recently updated
        matched.sort(
            key=lambda m: (m.total_score, m.issue.updated_at.timestamp()),
            reverse=True,
        )

        return IssueMatchResponse(
            owner=request.owner,
            repo=request.repo,
            matched_issues=matched,
            total_issues_considered=len(raw_issues),
            scoring_explanation=_SCORING_EXPLANATION,
            warnings=warnings,
        )


def _extract_keywords(text: str) -> list[str]:
    """Extract significant keywords and identifiers from text."""
    words = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b", text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 3][:20]


def _find_explicit_paths(text: str, known_paths: set[str]) -> list[str]:
    """Find file paths in text that actually exist in the repository snapshot."""
    found: list[str] = []
    # Match strings with slashes or standard code extensions
    candidates = re.findall(r"[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+", text)
    for c in candidates:
        clean = c.strip("`'\"(),:;")
        if clean in known_paths and clean not in found:
            found.append(clean)
    return found
