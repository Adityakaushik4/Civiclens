from typing import Optional
from pydantic import BaseModel, Field


class AssignWorkRequest(BaseModel):
    issue_id: str = Field(..., description="Target issue UUID")
    department_id: str = Field(..., description="Department ID")
    unit_id: str = Field(..., description="Responsible Unit ID")
    assigned_operator_id: str = Field(..., description="Field operator ID assigned to ticket")
    assigned_by: str = Field(default="supervisor_1", description="ID of supervisor making assignment")
    notes: Optional[str] = Field(default=None, description="Optional assignment instructions")


class IssueAssignmentRecord(BaseModel):
    assignment_id: str
    issue_id: str
    department_id: str
    unit_id: str
    assigned_operator_id: str
    assigned_by: str
    assigned_at: str
    acknowledged_at: Optional[str] = None
    work_started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = Field(default="ASSIGNED", description="ASSIGNED, REASSIGNED, COMPLETED")
    notes: Optional[str] = None
