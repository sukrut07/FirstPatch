"""Tests for Policy Radar and Claim Guard Services."""

import pytest
from app.services.policy_radar.service import (
    AIPolicyStatus,
    PolicyRadarService,
    WelcomenessRating,
)
from app.services.claim_guard.service import (
    ClaimGuardService,
    IssueReadinessStatus,
)


def test_policy_radar_banned_ai():
    service = PolicyRadarService()
    files = {
        "CONTRIBUTING.md": "# Contributing\nWe do not accept AI-generated pull requests or LLM code.",
    }
    report = service.analyze_repository_policies("org/banned-repo", files)
    assert report.ai_policy == AIPolicyStatus.BANNED
    assert report.welcomeness == WelcomenessRating.RED
    assert report.learn_mode_recommended is True
    assert "Learn Mode" in report.contributor_guidance


def test_policy_radar_disclosure_required():
    service = PolicyRadarService()
    files = {
        ".github/CONTRIBUTING.md": "# Guidelines\nPlease declare any AI assistance used during PR development.",
    }
    report = service.analyze_repository_policies("org/disclosure-repo", files)
    assert report.ai_policy == AIPolicyStatus.DISCLOSURE_REQUIRED
    assert report.learn_mode_recommended is False
    assert len(report.evidence_refs) > 0


def test_policy_radar_unclear_conflicting_policy():
    service = PolicyRadarService()
    files = {
        "CONTRIBUTING.md": "AI generated code is prohibited.",
        "AI.md": "Feel free to use AI tools for documentation and testing.",
    }
    report = service.analyze_repository_policies("org/conflicted-repo", files)
    assert report.ai_policy == AIPolicyStatus.UNCLEAR


def test_policy_radar_small_pr_sample_ratio_is_none():
    service = PolicyRadarService()
    files = {"CONTRIBUTING.md": "# Guidelines\nStandard open-source workflow."}
    # Only 5 PRs (less than the required 10)
    closed_prs = [{"merged": True} for _ in range(5)]
    report = service.analyze_repository_policies("org/sample-repo", files, closed_prs=closed_prs)
    assert report.external_merge_ratio is None
    assert report.sample_sizes["closed_prs"] == 5


def test_policy_radar_sufficient_pr_sample():
    service = PolicyRadarService()
    files = {"CONTRIBUTING.md": "# Guidelines\nStandard open-source workflow."}
    # 10 PRs: 7 merged, 3 unmerged
    closed_prs = [{"merged": True, "first_response_hours": 4.0} for _ in range(7)] + [
        {"merged": False, "first_response_hours": 10.0} for _ in range(3)
    ]
    report = service.analyze_repository_policies("org/active-repo", files, closed_prs=closed_prs)
    assert report.external_merge_ratio == 0.7
    assert report.median_first_response_hours is not None
    assert report.welcomeness == WelcomenessRating.GREEN


def test_claim_guard_available_issue():
    guard = ClaimGuardService()
    issue = {"number": 101, "state": "open", "assignees": [], "assignee": None}
    report = guard.check_issue_readiness("org/repo", issue)
    assert report.status == IssueReadinessStatus.AVAILABLE


def test_claim_guard_assigned_issue():
    guard = ClaimGuardService()
    issue = {"number": 102, "state": "open", "assignees": [{"login": "alice"}]}
    report = guard.check_issue_readiness("org/repo", issue)
    assert report.status == IssueReadinessStatus.ALREADY_ASSIGNED
    assert "alice" in report.summary


def test_claim_guard_open_pr_linking_issue():
    guard = ClaimGuardService()
    issue = {"number": 103, "state": "open", "assignees": []}
    prs = [
        {"number": 201, "title": "Fixes #103 bug in auth", "body": "Resolves issue.", "user": {"login": "bob"}}
    ]
    report = guard.check_issue_readiness("org/repo", issue, open_prs=prs)
    assert report.status == IssueReadinessStatus.HAS_OPEN_PR
    assert "#201" in report.summary


def test_claim_guard_comment_claim():
    guard = ClaimGuardService()
    issue = {"number": 104, "state": "open", "assignees": []}
    comments = [
        {"body": "Hi, I'd like to work on this issue!", "user": {"login": "charlie"}}
    ]
    report = guard.check_issue_readiness("org/repo", issue, comments=comments)
    assert report.status == IssueReadinessStatus.ALREADY_CLAIMED
    assert "charlie" in report.summary


def test_claim_guard_closed_issue():
    guard = ClaimGuardService()
    issue = {"number": 105, "state": "closed", "assignees": []}
    report = guard.check_issue_readiness("org/repo", issue)
    assert report.status == IssueReadinessStatus.CLOSED
