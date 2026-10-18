"""Policy-Aware Pull-Request Package Generator.

Combines verified evidence, contribution plans, verification execution records,
detected contribution policies, AI disclosures, and tamper-evident receipt links.
Never fabricates diffs, test executions, or unauthorized submissions.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.services.policy_radar.service import AIPolicyStatus, PolicyRadarReport
from app.services.trust.receipt import ReceiptEvent
from app.services.trust.render import RenderedContributionPackage
from app.services.understanding_gate.service import UnderstandingReceipt


class PRPackage(BaseModel):
    repository: str
    snapshot_sha: str
    title: str
    body_markdown: str
    ai_disclosure_text: Optional[str] = None
    policy_compliance_notes: List[str] = Field(default_factory=list)
    is_learn_mode_only: bool = False
    verification_summary: str
    receipt_head_hash: Optional[str] = None


class PRPackageGenerator:
    def generate_package(
        self,
        repository: str,
        snapshot_sha: str,
        issue_number: int,
        issue_title: str,
        policy_report: Optional[PolicyRadarReport],
        rendered_plan: Optional[RenderedContributionPackage],
        verification_record: Optional[Dict[str, Any]],
        understanding_receipt: Optional[UnderstandingReceipt],
        receipt_events: Optional[List[ReceiptEvent]],
        user_diff: Optional[str] = None,
        custom_pr_template: Optional[str] = None,
    ) -> PRPackage:
        is_learn_mode = False
        compliance_notes = []
        disclosure_text = None

        if policy_report:
            if policy_report.ai_policy == AIPolicyStatus.BANNED:
                is_learn_mode = True
                compliance_notes.append(
                    "Repository strictly prohibits AI-generated pull requests. "
                    "Package formatted as an educational Self-Authoring Guide."
                )
            elif policy_report.ai_policy == AIPolicyStatus.DISCLOSURE_REQUIRED:
                disclosure_text = (
                    "### 🤖 AI Assistance Disclosure\n"
                    "In compliance with this repository's contributing guidelines, "
                    "FirstPatch AI was used as a learning and navigation mentor. "
                    "All code changes were authored and verified by the contributor."
                )
                compliance_notes.append("AI disclosure notice included per repository policy.")
            elif policy_report.ai_policy == AIPolicyStatus.NOT_FOUND:
                compliance_notes.append("No explicit AI policy found. Transparent self-authoring recommended.")

        # Verification summary
        if verification_record:
            driver = verification_record.get("driver", "unknown")
            status = verification_record.get("status", "unknown")
            passed = verification_record.get("passed_tests", 0)
            failed = verification_record.get("failed_tests", 0)
            if driver in ("docker_isolated", "isolated_process") and status == "EXECUTED_PASS":
                verify_summary = f"✅ Tests executed in isolated container ({driver}): {passed} passed, {failed} failed."
            elif status == "UNAVAILABLE":
                verify_summary = "⚠️ Isolated verification unavailable (Docker daemon not accessible). Tests not run."
            elif driver == "mock":
                verify_summary = "ℹ️ Mock verification used for local development testing only."
            else:
                verify_summary = f"Verification status: {status} via {driver}."
        else:
            verify_summary = "Verification not executed."

        # Receipt reference
        head_hash = receipt_events[-1].event_hash if receipt_events else None

        # Compose PR package markdown
        lines = []
        if is_learn_mode:
            lines.append(f"# [Self-Authoring Guide] Contribution for Issue #{issue_number}: {issue_title}")
            lines.append("")
            lines.append("> 🛑 **Repository Policy Notice**: This repository prohibits AI-generated PR descriptions or code.")
            lines.append("> Use this document privately to guide your manual implementation.")
            lines.append("")
            lines.append("## Self-Authoring Checklist")
            lines.append("- [ ] Read and understood the issue requirements.")
            lines.append("- [ ] Inspected relevant source files manually.")
            lines.append("- [ ] Wrote original solution without copying raw LLM output.")
            lines.append("- [ ] Added tests covering the change.")
            lines.append("- [ ] Ran test suite locally.")
            lines.append("")
        else:
            lines.append(f"## Fix for Issue #{issue_number}: {issue_title}")
            lines.append("")
            lines.append("### Summary")
            lines.append(f"Resolves #{issue_number} under commit `{snapshot_sha[:8]}`.")
            lines.append("")

        if disclosure_text:
            lines.append(disclosure_text)
            lines.append("")

        lines.append("### Verified Evidence & Implementation Steps")
        if rendered_plan and rendered_plan.verified_steps:
            for s in rendered_plan.verified_steps:
                lines.append(f"- **Step {s.step_id}**: {s.grounded_statement}")
        else:
            lines.append("- Implementation steps manually specified.")
        lines.append("")

        if user_diff:
            lines.append("### Changes Made")
            lines.append("```diff")
            lines.append(user_diff.strip())
            lines.append("```")
            lines.append("")

        lines.append("### Test & Verification Evidence")
        lines.append(f"- {verify_summary}")
        lines.append("")

        if understanding_receipt:
            lines.append("### Contributor Grounding Record")
            lines.append(f"- {understanding_receipt.summary}")
            lines.append("")

        if head_hash:
            lines.append("### Tamper-Evident Flight Receipt")
            lines.append(f"- Flight Chain Head SHA-256: `{head_hash}`")
            lines.append(f"- Total recorded events: {len(receipt_events)}")
            lines.append("")

        if custom_pr_template:
            lines.append("---")
            lines.append("### Repository PR Template Integration")
            lines.append(custom_pr_template)

        body_md = "\n".join(lines)

        return PRPackage(
            repository=repository,
            snapshot_sha=snapshot_sha,
            title=f"Fix: {issue_title}" if not is_learn_mode else f"[Self-Authoring Guide] #{issue_number}: {issue_title}",
            body_markdown=body_md,
            ai_disclosure_text=disclosure_text,
            policy_compliance_notes=compliance_notes,
            is_learn_mode_only=is_learn_mode,
            verification_summary=verify_summary,
            receipt_head_hash=head_hash,
        )
