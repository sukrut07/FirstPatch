"""
FirstPatch AI — Phase 2 Evidence Extractor

Extracts structured EvidenceRef and ClaimRecord instances from repository artifacts:
- AST symbols (functions, classes, imports, routes)
- Manifest declarations
- Test directories and configuration files
- README statements
- GitHub issue fields
"""
from __future__ import annotations

from typing import Optional
from uuid import uuid4

from app.schemas.models import EvidenceRef, EvidenceStatus, EvidenceType
from app.services.repository_intelligence.schemas import (
    ClaimRecord,
    CodeSymbol,
    RepositorySnapshot,
)


class EvidenceExtractor:
    """Extracts verifiable evidence records from repository components."""

    @staticmethod
    def from_symbol(
        symbol: CodeSymbol,
        owner: str,
        repo: str,
        default_branch: str,
    ) -> tuple[EvidenceRef, ClaimRecord]:
        """Convert an extracted CodeSymbol to both an EvidenceRef and a ClaimRecord."""
        github_url = (
            f"https://github.com/{owner}/{repo}/blob/{symbol.snapshot_sha}/"
            f"{symbol.file_path}#L{symbol.start_line}-L{symbol.end_line}"
        )
        claim_id = uuid4()
        claim_text = f"Symbol '{symbol.name}' ({symbol.symbol_type.value}) is defined in '{symbol.file_path}'"

        ref = EvidenceRef(
            id=claim_id,
            owner=owner,
            repo=repo,
            commit_sha=symbol.snapshot_sha,
            file_path=symbol.file_path,
            github_url=github_url,
            start_line=symbol.start_line,
            end_line=symbol.end_line,
            evidence_type=(
                EvidenceType.AST_FUNCTION
                if "function" in symbol.symbol_type.value
                else EvidenceType.CONFIG_DECLARATION
            ),
            excerpt=symbol.excerpt,
            status=EvidenceStatus.VERIFIED,
            confidence_note=None,
        )

        claim = ClaimRecord(
            claim_id=claim_id,
            claim_text=claim_text,
            evidence_type=ref.evidence_type,
            commit_sha=symbol.snapshot_sha,
            file_path=symbol.file_path,
            start_line=symbol.start_line,
            end_line=symbol.end_line,
            excerpt=symbol.excerpt,
            status=EvidenceStatus.VERIFIED,
        )

        return ref, claim

    @staticmethod
    def from_file_presence(
        snapshot: RepositorySnapshot,
        file_path: str,
        claim_text: Optional[str] = None,
    ) -> tuple[EvidenceRef, ClaimRecord]:
        """Create evidence for a file present in the pinned snapshot."""
        claim_id = uuid4()
        text = claim_text or f"File '{file_path}' exists in repository snapshot {snapshot.commit_sha[:8]}"
        github_url = f"https://github.com/{snapshot.owner}/{snapshot.repo}/blob/{snapshot.commit_sha}/{file_path}"

        ref = EvidenceRef(
            id=claim_id,
            owner=snapshot.owner,
            repo=snapshot.repo,
            commit_sha=snapshot.commit_sha,
            file_path=file_path,
            github_url=github_url,
            evidence_type=EvidenceType.DIRECTORY_STRUCTURE,
            excerpt=f"File '{file_path}' exists in repository tree",
            status=EvidenceStatus.VERIFIED,
            confidence_note=None,
        )

        claim = ClaimRecord(
            claim_id=claim_id,
            claim_text=text,
            evidence_type=EvidenceType.DIRECTORY_STRUCTURE,
            commit_sha=snapshot.commit_sha,
            file_path=file_path,
            excerpt=ref.excerpt,
            status=EvidenceStatus.VERIFIED,
        )

        return ref, claim
