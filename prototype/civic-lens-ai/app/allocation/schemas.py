from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ProposalScore(BaseModel):
    proposal_id: str
    cycle_id: str
    need_score: float = Field(..., description="Weighted Civic Need Contribution")
    affected_population_score: float = Field(..., description="Weighted Affected Population Contribution")
    safety_impact_score: float = Field(..., description="Weighted Safety Impact Contribution")
    recurrence_score: float = Field(..., description="Weighted Recurrence Contribution")
    vulnerability_score: float = Field(..., description="Weighted Vulnerability Contribution")
    community_support_score: float = Field(..., description="Weighted Community Support Contribution")
    final_score: float = Field(..., description="Explainable Final Score (0 - 100)")
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    calculated_at: str


class BudgetAllocationResult(BaseModel):
    allocation_id: str
    cycle_id: str
    total_budget: float
    allocated_budget: float
    remaining_budget: float
    selected_proposals: List[Dict[str, Any]] = Field(default_factory=list)
    rejected_proposals: List[Dict[str, Any]] = Field(default_factory=list)
    decision_log: List[str] = Field(default_factory=list)
    allocated_at: str
