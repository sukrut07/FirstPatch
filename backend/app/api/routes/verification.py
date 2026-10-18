"""Verification routes."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas import CheckStatus, VerificationCheck, VerificationStatus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["verification"])


@router.get("/{session_id}", response_model=VerificationStatus)
async def get_verification_status(session_id: UUID) -> VerificationStatus:
    """
    Get verification status for a contribution session.

    Phase 0: Returns a status with all checks marked as NOT_RUN.
    Test execution is not yet implemented (requires isolated environment).
    This endpoint is a placeholder for the full verification pipeline.
    """
    # Phase 0: Return honest "not implemented" status
    # rather than fabricating check results
    checks = [
        VerificationCheck(
            name="test_suite",
            description="Run the project's test suite to verify the fix",
            status=CheckStatus.UNAVAILABLE,
            result_detail=(
                "Test execution requires an isolated environment and is not "
                "available in Phase 0. See docs/IMPLEMENTATION_PLAN.md for the roadmap."
            ),
        ),
        VerificationCheck(
            name="lint_check",
            description="Run the project's linter to check code style",
            status=CheckStatus.UNAVAILABLE,
            result_detail="Linting requires the project to be checked out locally.",
        ),
        VerificationCheck(
            name="contribution_checklist",
            description="Basic contribution readiness checklist",
            status=CheckStatus.NOT_RUN,
            result_detail=(
                "Items to check manually: "
                "(1) PR references the issue number. "
                "(2) Branch is up to date with main. "
                "(3) Tests pass locally. "
                "(4) CONTRIBUTING.md guidelines followed."
            ),
        ),
    ]

    return VerificationStatus(
        session_id=session_id,
        owner="unknown",
        repo="unknown",
        checks=checks,
        overall_ready=False,
        blockers=[
            "Test execution is not available in Phase 0. "
            "Run the test suite locally before submitting a PR."
        ],
    )
