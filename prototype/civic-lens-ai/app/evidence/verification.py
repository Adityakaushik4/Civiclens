import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.evidence.schemas import VerificationStatus, VerifyEvidenceRequest, EvidenceVerification
from app.evidence.storage import evidence_store
from app.escalation.state_machine import escalation_state_machine


class VerificationStore:
    """In-memory store for Evidence Verification records."""

    def __init__(self):
        self._verifications: Dict[str, EvidenceVerification] = {}

    def save(self, record: EvidenceVerification) -> None:
        self._verifications[record.verification_id] = record

    def list_by_issue(self, issue_id: str) -> List[EvidenceVerification]:
        return [v for v in self._verifications.values() if v.issue_id == issue_id]

    def clear(self) -> None:
        self._verifications.clear()


verification_store = VerificationStore()


class VerificationEngine:
    """Engine handling evidence verification approvals and rejections."""

    def verify_evidence(self, request: VerifyEvidenceRequest) -> EvidenceVerification:
        ev = evidence_store.get_evidence(request.evidence_id)
        if not ev:
            raise ValueError(f"Resolution evidence '{request.evidence_id}' not found.")

        decision_upper = request.decision.upper().strip()
        if decision_upper not in ["APPROVED", "REJECTED"]:
            raise ValueError("Decision must be either 'APPROVED' or 'REJECTED'.")

        if decision_upper == "REJECTED" and not request.rejection_reason:
            raise ValueError("rejection_reason is required when decision is REJECTED.")

        now_str = datetime.now(timezone.utc).isoformat()
        verification_id = f"ver_{uuid.uuid4().hex[:8]}"

        status_enum = VerificationStatus.VERIFIED if decision_upper == "APPROVED" else VerificationStatus.REJECTED
        evidence_store.update_verification_status(request.evidence_id, status_enum)

        verification_record = EvidenceVerification(
            verification_id=verification_id,
            evidence_id=request.evidence_id,
            issue_id=ev.issue_id,
            verifier_id=request.verifier_id,
            decision=decision_upper,
            rejection_reason=request.rejection_reason,
            verified_at=now_str,
        )

        verification_store.save(verification_record)

        # Trigger State Machine transitions
        if decision_upper == "APPROVED":
            escalation_state_machine.resolve_issue(
                issue_id=ev.issue_id,
                verifier_id=request.verifier_id,
                notes=f"Resolution evidence approved by '{request.verifier_id}'.",
            )
        else:
            escalation_state_machine.reopen_issue(
                issue_id=ev.issue_id,
                actor_id=request.verifier_id,
                reason=f"Evidence Rejected: {request.rejection_reason}",
                notes=f"Supervisor rejected resolution evidence. Issue status set to REOPENED.",
            )

        return verification_record


verification_engine = VerificationEngine()
