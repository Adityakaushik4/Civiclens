import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import Category
from app.priority import PriorityLevel
from app.routing import RoutingRequest, routing_engine, routing_store
from app.escalation import (
    IssueStatus,
    ActorType,
    EscalationReason,
    escalation_state_machine,
    escalation_store,
    ReopenPolicy,
    reopen_policy_store,
    reopen_idempotency_store,
)

client = TestClient(app)
ADMIN_HEADER = {"X-Admin-API-Key": "admin-secret-key"}


@pytest.fixture(autouse=True)
def reset_stores_phase5_1():
    routing_store.clear()
    escalation_store.clear()
    reopen_policy_store.reset_to_defaults()
    reopen_idempotency_store.clear()


def _create_routed_issue(issue_id: str = "issue_p51_test", jurisdiction_id: str = None) -> str:
    r_req = RoutingRequest(
        issue_id=issue_id,
        category=Category.ROAD_DAMAGE,
        subcategory="POTHOLE",
        priority_score=75,
        priority_level=PriorityLevel.HIGH,
        jurisdiction_id=jurisdiction_id,
    )
    decision = routing_engine.route_issue(r_req)
    escalation_state_machine.initialize_lifecycle(decision)
    return issue_id


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

def _get_admin_auth():
    r_login = client.post("/api/v1/auth/login", json={"email": "admin@civiclens.gov", "password": "admin123"})
    token = r_login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# =====================================================================
