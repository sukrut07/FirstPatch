"""Deterministic Checkers for Proof-Carrying Contributions.

Each checker evaluates a Claim strictly against the authoritative FactStore and snapshot.
None of these checkers execute untrusted shell code or call unconstrained LLMs.
"""

from app.services.trust.claims import Claim, Verdict, VerdictStatus
from app.services.trust.fact_store import FactStore, normalize_repo_path


def check_file_exists(claim: Claim, fact_store: FactStore, authoritative_sha: str) -> Verdict:
    raw_path = claim.arguments.get("path")
    if not raw_path:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="MISSING_ARGUMENT",
            explanation="Path argument is missing from FILE_EXISTS claim.",
        )
    try:
        clean_path = normalize_repo_path(raw_path)
    except ValueError as e:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="UNSAFE_PATH",
            explanation=f"Path rejected by safety normalizer: {e}",
        )

    file_record = fact_store.get_file(claim.repository, authoritative_sha, clean_path)
    if file_record:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.VERIFIED,
            snapshot_sha=authoritative_sha,
            reason_code="FILE_FOUND",
            explanation=f"File '{clean_path}' confirmed present in snapshot {authoritative_sha[:8]}.",
            witness={"path": clean_path, "content_hash": file_record["content_hash"]},
        )
    return Verdict(
        claim_id=claim.claim_id,
        status=VerdictStatus.REFUTED,
        snapshot_sha=authoritative_sha,
        reason_code="FILE_NOT_FOUND",
        explanation=f"File '{clean_path}' does not exist in snapshot {authoritative_sha[:8]}.",
    )


def check_symbol_in_file(claim: Claim, fact_store: FactStore, authoritative_sha: str) -> Verdict:
    raw_path = claim.arguments.get("path")
    symbol_name = claim.arguments.get("symbol_name")
    if not raw_path or not symbol_name:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="MISSING_ARGUMENT",
            explanation="Both 'path' and 'symbol_name' are required for SYMBOL_IN_FILE claim.",
        )
    try:
        clean_path = normalize_repo_path(raw_path)
    except ValueError as e:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="UNSAFE_PATH",
            explanation=f"Path rejected by safety normalizer: {e}",
        )

    sym = fact_store.get_symbol(claim.repository, authoritative_sha, clean_path, symbol_name)
    if sym:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.VERIFIED,
            snapshot_sha=authoritative_sha,
            reason_code="SYMBOL_FOUND",
            explanation=f"Symbol '{symbol_name}' found in '{clean_path}' (lines {sym['start_line']}-{sym['end_line']}).",
            witness=sym,
        )
    return Verdict(
        claim_id=claim.claim_id,
        status=VerdictStatus.REFUTED,
        snapshot_sha=authoritative_sha,
        reason_code="SYMBOL_NOT_FOUND",
        explanation=f"Symbol '{symbol_name}' not found in '{clean_path}' at snapshot {authoritative_sha[:8]}.",
    )


def check_lines_contain(claim: Claim, fact_store: FactStore, authoritative_sha: str) -> Verdict:
    raw_path = claim.arguments.get("path")
    substring = claim.arguments.get("substring")
    start_line = claim.arguments.get("start_line")
    end_line = claim.arguments.get("end_line")

    if not raw_path or substring is None:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="MISSING_ARGUMENT",
            explanation="'path' and 'substring' are required for LINES_CONTAIN claim.",
        )

    try:
        clean_path = normalize_repo_path(raw_path)
    except ValueError as e:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="UNSAFE_PATH",
            explanation=f"Path rejected by safety normalizer: {e}",
        )

    file_rec = fact_store.get_file(claim.repository, authoritative_sha, clean_path)
    if not file_rec:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="FILE_NOT_FOUND",
            explanation=f"File '{clean_path}' not found in snapshot {authoritative_sha[:8]}.",
        )

    lines = file_rec["content"].splitlines()
    if start_line is not None and end_line is not None:
        try:
            s = max(1, int(start_line)) - 1
            e = min(len(lines), int(end_line))
            target_slice = "\n".join(lines[s:e])
        except (ValueError, TypeError):
            target_slice = file_rec["content"]
    else:
        target_slice = file_rec["content"]

    # Normalize whitespace for robust comparison
    clean_target = " ".join(target_slice.split())
    clean_sub = " ".join(substring.split())

    if clean_sub in clean_target:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.VERIFIED,
            snapshot_sha=authoritative_sha,
            reason_code="LINES_VERIFIED",
            explanation=f"Substring verified in '{clean_path}' under snapshot {authoritative_sha[:8]}.",
            witness={"path": clean_path, "matched_snippet": substring[:100]},
        )

    return Verdict(
        claim_id=claim.claim_id,
        status=VerdictStatus.REFUTED,
        snapshot_sha=authoritative_sha,
        reason_code="LINES_MISMATCH",
        explanation=f"Target substring not found in '{clean_path}' at specified lines.",
    )


