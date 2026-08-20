from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CostEstimateLineItem(BaseModel):
    estimate_id: str
    proposal_id: str
    unit_item_name: str
    quantity: float = Field(..., gt=0.0)
    unit_rate: float = Field(..., ge=0.0)
    subtotal: float = Field(..., ge=0.0)
    provenance: str = Field(default="PROVISIONAL", description="PROVISIONAL or AUTHORITATIVE")
    rate_table_ref: Optional[str] = Field(default=None, description="Official PWD rate table reference")
    created_by: str
    created_at: str


class AddCostItemRequest(BaseModel):
    proposal_id: str
    unit_item_name: str
    quantity: float = Field(..., gt=0.0)
    unit_rate: float = Field(..., ge=0.0)
    provenance: str = Field(default="PROVISIONAL", description="PROVISIONAL or AUTHORITATIVE")
    rate_table_ref: Optional[str] = None
    created_by: str = Field(default="engineer_1")


class BudgetCycle(BaseModel):
    cycle_id: str
    jurisdiction_id: str = Field(..., description="Target Ward / Jurisdiction ID")
    cycle_name: str
    total_budget: float = Field(..., ge=0.0)
    min_project_cost: float = Field(default=100000.0)
    max_project_cost: float = Field(default=1000000.0)
    voting_start_time: str
    voting_end_time: str
    max_votes_per_citizen: int = Field(default=3, ge=1)
    status: str = Field(default="ACTIVE_VOTING", description="PLANNED, ACTIVE_SUBMISSION, ACTIVE_VOTING, COMPLETED, ALLOCATED")
    active: bool = True


class BudgetCycleCreateRequest(BaseModel):
    cycle_id: Optional[str] = None
    jurisdiction_id: str = Field(default="WARD_7")
    cycle_name: str
    total_budget: float = Field(default=5000000.0)
    min_project_cost: float = Field(default=100000.0)
    max_project_cost: float = Field(default=1000000.0)
    voting_start_time: Optional[str] = None
    voting_end_time: Optional[str] = None
    max_votes_per_citizen: int = Field(default=3)


class ProposalEligibility(BaseModel):
    eligibility_id: str
    proposal_id: str
    cycle_id: str
    is_eligible: bool
    rule_results: Dict[str, bool] = Field(..., description="Breakdown of all 8 eligibility rules")
    evaluation_notes: str
    evaluated_at: str