# 1. Repeated Identical Reopen Request & Idempotency Replay Test
# =====================================================================
def test_repeated_reopen_request_idempotency():
    issue_id = _create_routed_issue("issue_idem_1")
    citizen_id, headers = _get_citizen_auth()

    # First reopen call with key "key_abc123"
    resp1 = client.post(
        f"/api/v1/issues/{issue_id}/reopen",
        json={
            "actor_id": citizen_id,
            "reason": "Road repair failed",
            "idempotency_key": "key_abc123",
        },
        headers=headers,
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["current_status"] == "REOPENED"
    assert data1["reopened_count"] == 1
    assert data1["idempotency_replay"] is False
    assert len(data1["status_history"]) == 2  # Routed + Reopened

    # Second identical reopen call with same key "key_abc123"
    resp2 = client.post(
        f"/api/v1/issues/{issue_id}/reopen",
        json={
            "actor_id": citizen_id,
            "reason": "Road repair failed",
            "idempotency_key": "key_abc123",
        },
        headers=headers,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["reopened_count"] == 1  # Not incremented!
    assert data2["idempotency_replay"] is True  # Replay flag True!
    assert len(data2["status_history"]) == 2  # No duplicate history appended!


# =====================================================================
# 2. Header-Based Idempotency Key Test
# =====================================================================
def test_header_based_idempotency_key():
    issue_id = _create_routed_issue("issue_hdr_idem")
    citizen_id, auth_headers = _get_citizen_auth()

    headers = {"X-Idempotency-Key": "hdr_key_999", **auth_headers}
    resp1 = client.post(
        f"/api/v1/issues/{issue_id}/reopen",
        json={"actor_id": citizen_id, "reason": "Not fixed"},
        headers=headers,
    )
    assert resp1.status_code == 200
    assert resp1.json()["idempotency_replay"] is False
    assert resp1.json()["reopened_count"] == 1

    resp2 = client.post(
        f"/api/v1/issues/{issue_id}/reopen",
        json={"actor_id": citizen_id, "reason": "Not fixed"},
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["idempotency_replay"] is True
    assert resp2.json()["reopened_count"] == 1


# =====================================================================
# 3. Different Idempotency Keys Represent Distinct Reopen Attempts
# =====================================================================
def test_different_idempotency_keys_increment_count():
    issue_id = _create_routed_issue("issue_diff_keys")
    citizen_id, headers = _get_citizen_auth()

    resp1 = client.post(
        f"/api/v1/issues/{issue_id}/reopen",
        json={"actor_id": citizen_id, "reason": "Try 1", "idempotency_key": "key_1"},
        headers=headers,
    )
    assert resp1.json()["reopened_count"] == 1

    resp2 = client.post(
        f"/api/v1/issues/{issue_id}/reopen",
        json={"actor_id": citizen_id, "reason": "Try 2", "idempotency_key": "key_2"},
        headers=headers,
    )
    assert resp2.json()["reopened_count"] == 2
    assert resp2.json()["idempotency_replay"] is False


# =====================================================================
# 4. Configurable Reopen Threshold Evaluation (Threshold = 2)
# =====================================================================
def test_configurable_reopen_threshold():
    issue_id = _create_routed_issue("issue_config_thresh")

    # Update global policy threshold to 2
    admin_headers = _get_admin_auth()
    admin_resp = client.put(
        "/api/v1/admin/reopen-policies/reopen_pol_default",
        json={"reopen_threshold": 2},
        headers=admin_headers,
    )
    assert admin_resp.status_code == 200
    assert admin_resp.json()["reopen_threshold"] == 2

    # First reopen: count 1 (Threshold 2 not exceeded)
    rec1 = escalation_state_machine.reopen_issue(issue_id, actor_id="citizen_1", idempotency_key="k1")
    assert rec1.reopened_count == 1
    assert len(rec1.escalation_logs) == 0

    # Second reopen: count 2 (Threshold 2 reached -> auto-escalate!)
    rec2 = escalation_state_machine.reopen_issue(issue_id, actor_id="citizen_1", idempotency_key="k2")
    assert rec2.reopened_count == 2
    assert len(rec2.escalation_logs) == 1
    assert rec2.escalation_logs[0].reason == EscalationReason.REOPEN_THRESHOLD_EXCEEDED


# =====================================================================
# 5. Dedicated REOPEN_THRESHOLD_EXCEEDED Reason & System Actor Test
# =====================================================================
def test_dedicated_reason_and_system_actor():
    issue_id = _create_routed_issue("issue_system_actor")

    # Reopen 3 times to trigger default threshold = 3
    escalation_state_machine.reopen_issue(issue_id, actor_id="citizen_1", idempotency_key="k1")
    escalation_state_machine.reopen_issue(issue_id, actor_id="citizen_1", idempotency_key="k2")
    rec = escalation_state_machine.reopen_issue(issue_id, actor_id="citizen_1", idempotency_key="k3")

    assert rec.reopened_count == 3
    assert len(rec.escalation_logs) == 1
    esc_log = rec.escalation_logs[0]

    assert esc_log.reason == EscalationReason.REOPEN_THRESHOLD_EXCEEDED
    assert esc_log.actor_type == ActorType.SYSTEM
    assert esc_log.actor_id == "SYSTEM_ESCALATION_ENGINE"
    assert esc_log.reopen_count == 3


# =====================================================================
# 6. Immutable SLA Snapshot Preservation Test
# =====================================================================
def test_immutable_sla_snapshot_on_auto_escalation():
    issue_id = _create_routed_issue("issue_immutable_sla")

    initial_rec = escalation_store.get(issue_id)
    initial_sla = initial_rec.sla
    initial_ack_deadline = initial_rec.acknowledgement_deadline
    initial_res_deadline = initial_rec.resolution_deadline

    # Trigger auto-escalation via 3 reopenings
    escalation_state_machine.reopen_issue(issue_id, idempotency_key="k1")
    escalation_state_machine.reopen_issue(issue_id, idempotency_key="k2")
    final_rec = escalation_state_machine.reopen_issue(issue_id, idempotency_key="k3")

    # Verify SLA snapshot and deadlines are completely unchanged!
    assert final_rec.sla == initial_sla
    assert final_rec.acknowledgement_deadline == initial_ack_deadline
    assert final_rec.resolution_deadline == initial_res_deadline


# =====================================================================
# 7. Append-Only Audit History Test
# =====================================================================
def test_append_only_audit_history():
    issue_id = _create_routed_issue("issue_audit_hist")

    escalation_state_machine.reopen_issue(issue_id, actor_id="citizen_anand", notes="Notes 1", idempotency_key="k1")
    escalation_state_machine.reopen_issue(issue_id, actor_id="supervisor_patil", notes="Notes 2", idempotency_key="k2")

    rec = escalation_store.get(issue_id)
    # Routed + Reopened 1 + Reopened 2
    assert len(rec.status_history) == 3
    assert rec.status_history[1].actor_type == ActorType.CITIZEN
    assert rec.status_history[1].actor_id == "citizen_anand"
    assert rec.status_history[2].actor_type == ActorType.SUPERVISOR
    assert rec.status_history[2].actor_id == "supervisor_patil"


# =====================================================================
# 8. Duplicate Escalation Prevention on Idempotency Replay Test
# =====================================================================
def test_duplicate_escalation_prevention_on_replay():
    issue_id = _create_routed_issue("issue_prevent_dup_esc")

    # Trigger auto-escalation on 3rd reopen
    escalation_state_machine.reopen_issue(issue_id, idempotency_key="k1")
    escalation_state_machine.reopen_issue(issue_id, idempotency_key="k2")
    rec3 = escalation_state_machine.reopen_issue(issue_id, idempotency_key="k3")
    assert len(rec3.escalation_logs) == 1

    # Re-send 3rd reopen request with same key "k3"
    rec3_replay = escalation_state_machine.reopen_issue(issue_id, idempotency_key="k3")
    assert rec3_replay.idempotency_replay is True
    assert len(rec3_replay.escalation_logs) == 1  # Still exactly 1 escalation log!


# =====================================================================
# 9. Jurisdiction-Specific Reopen Policy Precedence Test
# =====================================================================
def test_jurisdiction_specific_reopen_policy():
    j_id = "BLR_URBAN"
    issue_id = _create_routed_issue("issue_j_policy", jurisdiction_id=j_id)

    # Create jurisdiction-specific policy with threshold = 1
    admin_headers = _get_admin_auth()
    create_resp = client.post(
        "/api/v1/admin/reopen-policies",
        json={
            "policy_id": "reopen_pol_blr",
            "jurisdiction_id": j_id,
            "enabled": True,
            "reopen_threshold": 1,
            "status": "PROVISIONAL",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201

    # Reopen 1 time -> Should auto-escalate due to jurisdiction policy (threshold = 1)
    rec = escalation_state_machine.reopen_issue(issue_id, idempotency_key="k1")
    assert rec.reopened_count == 1
    assert len(rec.escalation_logs) == 1
    assert rec.escalation_logs[0].reason == EscalationReason.REOPEN_THRESHOLD_EXCEEDED


# =====================================================================
# 10. Disabled Reopen Escalation Policy Test
# =====================================================================
def test_disabled_reopen_policy_prevents_auto_escalation():
    issue_id = _create_routed_issue("issue_disabled_policy")

    # Disable default policy
    admin_headers = _get_admin_auth()
    client.put(
        "/api/v1/admin/reopen-policies/reopen_pol_default",
        json={"enabled": False},
        headers=admin_headers,
    )

    # Reopen 5 times -> Auto-escalation should NOT trigger
    for i in range(1, 6):
        rec = escalation_state_machine.reopen_issue(issue_id, idempotency_key=f"k_{i}")

    assert rec.reopened_count == 5
    assert len(rec.escalation_logs) == 0  # No auto-escalation performed!
