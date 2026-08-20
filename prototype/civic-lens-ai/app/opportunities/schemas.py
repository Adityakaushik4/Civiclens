from typing import List, Optional
from pydantic import BaseModel, Field


class CivicProjectOpportunity(BaseModel):
    opportunity_id: str
    jurisdiction_id: Optional[str] = Field(default=None, description="Target jurisdiction ID")
    title: str
    category: str
    department: Optional[str] = Field(default=None, description="Assigned municipal department")
    suggested_budget: Optional[float] = Field(default=None, description="Estimated project budget")
    hotspot_id: Optional[str] = Field(default=None, description="Linked spatial hotspot ID")
    linked_master_issue_ids: List[str] = Field(default_factory=list)
    total_citizen_reports: int
    estimated_priority_avg: float
    status: str = Field(default="DETECTED", description="DETECTED, PROPOSED, ARCHIVED")
    created_at: str


class AIDraftProposalRequest(BaseModel):
    opportunity_id: str = Field(..., description="Target opportunity UUID to generate draft from")
    proposer_id: str = Field(default="citizen_1", description="ID of citizen creating proposal")


class AIDraftProposalResponse(BaseModel):
    opportunity_id: str
    suggested_title: str
    suggested_description: str
    linked_master_issue_ids: List[str]
    total_citizen_reports: int
    ai_disclaimer: str = "AI-assisted draft. Statistics and evidence cited from Master Issues. Financial costs and government approval are NOT calculated by AI."
    ai_generated_draft: bool = True
