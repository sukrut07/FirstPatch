"""
Tests for Contribution Plan Preparation & Deterministic Plan Validation
"""
from datetime import datetime, timezone
import pytest

from app.schemas.models import (
    GitHubIssue,
    PlanRequest,
)
from app.services.repository_intelligence.contribution_plan import (
    ContributionPlanService,
    PlanValidator,
)
from app.services.repository_intelligence.schemas import (
    PlanStageEnum,
    RepoFileEntry,
    RepositorySnapshot,
    SourceMappingResult,
    TestDiscoveryReport,
)

SNAPSHOT_SHA = "bbbb3333cccc4444dddd5555eeee6666ffff7777"


@pytest.fixture
def sample_snapshot():
    return RepositorySnapshot(
        owner="acme",
        repo="calculator",
        canonical_url="https://github.com/acme/calculator",
        default_branch="main",
        commit_sha=SNAPSHOT_SHA,
        files=[
            RepoFileEntry(path="calculator/engine.py", size=1200),
            RepoFileEntry(path="tests/test_engine.py", size=800),
            RepoFileEntry(path="pytest.ini", size=40),
            RepoFileEntry(path="README.md", size=500),
        ],
    )


@pytest.fixture
def sample_issue():
    return GitHubIssue(
        number=10,
        title="Division by zero raises unhandled ZeroDivisionError",
        state="open",
        body="Calling calculate('10 / 0') crashes instead of returning an error message.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        github_url="https://github.com/acme/calculator/issues/10",
    )


def test_generate_structured_plan_contains_all_stages(sample_snapshot, sample_issue):
    service = ContributionPlanService()
    request = PlanRequest(
        owner="acme",
        repo="calculator",
        issue_number=10,
    )
    mapping = SourceMappingResult(
        issue_number=10,
        relevant_files=["calculator/engine.py"],
        confidence="high",
        has_reliable_mapping=True,
    )
    test_report = TestDiscoveryReport(
        test_frameworks=["pytest"],
        test_directories=["tests"],
        discovered_test_files=["tests/test_engine.py"],
        execution_command_suggestions=["pytest tests/test_engine.py"],
    )

    plan = service.generate_structured_plan(
        request=request,
        snapshot=sample_snapshot,
        issue=sample_issue,
        source_mapping=mapping,
        test_report=test_report,
    )

    assert plan.commit_sha == SNAPSHOT_SHA
    assert plan.issue_number == 10
    assert len(plan.stages) == 6

    stage_types = [s.stage for s in plan.stages]
    assert stage_types == [
        PlanStageEnum.UNDERSTAND,
        PlanStageEnum.EXPLORE,
        PlanStageEnum.PLAN,
        PlanStageEnum.ATTEMPT,
        PlanStageEnum.VERIFY,
        PlanStageEnum.PREPARE_PR,
    ]


def test_plan_validator_success(sample_snapshot, sample_issue):
    service = ContributionPlanService()
    validator = PlanValidator()

    mapping = SourceMappingResult(
        issue_number=10,
        relevant_files=["calculator/engine.py"],
        confidence="high",
        has_reliable_mapping=True,
    )
    test_report = TestDiscoveryReport(
        test_frameworks=["pytest"],
        discovered_test_files=["tests/test_engine.py"],
    )

    plan = service.generate_structured_plan(
        request=PlanRequest(owner="acme", repo="calculator", issue_number=10),
        snapshot=sample_snapshot,
        issue=sample_issue,
        source_mapping=mapping,
        test_report=test_report,
    )

    report = validator.validate_plan(plan, sample_snapshot)
    assert report.is_valid is True
    assert len(report.violations) == 0
    assert len(report.invalid_file_refs) == 0


def test_plan_validator_catches_nonexistent_file_reference(sample_snapshot, sample_issue):
    service = ContributionPlanService()
    validator = PlanValidator()

    # Plan contains a hallucinated/nonexistent file
    mapping = SourceMappingResult(
        issue_number=10,
        relevant_files=["nonexistent/fake_module.py"],
        confidence="low",
    )
    test_report = TestDiscoveryReport()

    plan = service.generate_structured_plan(
        request=PlanRequest(owner="acme", repo="calculator", issue_number=10),
        snapshot=sample_snapshot,
        issue=sample_issue,
        source_mapping=mapping,
        test_report=test_report,
    )

    report = validator.validate_plan(plan, sample_snapshot)
    assert report.is_valid is False
    assert "nonexistent/fake_module.py" in report.invalid_file_refs
    assert any("does not exist in snapshot" in v for v in report.violations)


def test_plan_validator_catches_mismatched_commit_sha(sample_snapshot, sample_issue):
    service = ContributionPlanService()
    validator = PlanValidator()

    mapping = SourceMappingResult(issue_number=10, relevant_files=["calculator/engine.py"])
    test_report = TestDiscoveryReport()

    plan = service.generate_structured_plan(
        request=PlanRequest(owner="acme", repo="calculator", issue_number=10),
        snapshot=sample_snapshot,
        issue=sample_issue,
        source_mapping=mapping,
        test_report=test_report,
    )

    # Different snapshot SHA
    other_snapshot = sample_snapshot.model_copy(update={"commit_sha": "9999999999999999999999999999999999999999"})
    report = validator.validate_plan(plan, other_snapshot)

    assert report.is_valid is False
    assert any("does not match snapshot commit SHA" in v for v in report.violations)
