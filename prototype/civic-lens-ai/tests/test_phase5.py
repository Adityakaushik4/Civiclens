import io
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import Category
from app.priority import PriorityCalculateRequest, PriorityLevel, priority_calculator
from app.routing import RoutingRequest, routing_engine, routing_store
from app.escalation import IssueStatus, escalation_state_machine, escalation_store
from app.assignment import AssignWorkRequest, assignment_engine, assignment_store
from app.evidence import EvidenceType, VerifyEvidenceRequest, evidence_store, verification_engine
from app.privacy import public_issue_store, privacy_transformer


client = TestClient(app)
ADMIN_HEADER = {"X-Admin-API-Key": "admin-secret-key"}


@pytest.fixture(autouse=True)
def reset_all_phase5_stores():
    routing_store.clear()
    escalation_store.clear()
    assignment_store.clear()
    evidence_store.clear()
    if hasattr(verification_engine, "_store"):
        verification_engine._store.clear()
    public_issue_store.clear()


# Helper function to setup a routed issue
def _create_routed_issue(issue_id: str = "issue_p5_test") -> str:
    r_req = RoutingRequest(
        issue_id=issue_id,
        category=Category.ROAD_DAMAGE,
        subcategory="POTHOLE",
        priority_score=75,
        priority_level=PriorityLevel.HIGH,
    )
    decision = routing_engine.route_issue(r_req)
    escalation_state_machine.initialize_lifecycle(decision)
    return issue_id


# =====================================================================
# 1. Work Assignment & Reassignment Test
# =====================================================================
def test_work_assignment_and_reassignment():
    issue_id = _create_routed_issue("issue_assign_test")

    # Initial Assignment
    assign_resp = client.post(
        "/api/v1/work/assign",
        json={
            "issue_id": issue_id,
            "department_id": "Roads & PWD",
            "unit_id": "Asphalt Patching Unit",
            "assigned_operator_id": "op_rajesh_1",
            "assigned_by": "supervisor_sharma",
            "notes": "Dispatch asphalt patch truck",
        },
    )
    assert assign_resp.status_code == 200
    data = assign_resp.json()
    assert data["status"] == "ASSIGNED"
    assert data["assigned_operator_id"] == "op_rajesh_1"

    # Reassignment
    reassign_resp = client.post(
        "/api/v1/work/assign",
        json={
            "issue_id": issue_id,
            "department_id": "Roads & PWD",
            "unit_id": "Asphalt Patching Unit",
            "assigned_operator_id": "op_suresh_2",
            "assigned_by": "supervisor_sharma",
            "notes": "Reassigned due to shift change",
        },
    )
    assert reassign_resp.status_code == 200
    r_data = reassign_resp.json()
    assert r_data["status"] == "REASSIGNED"
    assert r_data["assigned_operator_id"] == "op_suresh_2"


