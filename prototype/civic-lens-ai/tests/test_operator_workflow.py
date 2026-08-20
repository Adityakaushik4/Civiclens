import pytest
import json
from datetime import datetime, timezone
from app.database.connection import init_db
from app.escalation.state_machine import escalation_state_machine, escalation_store, IssueLifecycleRecord, IssueStatus
from app.routing.engine import RoutingDecisionResult, PriorityLevel
from app.taxonomy import Category

def setup_function():
    init_db()
    escalation_store.clear()

def create_mock_issue(issue_id="civic-test-123"):
    decision = RoutingDecisionResult(
        decision_id="dec_123",
        issue_id=issue_id,
        category=Category.DRAINAGE.value,
        subcategory="WATERLOGGING",
        priority_score=90,
        priority_level=PriorityLevel.HIGH,
        primary_department="Drainage & Sewerage",
        responsible_unit="Stormwater & Drain Unit",
        escalation_department="DPW",
        selection_reason="Test reason",
        routed_at=datetime.now(timezone.utc).isoformat()
    )
    return escalation_state_machine.initialize_lifecycle(decision)

def test_operator_workflow_success():
    issue = create_mock_issue("test-workflow-1")
    assert issue.current_status == IssueStatus.ROUTED

    # Acknowledge
    ack_issue = escalation_state_machine.acknowledge_issue("test-workflow-1", "operator_1", "notes")
    assert ack_issue.current_status == IssueStatus.ACKNOWLEDGED
    assert ack_issue.acknowledged_by == "operator_1"

    # Start Work
    start_issue = escalation_state_machine.start_work("test-workflow-1", "operator_1", "notes")
    assert start_issue.current_status == IssueStatus.IN_PROGRESS
    assert start_issue.assigned_operator_id == "operator_1"

    # Submit Completion
    comp_issue = escalation_state_machine.submit_completion("test-workflow-1", "operator_1", "notes")
    assert comp_issue.current_status == IssueStatus.AWAITING_VERIFICATION

def test_operator_workflow_invalid_transition():
    issue = create_mock_issue("test-workflow-2")
    assert issue.current_status == IssueStatus.ROUTED

    # Attempt to jump straight to IN_PROGRESS from ROUTED
    with pytest.raises(ValueError, match="Invalid transition"):
        escalation_state_machine.start_work("test-workflow-2", "operator_1", "notes")

def test_operator_workflow_persistence():
    issue = create_mock_issue("test-workflow-persistence")
    escalation_state_machine.acknowledge_issue("test-workflow-persistence", "operator_1", "notes")
    
    # Reload from DB by destroying cache
    escalation_store._records.clear()
    
    reloaded_issue = escalation_store.get("test-workflow-persistence")
    assert reloaded_issue is not None
    assert reloaded_issue.current_status == IssueStatus.ACKNOWLEDGED
    
    # Do start work
    escalation_state_machine.start_work("test-workflow-persistence", "operator_1", "notes")
    
    # Reload from DB again
    escalation_store._records.clear()
    reloaded_issue_2 = escalation_store.get("test-workflow-persistence")
    assert reloaded_issue_2.current_status == IssueStatus.IN_PROGRESS
