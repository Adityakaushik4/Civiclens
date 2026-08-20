from fastapi.testclient import TestClient
from app.main import app
from app.escalation.state_machine import escalation_state_machine, escalation_store, IssueStatus
from app.duplicates.store import master_issue_store, MasterIssueRecord
from app.taxonomy import Category
from app.routing.engine import routing_store, RoutingDecisionResult
from app.evidence.storage import evidence_store
from app.evidence.schemas import EvidenceType
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
    evidence_store.clear()

def test_evidence_integrity_bug():
    issue_id = "CIVIC-2026-457A"
    
    # 1. Mock Master Issue (WATERLOGGING)
    rec = MasterIssueRecord(
        id=issue_id,
        title="Waterlogging Issue",
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
    
    # 3. Mock Lifecycle (IN_PROGRESS -> AWAITING_VERIFICATION)
    escalation_state_machine.initialize_lifecycle(route)
    escalation_state_machine.acknowledge_issue(issue_id, "op_1")
    escalation_state_machine.start_work(issue_id, "op_1")
    
    # 4. Upload Evidence (Mocking operator action)
    with open("test_img.jpg", "wb") as f:
        f.write(b"fake image data")
        
    with open("test_img.jpg", "rb") as f:
        r_upload = client.post("/api/v1/evidence/upload", data={
            "issue_id": issue_id,
            "evidence_type": "AFTER_IMAGE",
            "uploaded_by": "op_1"
        }, files={"file": ("test_img.jpg", f, "image/jpeg")})
    assert r_upload.status_code == 201
    
    # 5. Submit Completion
    r_sub = client.post(f"/api/v1/work/{issue_id}/submit-completion", json={"operator_id": "op_1", "notes": "Done"})
    assert r_sub.status_code == 200
    
    # 6. Check Supervisor Queue
    r_queue = client.get("/api/v1/supervisor/verification-queue")
    assert r_queue.status_code == 200
    queue_data = r_queue.json()
    
    assert len(queue_data) == 1
    item = queue_data[0]
    
    # Assert integrity
    assert item["issue_id"] == issue_id
    assert item["department"] == "Drainage & Sewerage"
    
    assert item["before_image_url"] is None, "BUG: before_image_url should be None"
    assert item["after_image_url"].startswith("/api/v1/public/evidence/"), "BUG: after_image_url should use real token"
    assert "pothole" not in str(item["before_image_url"]).lower()
    assert "pothole" not in str(item["after_image_url"]).lower()

def test_evidence_restart_simulation():
    issue_id = "CIVIC-2026-RESTART"
    
    rec = MasterIssueRecord(
        id=issue_id, title="Test Issue", category=Category.DRAINAGE, subcategory="WATERLOGGING", severity_score=3, latitude=20.0, longitude=85.0
    )
    master_issue_store.add(rec)
    
    route = RoutingDecisionResult(
        decision_id="r_2", issue_id=issue_id, category=Category.DRAINAGE, subcategory="WATERLOGGING", primary_department="Drainage & Sewerage",
        responsible_unit="Stormwater & Drain Unit", escalation_department="Drainage & Sewerage", priority_score=75, priority_level="HIGH",
        selection_reason="Mock", matching_rule_name="Mock", rule_logic=["Mock"], confidence=1.0, routed_at="2026-08-16T10:00:00Z"
    )
    routing_store.save(route)
    routing_store._sync_to_db(route)
    
    escalation_state_machine.initialize_lifecycle(route)
    escalation_state_machine.acknowledge_issue(issue_id, "op_1")
    escalation_state_machine.start_work(issue_id, "op_1")
    
    with open("test_img.jpg", "wb") as f:
        f.write(b"fake image data")
        
    with open("test_img.jpg", "rb") as f:
        r_upload = client.post("/api/v1/evidence/upload", data={"issue_id": issue_id, "evidence_type": "AFTER_IMAGE", "uploaded_by": "op_1"}, files={"file": ("test_img.jpg", f, "image/jpeg")})
    assert r_upload.status_code == 201
    
    r_sub = client.post(f"/api/v1/work/{issue_id}/submit-completion", json={"operator_id": "op_1", "notes": "Done"})
    assert r_sub.status_code == 200
    
    # Simulate restart by clearing in-memory dicts and calling _load_from_db
    evidence_store._evidence.clear()
    evidence_store._file_contents.clear()
    evidence_store._load_from_db()
    
    r_queue = client.get("/api/v1/supervisor/verification-queue")
    assert r_queue.status_code == 200
    queue_data = r_queue.json()
    
    item = next((i for i in queue_data if i["issue_id"] == issue_id), None)
    assert item is not None
    assert item["before_image_url"] is None
    assert "pothole" not in str(item["after_image_url"]).lower()
    
    # 7. Check if stream returns actual bytes after restart
    url_path = item["after_image_url"]
    r_stream = client.get(url_path)
    assert r_stream.status_code == 200
    assert r_stream.content == b"fake image data"

def test_evidence_multi_category_isolation():
    categories = [
        (Category.ROAD_DAMAGE, "POTHOLE", "Roads & PWD"),
        (Category.ELECTRICITY, "STREETLIGHT", "Energy Department"),
        (Category.GARBAGE, "GARBAGE", "Solid Waste Management")
    ]
    
    for idx, (cat, subcat, dept) in enumerate(categories):
        issue_id = f"CIVIC-2026-MULTI-{idx}"
        
        rec = MasterIssueRecord(
            id=issue_id, title=f"Test {subcat}", category=cat, subcategory=subcat, severity_score=3, latitude=20.0, longitude=85.0
        )
        master_issue_store.add(rec)
        
        route = RoutingDecisionResult(
            decision_id=f"r_multi_{idx}", issue_id=issue_id, category=cat, subcategory=subcat, primary_department=dept,
            responsible_unit="Test Unit", escalation_department=dept, priority_score=75, priority_level="HIGH",
            selection_reason="Mock", matching_rule_name="Mock", rule_logic=["Mock"], confidence=1.0, routed_at="2026-08-16T10:00:00Z"
        )
        routing_store.save(route)
        routing_store._sync_to_db(route)
        
        escalation_state_machine.initialize_lifecycle(route)
        escalation_state_machine.acknowledge_issue(issue_id, "op_1")
        escalation_state_machine.start_work(issue_id, "op_1")
        
        with open(f"test_img_{idx}.jpg", "wb") as f:
            f.write(f"fake data {idx}".encode("utf-8"))
            
        with open(f"test_img_{idx}.jpg", "rb") as f:
            client.post("/api/v1/evidence/upload", data={"issue_id": issue_id, "evidence_type": "AFTER_IMAGE", "uploaded_by": "op_1"}, files={"file": (f"test_img_{idx}.jpg", f, "image/jpeg")})
            
        client.post(f"/api/v1/work/{issue_id}/submit-completion", json={"operator_id": "op_1", "notes": "Done"})
        
    r_queue = client.get("/api/v1/supervisor/verification-queue")
    assert r_queue.status_code == 200
    queue_data = r_queue.json()
    
    for idx, (cat, subcat, dept) in enumerate(categories):
        issue_id = f"CIVIC-2026-MULTI-{idx}"
        item = next((i for i in queue_data if i["issue_id"] == issue_id), None)
        assert item is not None
        assert item["category"] == cat.value if hasattr(cat, "value") else cat
        assert item["department"] == dept
        assert item["status"] == "BEFORE EVIDENCE NOT PROVIDED"
        assert item["before_image_url"] is None
        assert item["after_image_url"].startswith("/api/v1/public/evidence/")
        assert "pothole" not in str(item["after_image_url"]).lower()