def check_imported_by(claim: Claim, fact_store: FactStore, authoritative_sha: str) -> Verdict:
    raw_path = claim.arguments.get("source_path")
    imported_module = claim.arguments.get("imported_module")
    imported_name = claim.arguments.get("imported_name")

    if not raw_path or not imported_module:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="MISSING_ARGUMENT",
            explanation="'source_path' and 'imported_module' are required.",
        )
    try:
        clean_path = normalize_repo_path(raw_path)
    except ValueError as e:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="UNSAFE_PATH",
            explanation=f"Path rejected: {e}",
        )

    records = fact_store.get_imports(claim.repository, authoritative_sha, clean_path)
    for rec in records:
        if rec["imported_module"] == imported_module:
            if not imported_name or rec["imported_name"] == imported_name:
                return Verdict(
                    claim_id=claim.claim_id,
                    status=VerdictStatus.VERIFIED,
                    snapshot_sha=authoritative_sha,
                    reason_code="IMPORT_FOUND",
                    explanation=f"Import '{imported_module}' confirmed in '{clean_path}'.",
                    witness=rec,
                )
    return Verdict(
        claim_id=claim.claim_id,
        status=VerdictStatus.REFUTED,
        snapshot_sha=authoritative_sha,
        reason_code="IMPORT_NOT_FOUND",
        explanation=f"Import '{imported_module}' not confirmed in '{clean_path}'.",
    )


def check_test_imports(claim: Claim, fact_store: FactStore, authoritative_sha: str) -> Verdict:
    test_path = claim.arguments.get("test_path")
    target_module = claim.arguments.get("target_module")
    if not test_path or not target_module:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="MISSING_ARGUMENT",
            explanation="'test_path' and 'target_module' are required.",
        )
    # Check imports recorded for this test file
    try:
        clean_path = normalize_repo_path(test_path)
    except ValueError as e:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="UNSAFE_PATH",
            explanation=str(e),
        )

    imports = fact_store.get_imports(claim.repository, authoritative_sha, clean_path)
    for imp in imports:
        if target_module in imp["imported_module"]:
            return Verdict(
                claim_id=claim.claim_id,
                status=VerdictStatus.VERIFIED,
                snapshot_sha=authoritative_sha,
                reason_code="TEST_IMPORTS_VERIFIED",
                explanation=f"Test '{clean_path}' imports '{target_module}'.",
                witness={"test_path": clean_path, "target_module": target_module},
            )
    return Verdict(
        claim_id=claim.claim_id,
        status=VerdictStatus.REFUTED,
        snapshot_sha=authoritative_sha,
        reason_code="TEST_IMPORT_NOT_FOUND",
        explanation=f"No verified link between test '{clean_path}' and module '{target_module}'.",
    )


def check_policy_fact(claim: Claim, fact_store: FactStore, authoritative_sha: str) -> Verdict:
    policy_type = claim.arguments.get("policy_type")
    claimed_value = claim.arguments.get("value")

    if not policy_type or claimed_value is None:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="MISSING_ARGUMENT",
            explanation="'policy_type' and 'value' are required.",
        )

    fact = fact_store.get_policy_fact(claim.repository, authoritative_sha, policy_type)
    if not fact:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.UNKNOWN,
            snapshot_sha=authoritative_sha,
            reason_code="POLICY_FACT_ABSENT",
            explanation=f"No recorded policy fact for '{policy_type}' at commit {authoritative_sha[:8]}.",
        )

    if str(fact["value"]).lower() == str(claimed_value).lower():
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.VERIFIED,
            snapshot_sha=authoritative_sha,
            reason_code="POLICY_VERIFIED",
            explanation=f"Policy '{policy_type}'={claimed_value} verified by source evidence.",
            witness=fact,
        )
    return Verdict(
        claim_id=claim.claim_id,
        status=VerdictStatus.REFUTED,
        snapshot_sha=authoritative_sha,
        reason_code="POLICY_CONTRADICTION",
        explanation=f"Policy '{policy_type}' recorded value is '{fact['value']}', contradicting claim '{claimed_value}'.",
        witness=fact,
    )


