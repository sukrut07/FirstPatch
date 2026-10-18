"""
Tests for EvidenceValidator (Deterministic Repository Reality Checker)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.schemas.models import EvidenceStatus, EvidenceType
from app.services.repository_intelligence.evidence_validator import EvidenceValidator
from app.services.repository_intelligence.schemas import (
    ClaimRecord,
    RepoFileEntry,
    RepositorySnapshot,
)
from app.services.repository_intelligence.snapshot import RepositorySnapshotService

SNAPSHOT_SHA = "aaaa1111bbbb2222cccc3333dddd4444eeee5555"
STALE_SHA = "0000000000000000000000000000000000000000"

SAMPLE_FILE_CONTENT = """def calculate_discount(price: float, discount_percent: float) -> float:
    \"\"\"Calculate the discounted price.\"\"\"
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Invalid discount")
    return price * (1 - discount_percent / 100)
"""


@pytest.fixture
def mock_snapshot_service():
    service = MagicMock(spec=RepositorySnapshotService)
    service.get_file_content = AsyncMock(side_effect=lambda snap, path: SAMPLE_FILE_CONTENT if path == "pricing.py" else None)
    return service


@pytest.fixture
def sample_snapshot():
    return RepositorySnapshot(
        owner="test-org",
        repo="shop",
        canonical_url="https://github.com/test-org/shop",
        default_branch="main",
        commit_sha=SNAPSHOT_SHA,
        files=[
            RepoFileEntry(path="pricing.py", size=len(SAMPLE_FILE_CONTENT)),
            RepoFileEntry(path="README.md", size=100),
        ],
    )


@pytest.mark.asyncio
async def test_validate_claim_success(mock_snapshot_service, sample_snapshot):
    validator = EvidenceValidator(mock_snapshot_service)
    claim = ClaimRecord(
        claim_text="Function calculate_discount handles discount percentages",
        evidence_type=EvidenceType.AST_FUNCTION,
        commit_sha=SNAPSHOT_SHA,
        file_path="pricing.py",
        start_line=1,
        end_line=2,
        excerpt="def calculate_discount(price: float, discount_percent: float) -> float:",
        status=EvidenceStatus.VERIFIED,
    )

    result = await validator.validate_claim(sample_snapshot, claim)
    assert result.is_valid is True
    assert result.status == EvidenceStatus.VERIFIED
    assert "Verified" in result.reason


@pytest.mark.asyncio
async def test_validate_claim_missing_file_rejected(mock_snapshot_service, sample_snapshot):
    validator = EvidenceValidator(mock_snapshot_service)
    claim = ClaimRecord(
        claim_text="Database model is defined in missing.py",
        evidence_type=EvidenceType.AST_FUNCTION,
        commit_sha=SNAPSHOT_SHA,
        file_path="missing.py",
        status=EvidenceStatus.VERIFIED,
    )

    result = await validator.validate_claim(sample_snapshot, claim)
    assert result.is_valid is False
    assert result.status == EvidenceStatus.UNAVAILABLE
    assert "does not exist in snapshot" in result.reason


@pytest.mark.asyncio
async def test_validate_claim_stale_commit_sha(mock_snapshot_service, sample_snapshot):
    validator = EvidenceValidator(mock_snapshot_service)
    claim = ClaimRecord(
        claim_text="Function calculate_discount exists in old commit",
        evidence_type=EvidenceType.AST_FUNCTION,
        commit_sha=STALE_SHA,
        file_path="pricing.py",
        start_line=1,
        end_line=2,
        status=EvidenceStatus.VERIFIED,
    )

    result = await validator.validate_claim(sample_snapshot, claim)
    assert result.is_valid is False
    assert result.status == EvidenceStatus.STALE
    assert "references commit SHA" in result.reason


@pytest.mark.asyncio
async def test_validate_claim_invalid_line_range(mock_snapshot_service, sample_snapshot):
    validator = EvidenceValidator(mock_snapshot_service)
    # end_line < start_line
    claim = ClaimRecord(
        claim_text="Invalid line range",
        evidence_type=EvidenceType.AST_FUNCTION,
        commit_sha=SNAPSHOT_SHA,
        file_path="pricing.py",
        start_line=5,
        end_line=2,
    )
    result = await validator.validate_claim(sample_snapshot, claim)
    assert result.is_valid is False
    assert "Invalid range" in result.reason

    # start_line beyond file length
    claim_out_of_bounds = ClaimRecord(
        claim_text="Out of bounds line",
        evidence_type=EvidenceType.AST_FUNCTION,
        commit_sha=SNAPSHOT_SHA,
        file_path="pricing.py",
        start_line=100,
        end_line=110,
    )
    result_oob = await validator.validate_claim(sample_snapshot, claim_out_of_bounds)
    assert result_oob.is_valid is False
    assert "exceeds total lines" in result_oob.reason


@pytest.mark.asyncio
async def test_validate_claim_excerpt_mismatch(mock_snapshot_service, sample_snapshot):
    validator = EvidenceValidator(mock_snapshot_service)
    claim = ClaimRecord(
        claim_text="Function calculate_discount definition",
        evidence_type=EvidenceType.AST_FUNCTION,
        commit_sha=SNAPSHOT_SHA,
        file_path="pricing.py",
        start_line=1,
        end_line=2,
        excerpt="completely_different_code()",
    )

    result = await validator.validate_claim(sample_snapshot, claim)
    assert result.is_valid is False
    assert result.status == EvidenceStatus.UNAVAILABLE
    assert "does not match actual content" in result.reason


@pytest.mark.asyncio
async def test_validate_claim_relevance_failure(mock_snapshot_service, sample_snapshot):
    validator = EvidenceValidator(mock_snapshot_service)
    # Line 5 contains: return price * (1 - discount_percent / 100)
    # But claim alleges: "Kubernetes pod autoscaler cluster configuration"
    claim = ClaimRecord(
        claim_text="Kubernetes pod autoscaler cluster configuration",
        evidence_type=EvidenceType.CONFIG_DECLARATION,
        commit_sha=SNAPSHOT_SHA,
        file_path="pricing.py",
        start_line=5,
        end_line=5,
        excerpt="return price * (1 - discount_percent / 100)",
    )

    result = await validator.validate_claim(sample_snapshot, claim)
    assert result.is_valid is False
    assert "does not support the claim" in result.reason


@pytest.mark.asyncio
async def test_validate_inferred_claim(mock_snapshot_service, sample_snapshot):
    validator = EvidenceValidator(mock_snapshot_service)
    claim = ClaimRecord(
        claim_text="Pricing service probably validates negative values",
        evidence_type=EvidenceType.INFERRED,
        commit_sha=SNAPSHOT_SHA,
        file_path="pricing.py",
        status=EvidenceStatus.INFERRED,
    )

    result = await validator.validate_claim(sample_snapshot, claim)
    assert result.is_valid is True
    assert result.status == EvidenceStatus.INFERRED
    assert "reasoned inference" in result.reason


@pytest.mark.asyncio
async def test_validate_bundle(mock_snapshot_service, sample_snapshot):
    validator = EvidenceValidator(mock_snapshot_service)
    claims = [
        ClaimRecord(
            claim_text="pricing.py exists",
            evidence_type=EvidenceType.DIRECTORY_STRUCTURE,
            commit_sha=SNAPSHOT_SHA,
            file_path="pricing.py",
        ),
        ClaimRecord(
            claim_text="missing.py exists",
            evidence_type=EvidenceType.DIRECTORY_STRUCTURE,
            commit_sha=SNAPSHOT_SHA,
            file_path="missing.py",
        ),
    ]

    bundle = await validator.validate_bundle(sample_snapshot, claims)
    assert bundle.snapshot_sha == SNAPSHOT_SHA
    assert bundle.verified_count == 1
    assert bundle.unknown_count == 1
