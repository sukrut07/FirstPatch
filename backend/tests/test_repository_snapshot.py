"""
Tests for Repository Snapshot & File Inventory Service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.github.client import (
    GitHubService,
)
from app.services.repository_intelligence.exceptions import SnapshotIncompleteError
from app.services.repository_intelligence.schemas import FileType, RepositorySnapshot
from app.services.repository_intelligence.snapshot import (
    RepositorySnapshotService,
    classify_file,
)


@pytest.fixture
def mock_github():
    github = MagicMock(spec=GitHubService)
    github.get_repository_metadata = AsyncMock(return_value={
        "full_name": "owner/repo",
        "default_branch": "main",
        "stargazers_count": 120,
        "language": "Python",
    })
    github.get_default_branch_sha = AsyncMock(return_value="a1b2c3d4e5f678901234567890abcdef12345678")
    github.get_languages = AsyncMock(return_value={"Python": 8000, "Shell": 2000})
    github.get_tree = AsyncMock(return_value=[
        {"path": "app/main.py", "type": "blob", "size": 1500},
        {"path": "tests/test_main.py", "type": "blob", "size": 2200},
        {"path": "requirements.txt", "type": "blob", "size": 340},
        {"path": "pytest.ini", "type": "blob", "size": 50},
        {"path": "README.md", "type": "blob", "size": 1200},
        {"path": "app", "type": "tree"},  # non-blob item
    ])
    github.get_file_content = AsyncMock(return_value="print('hello')\n")
    return github


@pytest.mark.asyncio
async def test_snapshot_creation_pins_commit_sha(mock_github):
    service = RepositorySnapshotService(mock_github)
    snapshot = await service.create_snapshot("https://github.com/owner/repo")

    assert isinstance(snapshot, RepositorySnapshot)
    assert snapshot.owner == "owner"
    assert snapshot.repo == "repo"
    assert snapshot.commit_sha == "a1b2c3d4e5f678901234567890abcdef12345678"
    assert snapshot.default_branch == "main"
    assert snapshot.is_partial is False
    assert len(snapshot.files) == 5  # blob items only


@pytest.mark.asyncio
async def test_snapshot_preserves_explicit_commit_sha(mock_github):
    service = RepositorySnapshotService(mock_github)
    explicit_sha = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    snapshot = await service.create_snapshot("https://github.com/owner/repo", commit_sha=explicit_sha)

    assert snapshot.commit_sha == explicit_sha
    # Should not call get_default_branch_sha when SHA is explicitly passed
    mock_github.get_default_branch_sha.assert_not_called()


@pytest.mark.asyncio
async def test_snapshot_fails_honestly_when_sha_cannot_be_resolved(mock_github):
    mock_github.get_default_branch_sha = AsyncMock(return_value=None)
    service = RepositorySnapshotService(mock_github)

    with pytest.raises(SnapshotIncompleteError) as exc_info:
        await service.create_snapshot("https://github.com/owner/repo")

    assert "Unable to determine commit SHA" in str(exc_info.value)


@pytest.mark.asyncio
async def test_snapshot_detects_manifests_and_test_configs(mock_github):
    service = RepositorySnapshotService(mock_github)
    snapshot = await service.create_snapshot("https://github.com/owner/repo")

    assert "requirements.txt" in snapshot.dependency_manifests
    assert "pytest.ini" in snapshot.test_configs
    assert snapshot.has_file("app/main.py")
    assert not snapshot.has_file("nonexistent.py")


@pytest.mark.asyncio
async def test_snapshot_handles_partial_tree_gracefully(mock_github):
    # If recursive tree returns empty, fallback to non-recursive
    mock_github.get_tree = AsyncMock(side_effect=[
        [],  # recursive fails
        [{"path": "README.md", "type": "blob", "size": 100}],  # non-recursive returns top-level
    ])
    service = RepositorySnapshotService(mock_github)
    snapshot = await service.create_snapshot("https://github.com/owner/repo")

    assert snapshot.is_partial is True
    assert any("truncated" in w.lower() for w in snapshot.warnings)
    assert len(snapshot.files) == 1


@pytest.mark.asyncio
async def test_file_content_caching(mock_github):
    service = RepositorySnapshotService(mock_github)
    snapshot = await service.create_snapshot("https://github.com/owner/repo")

    content1 = await service.get_file_content(snapshot, "app/main.py")
    content2 = await service.get_file_content(snapshot, "app/main.py")

    assert content1 == "print('hello')\n"
    assert content2 == "print('hello')\n"
    # Content should be fetched from GitHub only once due to caching
    assert mock_github.get_file_content.call_count == 1


def test_classify_file():
    assert classify_file("requirements.txt") == FileType.MANIFEST
    assert classify_file("package.json") == FileType.MANIFEST
    assert classify_file("pytest.ini") == FileType.CONFIG
    assert classify_file("jest.config.js") == FileType.CONFIG
    assert classify_file("README.md") == FileType.DOC
    assert classify_file("tests/test_foo.py") == FileType.TEST
    assert classify_file("src/foo.test.ts") == FileType.TEST
    assert classify_file("app/main.py") == FileType.SOURCE
    assert classify_file("logo.png") == FileType.ASSET
    assert classify_file("data.bin") == FileType.OTHER