# =====================================================================
# 2. Work Start Transition Test
# =====================================================================
def test_work_start_transition():
    issue_id = _create_routed_issue("issue_start_test")
    escalation_state_machine.acknowledge_issue(issue_id, operator_id="op_rajesh_1")

    resp = client.post(
        f"/api/v1/work/{issue_id}/start?operator_id=op_rajesh_1&notes=Crew+on+site"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_status"] == "IN_PROGRESS"
    assert data["assigned_operator_id"] == "op_rajesh_1"
    assert data["work_started_at"] is not None


# =====================================================================
# 3. Valid Evidence Upload & EXIF Sanitization Test
# =====================================================================
def test_valid_evidence_upload():
    issue_id = _create_routed_issue("issue_ev_upload_test")

    # Create dummy 1x1 JPEG image bytes
    dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"

    resp = client.post(
        "/api/v1/evidence/upload",
        data={
            "issue_id": issue_id,
            "evidence_type": "AFTER_IMAGE",
            "uploaded_by": "op_rajesh_1",
        },
        files={"file": ("after_pothole.jpg", io.BytesIO(dummy_jpeg), "image/jpeg")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["evidence_type"] == "AFTER_IMAGE"
    assert data["verification_status"] == "PENDING"
    assert data["public_token"] is not None


def test_valid_jpg_alias_mime_type_upload():
    issue_id = _create_routed_issue("issue_ev_upload_jpg_alias_test")

    dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xd9"

    resp = client.post(
        "/api/v1/evidence/upload",
        data={
            "issue_id": issue_id,
            "evidence_type": "AFTER_IMAGE",
            "uploaded_by": "op_rajesh_1",
        },
        files={"file": ("after_pothole.jpg", io.BytesIO(dummy_jpeg), "image/jpg")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mime_type"] == "image/jpeg"


def test_valid_png_evidence_upload():
    issue_id = _create_routed_issue("issue_ev_upload_png_test")

    dummy_png = bytes.fromhex(
        "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
        "0000000A49444154789C63600000020001E221BC330000000049454E44AE426082"
    )

    resp = client.post(
        "/api/v1/evidence/upload",
        data={
            "issue_id": issue_id,
            "evidence_type": "AFTER_IMAGE",
            "uploaded_by": "op_rajesh_1",
        },
        files={"file": ("after_pothole.png", io.BytesIO(dummy_png), "image/png")},
    )
    assert resp.status_code == 201
    assert resp.json()["mime_type"] == "image/png"


# =====================================================================
# 4. Invalid Evidence File Rejection Test
# =====================================================================
def test_invalid_evidence_mime_type_rejected():
    issue_id = _create_routed_issue("issue_invalid_ev")

    fake_script = b"<?php echo 'malicious'; ?>"
    resp = client.post(
        "/api/v1/evidence/upload",
        data={
            "issue_id": issue_id,
            "evidence_type": "AFTER_IMAGE",
            "uploaded_by": "op_rajesh_1",
        },
        files={"file": ("exploit.php", io.BytesIO(fake_script), "application/x-php")},
    )
    assert resp.status_code == 400
    assert "Only images and audio files are allowed" in resp.json()["detail"]


# =====================================================================
# 5. Oversized File Rejection Test
# =====================================================================
def test_oversized_evidence_file_rejected():
    issue_id = _create_routed_issue("issue_oversized_ev")

    # Create dummy 11MB payload
    large_payload = b"0" * (11 * 1024 * 1024)
    resp = client.post(
        "/api/v1/evidence/upload",
        data={
            "issue_id": issue_id,
            "evidence_type": "BEFORE_IMAGE",
            "uploaded_by": "op_rajesh_1",
        },
        files={"file": ("huge.jpg", io.BytesIO(large_payload), "image/jpeg")},
    )
    assert resp.status_code == 400
    assert "exceeds maximum allowed limit" in resp.json()["detail"]


# =====================================================================
# 6. Evidence Verification Approval Test
# =====================================================================
def test_evidence_verification_approval():
    issue_id = _create_routed_issue("issue_verify_app")
    escalation_state_machine.acknowledge_issue(issue_id, "operator_1")
    escalation_state_machine.start_work(issue_id)
    escalation_state_machine.submit_completion(issue_id)

    dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xd9"
    ev_record = evidence_store.save_evidence(
        issue_id, EvidenceType.AFTER_IMAGE, "fixed.jpg", "image/jpeg", dummy_jpeg
    )

    verify_resp = client.post(
        f"/api/v1/evidence/{ev_record.evidence_id}/verify",
        json={
            "evidence_id": ev_record.evidence_id,
            "verifier_id": "supervisor_patil",
            "decision": "APPROVED",
        },
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["decision"] == "APPROVED"

    lifecycle = escalation_store.get(issue_id)
    assert lifecycle.current_status == IssueStatus.RESOLVED


# =====================================================================
# 7. Evidence Verification Rejection Test
# =====================================================================
def test_evidence_verification_rejection():
    issue_id = _create_routed_issue("issue_verify_rej")
    escalation_state_machine.acknowledge_issue(issue_id, "operator_1")
    escalation_state_machine.start_work(issue_id)
    escalation_state_machine.submit_completion(issue_id)

    dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xd9"
    ev_record = evidence_store.save_evidence(
        issue_id, EvidenceType.AFTER_IMAGE, "blurry.jpg", "image/jpeg", dummy_jpeg
    )

    verify_resp = client.post(
        f"/api/v1/evidence/{ev_record.evidence_id}/verify",
        json={
            "evidence_id": ev_record.evidence_id,
            "verifier_id": "supervisor_patil",
            "decision": "REJECTED",
            "rejection_reason": "Image is blurry and pothole is not filled properly.",
        },
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["decision"] == "REJECTED"

    lifecycle = escalation_store.get(issue_id)
    assert lifecycle.current_status == IssueStatus.REOPENED


import uuid

def _get_citizen_auth():
    email = f"cit_{uuid.uuid4().hex[:6]}@civiclens.gov"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": "Test Citizen",
        "role": "CITIZEN"
    })
    r_login = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = r_login.json()["access_token"]
    r_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return r_me.json()["id"], {"Authorization": f"Bearer {token}"}


# =====================================================================
# 8. Citizen Reopening Flow Test
# =====================================================================
def test_citizen_reopening_flow():
    issue_id = _create_routed_issue("issue_citizen_reopen")
    escalation_state_machine.acknowledge_issue(issue_id, "operator_1")
    escalation_state_machine.start_work(issue_id)
    escalation_state_machine.resolve_issue(issue_id, verifier_id="supervisor_patil")

    citizen_id, headers = _get_citizen_auth()

    reopen_resp = client.post(
        f"/api/v1/issues/{issue_id}/reopen",
        json={
            "actor_id": citizen_id,
            "reason": "Water is still leaking from the main pipe.",
            "notes": "Pothole reappeared after rain",
        },
        headers=headers,
    )
    assert reopen_resp.status_code == 200
    data = reopen_resp.json()
    assert data["current_status"] == "REOPENED"
    assert data["reopened_count"] == 1


# =====================================================================
# 9. Public vs Private View Data Isolation Test
# =====================================================================
def test_public_vs_private_view_isolation():
    issue_id = _create_routed_issue("issue_privacy_isolation")

    public_resp = client.get(f"/api/v1/public/issues/{issue_id}")
    assert public_resp.status_code == 200
    pub_data = public_resp.json()

    # Verify public ID format
    assert pub_data["public_id"].startswith("CIVIC-2026-")

    # Verify no PII fields present in public JSON schema keys
    assert "complainant_name" not in pub_data
    assert "complainant_phone" not in pub_data
    assert "complainant_email" not in pub_data
    assert "private_file_key" not in pub_data

    # Verify fuzzed coordinates
    assert pub_data["fuzzed_latitude"] == round(pub_data["fuzzed_latitude"], 3)
    assert pub_data["fuzzed_longitude"] == round(pub_data["fuzzed_longitude"], 3)


# =====================================================================
# 10. Public Media Proxy Streaming Test
# =====================================================================
def test_public_media_proxy_streaming():
    issue_id = _create_routed_issue("issue_media_proxy")
    dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xd9"
    ev = evidence_store.save_evidence(
        issue_id, EvidenceType.AFTER_IMAGE, "media.jpg", "image/jpeg", dummy_jpeg
    )

    media_resp = client.get(f"/api/v1/public/evidence/CIVIC-2026-TEST/media/{ev.public_token}")
    assert media_resp.status_code == 200
    assert media_resp.headers["content-type"] == "image/jpeg"
    assert media_resp.content == dummy_jpeg


# =====================================================================
# 11. Auto-Escalation on Repeated Reopenings Test
# =====================================================================
def test_auto_escalation_on_repeated_reopening():
    issue_id = _create_routed_issue("issue_repeat_reopen")

    # Reopen 3 times
    escalation_state_machine.reopen_issue(issue_id, actor_id="citizen_1", reason="Fix 1 failed")
    escalation_state_machine.reopen_issue(issue_id, actor_id="citizen_1", reason="Fix 2 failed")
    rec3 = escalation_state_machine.reopen_issue(issue_id, actor_id="citizen_1", reason="Fix 3 failed")

    assert rec3.reopened_count == 3
    assert len(rec3.escalation_logs) == 1
    assert "Auto-escalated:" in rec3.escalation_logs[0].notes



# =====================================================================
# 12. Full End-to-End Pipeline Integration Test (Phases 1-5)
# =====================================================================
def test_full_phases_1_to_5_integration_flow():
    # 1. Calculate Priority (Phase 4.1 Priority Engine)
    p_req = PriorityCalculateRequest(
        issue_id="issue_e2e_full",
        severity=4,
        safety_risk=True,
        public_impact=4,
        category=Category.ELECTRICITY,
        subcategory="SPARKING",
    )
    p_res = priority_calculator.calculate_priority(p_req)

    # 2. Route Issue (Phase 4 & 4.1 Routing & SLA Engine)
    r_req = RoutingRequest(
        issue_id="issue_e2e_full",
        category=Category.ELECTRICITY,
        subcategory="SPARKING",
        priority_score=p_res.priority_score,
        priority_level=p_res.priority_level,
    )
    route_dec = routing_engine.route_issue(r_req)
    escalation_state_machine.initialize_lifecycle(route_dec)

    # 3. Work Assignment (Phase 5 Assignment Engine)
    assign_record = assignment_engine.assign_work(
        AssignWorkRequest(
            issue_id="issue_e2e_full",
            department_id="Electrical / Street Lighting",
            unit_id="High Tension Emergency Unit",
            assigned_operator_id="op_grid_lead",
        )
    )
    assert assign_record.assigned_operator_id == "op_grid_lead"

    # 4. Work Start & Completion
    escalation_state_machine.acknowledge_issue("issue_e2e_full", operator_id="op_grid_lead")
    escalation_state_machine.start_work("issue_e2e_full", operator_id="op_grid_lead")
    escalation_state_machine.submit_completion("issue_e2e_full", operator_id="op_grid_lead")

    # 5. Upload After Evidence
    dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xd9"
    ev = evidence_store.save_evidence(
        "issue_e2e_full", EvidenceType.AFTER_IMAGE, "transformer_fixed.jpg", "image/jpeg", dummy_jpeg
    )

    # 6. Verification Approval
    ver = verification_engine.verify_evidence(
        VerifyEvidenceRequest(
            evidence_id=ev.evidence_id,
            verifier_id="supervisor_patil",
            decision="APPROVED",
        )
    )
    assert ver.decision == "APPROVED"

    # 7. Generate Public Tracking View
    pub_view = privacy_transformer.generate_public_view("issue_e2e_full")
    assert pub_view.status == IssueStatus.RESOLVED
    assert pub_view.department_name == "Electrical / Street Lighting"
    assert len(pub_view.public_evidence_urls) == 1
    assert len(pub_view.public_timeline) >= 4
