"""Contribution Receipt and Flight Recorder with Tamper-Evident Hash Chain.

Provides deterministic SHA-256 canonical hashing across contribution events,
chain integrity auditing, and verification driver provenance tracking.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

GENESIS_HASH = "0" * 64


class ReceiptEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence_number: int
    step_name: str
    timestamp: str
    repository: str
    snapshot_sha: str
    evidence_ids: List[str] = Field(default_factory=list)
    policy_report_ref: Optional[str] = None
    understanding_receipt_ref: Optional[str] = None
    verification_driver: Optional[str] = None
    verification_status: Optional[str] = None
    result_code: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    event_hash: str


class ReceiptVerificationReport(BaseModel):
    is_valid: bool
    verified_event_count: int
    first_invalid_index: Optional[int] = None
    errors: List[str] = Field(default_factory=list)
    final_hash: Optional[str] = None
    snapshot_sha: Optional[str] = None


class ContributionReceiptRecorder:
    def __init__(self, repository: str, snapshot_sha: str):
        self.repository = repository
        self.snapshot_sha = snapshot_sha
        self.events: List[ReceiptEvent] = []
        self._last_hash = GENESIS_HASH

    @staticmethod
    def compute_canonical_hash(payload: Dict[str, Any], prev_hash: str) -> str:
        data = {
            "payload": payload,
            "prev_hash": prev_hash,
        }
        canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def record_event(
        self,
        step_name: str,
        result_code: str,
        evidence_ids: Optional[List[str]] = None,
        policy_report_ref: Optional[str] = None,
        understanding_receipt_ref: Optional[str] = None,
        verification_driver: Optional[str] = None,
        verification_status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReceiptEvent:
        seq = len(self.events)
        ts = datetime.now(timezone.utc).isoformat()
        ev_ids = evidence_ids or []
        meta = metadata or {}

        payload = {
            "sequence_number": seq,
            "step_name": step_name,
            "timestamp": ts,
            "repository": self.repository,
            "snapshot_sha": self.snapshot_sha,
            "evidence_ids": sorted(ev_ids),
            "policy_report_ref": policy_report_ref,
            "understanding_receipt_ref": understanding_receipt_ref,
            "verification_driver": verification_driver,
            "verification_status": verification_status,
            "result_code": result_code,
            "metadata": meta,
        }

        event_hash = self.compute_canonical_hash(payload, self._last_hash)
        event = ReceiptEvent(
            event_id=str(uuid4()),
            sequence_number=seq,
            step_name=step_name,
            timestamp=ts,
            repository=self.repository,
            snapshot_sha=self.snapshot_sha,
            evidence_ids=ev_ids,
            policy_report_ref=policy_report_ref,
            understanding_receipt_ref=understanding_receipt_ref,
            verification_driver=verification_driver,
            verification_status=verification_status,
            result_code=result_code,
            metadata=meta,
            prev_hash=self._last_hash,
            event_hash=event_hash,
        )

        self.events.append(event)
        self._last_hash = event_hash
        return event

    def export_chain(self) -> List[Dict[str, Any]]:
        return [e.model_dump() for e in self.events]


def verify_receipt_chain(
    events_raw: List[Dict[str, Any]],
    require_provenance: bool = False,
) -> ReceiptVerificationReport:
    """Independently verifies the cryptographic hash chain and sequence integrity."""
    if not events_raw:
        return ReceiptVerificationReport(
            is_valid=True,
            verified_event_count=0,
            first_invalid_index=None,
            errors=["Empty event chain."],
            final_hash=None,
            snapshot_sha=None,
        )

    errors = []
    expected_prev = GENESIS_HASH
    first_invalid = None
    snapshot_sha = None

    for idx, e_dict in enumerate(events_raw):
        try:
            seq = e_dict.get("sequence_number")
            if seq != idx:
                errors.append(f"Event {idx} has invalid sequence number {seq} (expected {idx}).")
                if first_invalid is None:
                    first_invalid = idx

            prev = e_dict.get("prev_hash")
            if prev != expected_prev:
                errors.append(f"Event {idx} prev_hash mismatch: expected {expected_prev}, got {prev}.")
                if first_invalid is None:
                    first_invalid = idx

            sha = e_dict.get("snapshot_sha")
            if snapshot_sha is None:
                snapshot_sha = sha
            elif snapshot_sha != sha:
                errors.append(f"Event {idx} snapshot_sha '{sha}' differs from chain root '{snapshot_sha}'.")
                if first_invalid is None:
                    first_invalid = idx

            # Check verification provenance and untrusted mock driver claims
            v_status = e_dict.get("verification_status")
            v_driver = e_dict.get("verification_driver")
            meta = e_dict.get("metadata") or {}

            if v_status == "EXECUTED_PASS":
                if not v_driver or v_driver in ("mock", "mock-sandbox", "static", "none", "unavailable"):
                    errors.append(
                        f"Event {idx} claims EXECUTED_PASS with untrusted driver '{v_driver}'. Real isolated driver required."
                    )
                    if first_invalid is None:
                        first_invalid = idx
                if (require_provenance or meta.get("requires_provenance")) and not meta.get("run_id"):
                    errors.append(
                        f"Event {idx} claims EXECUTED_PASS but lacks execution provenance (run_id missing from metadata)."
                    )
                    if first_invalid is None:
                        first_invalid = idx

            # Recompute expected hash
            payload = {
                "sequence_number": seq,
                "step_name": e_dict.get("step_name"),
                "timestamp": e_dict.get("timestamp"),
                "repository": e_dict.get("repository"),
                "snapshot_sha": sha,
                "evidence_ids": sorted(e_dict.get("evidence_ids") or []),
                "policy_report_ref": e_dict.get("policy_report_ref"),
                "understanding_receipt_ref": e_dict.get("understanding_receipt_ref"),
                "verification_driver": v_driver,
                "verification_status": v_status,
                "result_code": e_dict.get("result_code"),
                "metadata": meta,
            }
            computed_hash = ContributionReceiptRecorder.compute_canonical_hash(payload, prev)
            recorded_hash = e_dict.get("event_hash")

            if computed_hash != recorded_hash:
                errors.append(f"Event {idx} event_hash tampered: recorded {recorded_hash}, recomputed {computed_hash}.")
                if first_invalid is None:
                    first_invalid = idx

            expected_prev = recorded_hash

        except Exception as ex:
            errors.append(f"Event {idx} parsing/hash error: {ex}")
            if first_invalid is None:
                first_invalid = idx

    is_valid = len(errors) == 0
    return ReceiptVerificationReport(
        is_valid=is_valid,
        verified_event_count=len(events_raw) if is_valid else (first_invalid or 0),
        first_invalid_index=first_invalid,
        errors=errors,
        final_hash=events_raw[-1].get("event_hash") if events_raw else None,
        snapshot_sha=snapshot_sha,
    )
