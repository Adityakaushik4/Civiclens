from fastapi.testclient import TestClient
from app.main import app
from app.escalation.state_machine import escalation_state_machine, escalation_store, IssueStatus
from app.duplicates.store import master_issue_store, MasterIssueRecord
from app.taxonomy import Category
from app.routing.engine import routing_store, RoutingDecisionResult
from app.database.connection import SessionLocal, engine
from app.database import models
import pytest

from app.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    yield
    init_db()
    master_issue_store.clear()
    escalation_store._records.clear()
    routing_store._decisions.clear()

def _create_mock_issue():
    issue_id = "CIVIC-2026-457A"
    
    # 1. Mock Master Issue
    rec = MasterIssueRecord(
        id=issue_id,
        title="Test Issue",
        category=Category.DRAINAGE,
        subcategory="WATERLOGGING",
        severity_score=3,
        latitude=20.0,
        longitude=85.0
    )
    master_issue_store.add(rec)
    
    # 2. Mock Routing Decision
    route = RoutingDecisionResult(
        decision_id="r_1",
        issue_id=issue_id,
        category=Category.DRAINAGE,
        subcategory="WATERLOGGING",
        primary_department="Drainage & Sewerage",
        responsible_unit="Stormwater & Drain Unit",
        escalation_department="Drainage & Sewerage",
        priority_score=75,
        priority_level="HIGH",
        selection_reason="Mock",
        matching_rule_name="Mock",
        rule_logic=["Mock"],
        confidence=1.0,
        routed_at="2026-08-16T10:00:00Z"
    )
    routing_store.save(route)
    routing_store._sync_to_db(route)
    
    # 3. Mock Lifecycle (IN_PROGRESS)
    lifecycle = escalation_state_machine.initialize_lifecycle(route)
    escalation_state_machine.acknowledge_issue(issue_id, "op_1")
    escalation_state_machine.start_work(issue_id, "op_1")
    
    return issue_id

def test_supervisor_queue_bug():
    issue_id = _create_mock_issue()
    
    # Verify IN_PROGRESS state
    lifecycle = escalation_store.get(issue_id)
    assert lifecycle.current_status == IssueStatus.IN_PROGRESS
    
    # Submit Completion
    r_sub = client.post(f"/api/v1/work/{issue_id}/submit-completion", json={"operator_id": "op_1"})
    assert r_sub.status_code == 200
    
    # Verify AWAITING_VERIFICATION state
    lifecycle = escalation_store.get(issue_id)
    assert lifecycle.current_status == IssueStatus.AWAITING_VERIFICATION
    
    # Check Analytics Summary (Dashboard)
    r_dash = client.get("/api/v1/analytics/summary")
    assert r_dash.status_code == 200
    dash_data = r_dash.json()
    assert dash_data["pending_verification_count"] == 1
    
    # Check Supervisor Queue
    r_queue = client.get("/api/v1/supervisor/verification-queue")
    assert r_queue.status_code == 200
    queue_data = r_queue.json()
    
    # Verify the issue is in the queue
    assert len(queue_data) == 1
    assert queue_data[0]["issue_id"] == issue_id
    assert queue_data[0]["status"] == "EVIDENCE UNAVAILABLE"
    assert queue_data[0]["department"] == "Drainage & Sewerage"

def test_non_awaiting_verification_not_in_queue():
    issue_id = _create_mock_issue()
    
    # Leave it as IN_PROGRESS
    r_queue = client.get("/api/v1/supervisor/verification-queue")
    assert r_queue.status_code == 200
    queue_data = r_queue.json()
    
    assert len(queue_data) == 0
