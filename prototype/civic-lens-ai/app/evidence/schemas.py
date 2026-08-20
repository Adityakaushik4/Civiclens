from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    BEFORE_IMAGE = "BEFORE_IMAGE"
    AFTER_IMAGE = "AFTER_IMAGE"
    VOICE_NOTE = "VOICE_NOTE"
    WORK_LOG = "WORK_LOG"
    COMPLETION_CERTIFICATE = "COMPLETION_CERTIFICATE"


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ResolutionEvidence(BaseModel):
    evidence_id: str
    issue_id: str
    evidence_type: EvidenceType
    file_key: str
    file_name: str
    mime_type: str
    file_size_bytes: int
    uploaded_by: str
    uploaded_at: str
    verification_status: VerificationStatus = VerificationStatus.PENDING
    public_token: str


class VerifyEvidenceRequest(BaseModel):
    evidence_id: str = Field(..., description="Target evidence UUID to verify")
    verifier_id: str = Field(default="verifier_1", description="ID of municipal verifier / supervisor")
    decision: str = Field(..., description="APPROVED or REJECTED")
    rejection_reason: Optional[str] = Field(default=None, description="Required notes if decision is REJECTED")


class EvidenceVerification(BaseModel):
    verification_id: str
    evidence_id: str
    issue_id: str
    verifier_id: str
    decision: str
    rejection_reason: Optional[str] = None
    verified_at: str
