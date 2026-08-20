import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.assignment.schemas import AssignWorkRequest, IssueAssignmentRecord
from app.escalation.state_machine import escalation_state_machine, escalation_store


class AssignmentStore:
    """In-memory store for Issue Assignment records."""

    def __init__(self):
        self._assignments: Dict[str, IssueAssignmentRecord] = {}

    def save(self, record: IssueAssignmentRecord) -> None:
        self._assignments[record.issue_id] = record

    def get(self, issue_id: str) -> Optional[IssueAssignmentRecord]:
        return self._assignments.get(issue_id)

    def clear(self) -> None:
        self._assignments.clear()


assignment_store = AssignmentStore()


class AssignmentEngine:
    """Engine managing work assignment from Department -> Unit -> Operator."""

    def assign_work(self, request: AssignWorkRequest) -> IssueAssignmentRecord:
        now_str = datetime.now(timezone.utc).isoformat()
        assignment_id = f"assign_{uuid.uuid4().hex[:8]}"

        existing = assignment_store.get(request.issue_id)
        status_str = "REASSIGNED" if existing else "ASSIGNED"

        record = IssueAssignmentRecord(
            assignment_id=assignment_id,
            issue_id=request.issue_id,
            department_id=request.department_id,
            unit_id=request.unit_id,
            assigned_operator_id=request.assigned_operator_id,
            assigned_by=request.assigned_by,
            assigned_at=now_str,
            status=status_str,
            notes=request.notes,
        )

        assignment_store.save(record)

        # Update lifecycle record if exists
        lifecycle = escalation_store.get(request.issue_id)
        if lifecycle:
            lifecycle.assigned_operator_id = request.assigned_operator_id
            lifecycle.current_department = request.department_id
            lifecycle.responsible_unit = request.unit_id
            escalation_store.save(lifecycle)

        return record


assignment_engine = AssignmentEngine()