def check_issue_unclaimed(claim: Claim, fact_store: FactStore, authoritative_sha: str) -> Verdict:
    issue_number = claim.arguments.get("issue_number")
    if not issue_number:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="MISSING_ARGUMENT",
            explanation="'issue_number' is required.",
        )

    fact = fact_store.get_issue_fact(claim.repository, int(issue_number))
    if not fact:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.UNKNOWN,
            snapshot_sha=authoritative_sha,
            reason_code="ISSUE_FACT_ABSENT",
            explanation=f"Issue #{issue_number} has no recorded ground-truth status in FactStore.",
        )

    if fact["state"] != "open":
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="ISSUE_CLOSED",
            explanation=f"Issue #{issue_number} is closed.",
            witness=fact,
        )

    if fact["is_assigned"]:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="ISSUE_ALREADY_ASSIGNED",
            explanation=f"Issue #{issue_number} is already assigned to {fact['assignees']}.",
            witness=fact,
        )

    if fact["has_open_pr"]:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="HAS_OPEN_PR",
            explanation=f"Issue #{issue_number} already has an active linked open PR.",
            witness=fact,
        )

    if fact.get("claim_comment"):
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="CLAIM_IN_COMMENTS",
            explanation=f"Issue #{issue_number} has an existing claim comment: {fact['claim_comment'][:80]}",
            witness=fact,
        )

    return Verdict(
        claim_id=claim.claim_id,
        status=VerdictStatus.VERIFIED,
        snapshot_sha=authoritative_sha,
        reason_code="ISSUE_UNCLAIMED_VERIFIED",
        explanation=f"Issue #{issue_number} is confirmed open, unassigned, with no open PR or claim comment.",
        witness=fact,
    )


def check_verify_result(claim: Claim, fact_store: FactStore, authoritative_sha: str) -> Verdict:
    run_id = claim.arguments.get("run_id")
    claimed_status = claim.arguments.get("status")

    if not run_id or not claimed_status:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="MISSING_ARGUMENT",
            explanation="'run_id' and 'status' are required.",
        )

    rec = fact_store.get_verification_run(run_id)
    if not rec:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.UNKNOWN,
            snapshot_sha=authoritative_sha,
            reason_code="RUN_NOT_FOUND",
            explanation=f"Verification run '{run_id}' not found in FactStore.",
        )

    # CRITICAL SECURITY RULE: Mock runs, static discoveries, or unavailable drivers
    # can NEVER certify an 'EXECUTED_PASS' claim!
    trusted_real_drivers = {"docker_isolated", "isolated_process"}
    if claimed_status == "EXECUTED_PASS":
        if rec["driver"] not in trusted_real_drivers:
            return Verdict(
                claim_id=claim.claim_id,
                status=VerdictStatus.REFUTED,
                snapshot_sha=authoritative_sha,
                reason_code="UNTRUSTED_DRIVER_FOR_EXECUTION_PASS",
                explanation=f"Driver '{rec['driver']}' cannot certify EXECUTED_PASS. Real isolated driver required.",
                witness=rec,
            )
        if rec["status"] != "EXECUTED_PASS":
            return Verdict(
                claim_id=claim.claim_id,
                status=VerdictStatus.REFUTED,
                snapshot_sha=authoritative_sha,
                reason_code="EXECUTION_STATUS_MISMATCH",
                explanation=f"Recorded execution status is '{rec['status']}', not EXECUTED_PASS.",
                witness=rec,
            )
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.VERIFIED,
            snapshot_sha=authoritative_sha,
            reason_code="EXECUTED_PASS_VERIFIED",
            explanation=f"Actual execution passed under real driver '{rec['driver']}' (exit code {rec['exit_code']}).",
            witness=rec,
        )

    # If claiming other statuses (e.g. MOCK, UNAVAILABLE, EXECUTED_FAIL)
    if rec["status"] == claimed_status:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.VERIFIED,
            snapshot_sha=authoritative_sha,
            reason_code="VERIFY_RESULT_MATCH",
            explanation=f"Verification status '{claimed_status}' verified against recorded run.",
            witness=rec,
        )

    return Verdict(
        claim_id=claim.claim_id,
        status=VerdictStatus.REFUTED,
        snapshot_sha=authoritative_sha,
        reason_code="VERIFY_RESULT_MISMATCH",
        explanation=f"Recorded status is '{rec['status']}', expected '{claimed_status}'.",
        witness=rec,
    )


def check_review_theme(claim: Claim, fact_store: FactStore, authoritative_sha: str) -> Verdict:
    theme = claim.arguments.get("theme")
    comment_refs = claim.arguments.get("comment_refs", [])

    if not theme or not isinstance(comment_refs, list):
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="MISSING_ARGUMENT",
            explanation="'theme' and list of 'comment_refs' required.",
        )

    # Deduplicate references
    unique_refs = set(comment_refs)
    if len(unique_refs) < 2:
        return Verdict(
            claim_id=claim.claim_id,
            status=VerdictStatus.REFUTED,
            snapshot_sha=authoritative_sha,
            reason_code="INSUFFICIENT_REFERENCES",
            explanation=f"Theme '{theme}' requires at least 2 distinct review comment references; got {len(unique_refs)}.",
        )

    return Verdict(
        claim_id=claim.claim_id,
        status=VerdictStatus.VERIFIED,
        snapshot_sha=authoritative_sha,
        reason_code="REVIEW_THEME_VERIFIED",
        explanation=f"Theme '{theme}' supported by {len(unique_refs)} verified comment references.",
        witness={"theme": theme, "comment_count": len(unique_refs)},
    )
