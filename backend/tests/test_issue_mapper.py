"""
Tests for Issue-to-Code Mapping & Readiness Scoring Preservation
"""
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock

from app.schemas.models import (
    GitHubIssue,
    IssueMatchRequest,
    RepositoryIdentity,
    RepositoryOverview,
)
from app.services.github.client import GitHubService
from app.services.repository_intelligence.issue_mapper import IssueToCodeMapper
from app.services.repository_intelligence.schemas import (
    CodeStructureReport,
    CodeSymbol,
    FileStructure,
    RepoFileEntry,
    RepositorySnapshot,
    SymbolType,
)

SNAPSHOT_SHA = "cccc2222dddd3333eeee4444ffff5555aaaa6666"


@pytest.fixture
def sample_snapshot():
    return RepositorySnapshot(
        owner="example",
        repo="project",
        canonical_url="https://github.com/example/project",
        default_branch="main",
        commit_sha=SNAPSHOT_SHA,
        files=[
            RepoFileEntry(path="src/auth.py", size=1000),
            RepoFileEntry(path="src/utils.py", size=500),
            RepoFileEntry(path="tests/test_auth.py", size=800),
        ],
    )


@pytest.fixture
def sample_code_report():
    auth_struct = FileStructure(
        file_path="src/auth.py",
        language="Python",
        symbols=[
            CodeSymbol(
                snapshot_sha=SNAPSHOT_SHA,
                file_path="src/auth.py",
                name="validate_token",
                symbol_type=SymbolType.FUNCTION,
                start_line=10,
                end_line=15,
                excerpt="def validate_token(token: str) -> bool:\n    return True",
            ),
            CodeSymbol(
                snapshot_sha=SNAPSHOT_SHA,
                file_path="src/auth.py",
                name="AuthService",
                symbol_type=SymbolType.CLASS,
                start_line=20,
                end_line=50,
                excerpt="class AuthService:\n    pass",
            ),
        ],
    )
    return CodeStructureReport(
        snapshot_sha=SNAPSHOT_SHA,
        files={"src/auth.py": auth_struct},
        total_symbols=2,
    )


def test_issue_mapping_with_ast_symbol_match(sample_snapshot, sample_code_report):
    mapper = IssueToCodeMapper(MagicMock(spec=GitHubService))
    issue = GitHubIssue(
        number=42,
        title="Bug in validate_token with expired timestamps",
        state="open",
        body="Calling validate_token with an expired timestamp causes an uncaught error.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        github_url="https://github.com/example/project/issues/42",
    )

    mapping = mapper.map_issue_to_source(issue, sample_snapshot, sample_code_report)

    assert mapping.has_reliable_mapping is True
    assert "src/auth.py" in mapping.relevant_files
    assert any(sym.name == "validate_token" for sym in mapping.matched_symbols)
    assert mapping.confidence in {"high", "medium"}


def test_issue_mapping_with_explicit_path_mention(sample_snapshot):
    mapper = IssueToCodeMapper(MagicMock(spec=GitHubService))
    issue = GitHubIssue(
        number=43,
        title="Formatting error",
        state="open",
        body="Please update src/utils.py to handle trailing commas.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        github_url="https://github.com/example/project/issues/43",
    )

    mapping = mapper.map_issue_to_source(issue, sample_snapshot)

    assert mapping.has_reliable_mapping is True
    assert "src/utils.py" in mapping.relevant_files
    assert mapping.confidence == "high"


def test_issue_mapping_with_no_reliable_connection(sample_snapshot):
    mapper = IssueToCodeMapper(MagicMock(spec=GitHubService))
    issue = GitHubIssue(
        number=99,
        title="Website color scheme looks dull",
        state="open",
        body="The background gradient could be slightly brighter.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        github_url="https://github.com/example/project/issues/99",
    )

    mapping = mapper.map_issue_to_source(issue, sample_snapshot)

    assert mapping.has_reliable_mapping is False
    assert mapping.confidence == "none"
    assert len(mapping.missing_evidence_notes) > 0
    assert "Could not establish a reliable connection" in mapping.missing_evidence_notes[0]


def test_rank_issues_preserves_7_criteria_and_excludes_pull_requests(sample_snapshot):
    mapper = IssueToCodeMapper(MagicMock(spec=GitHubService))
    overview = RepositoryOverview(
        identity=RepositoryIdentity(owner="example", repo="project"),
        full_name="example/project",
        github_url="https://github.com/example/project",
        primary_language="Python",
    )
    request = IssueMatchRequest(
        owner="example",
        repo="project",
        preferred_languages=["Python"],
    )
    raw_items = [
        # Regular issue
        {
            "number": 1,
            "title": "Good first issue for beginners",
            "state": "open",
            "body": "Steps to reproduce: run tests. Expected: pass.",
            "labels": [{"name": "good first issue"}],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        # Pull request (must be excluded)
        {
            "number": 2,
            "title": "Fix token issue",
            "state": "open",
            "pull_request": {"url": "https://api.github.com/repos/example/project/pulls/2"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    response = mapper.rank_issues_with_evidence(
        request=request,
        snapshot=sample_snapshot,
        repo_overview=overview,
        raw_issues=raw_items,
    )

    # Pull request should be excluded
    assert len(response.matched_issues) == 1
    matched = response.matched_issues[0]
    assert matched.issue.number == 1

    # Preserved 7-criteria check
    criterion_names = {c.name for c in matched.criteria}
    expected_criteria = {
        "issue_is_open",
        "has_clear_description",
        "not_stale",
        "has_reproduction_or_steps",
        "has_good_first_issue_label",
        "language_match",
        "has_tests_nearby",
    }
    assert criterion_names == expected_criteria
