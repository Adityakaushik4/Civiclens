from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ProposalStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    VOTING = "VOTING"
    SELECTED = "SELECTED"
    FUNDED = "FUNDED"
    IMPLEMENTED = "IMPLEMENTED"
    REJECTED = "REJECTED"


class CitizenProposal(BaseModel):
    proposal_id: str
    opportunity_id: Optional[str] = Field(default=None, description="Optional linked project opportunity")
    jurisdiction_id: str = Field(default="WARD_7", description="Jurisdiction / Ward ID")
    title: str
    description: str
    proposer_id_hash: str = Field(..., description="Masked voter/proposer identity hash")
    category: str
    requested_budget: float = Field(..., ge=0.0, description="Initial requested cost")
    cost_status: str = Field(default="ESTIMATED", description="ESTIMATED, PROVISIONAL, AUTHORITATIVE")
    linked_master_issue_ids: List[str] = Field(default_factory=list)
    status: ProposalStatus = ProposalStatus.DRAFT
    ai_generated_draft: bool = False
    created_at: str
    updated_at: str


class ProposalCreateRequest(BaseModel):
    opportunity_id: Optional[str] = None
    jurisdiction_id: str = Field(default="WARD_7")
    title: str
    description: str
    proposer_id: str = Field(default="citizen_1", description="Raw proposer ID, masked on storage")
    category: str
    requested_budget: float
    linked_master_issue_ids: List[str] = Field(default_factory=list)
    ai_generated_draft: bool = False


class ProposalUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requested_budget: Optional[float] = None
    status: Optional[ProposalStatus] = None
    linked_master_issue_ids: Optional[List[str]] = None


class ProposalEvidencePanel(BaseModel):
    proposal_id: str
    linked_master_issues: List[Dict[str, Any]] = Field(default_factory=list)
    total_citizen_reports: int = 0
    safety_risk_count: int = 0
    historical_reopening_avg: float = 0.0
    rag_citations: List[Dict[str, Any]] = Field(default_factory=list)
