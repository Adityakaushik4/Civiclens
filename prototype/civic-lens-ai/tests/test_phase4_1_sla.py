import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import Category
from app.priority import PriorityLevel
from app.routing import RoutingRequest, routing_engine, routing_store
from app.escalation import escalation_state_machine, escalation_store
from app.sla import (
    SLAPolicy,
    SLAPolicyStatus,
    SLAPolicyCreateRequest,
    SLAPolicyUpdateRequest,
    sla_policy_store,
    sla_calculator,
)

client = TestClient(app)
ADMIN_HEADER = {"X-Admin-API-Key": "admin-secret-key"}


@pytest.fixture(autouse=True)
def reset_all_stores():
    routing_store.clear()
    escalation_store.clear()
    sla_policy_store.seed_default_policies()


# =====================================================================
# 1. Provisional Default Policy Test
# =====================================================================
def test_provisional_default_policy():
    pol = sla_calculator.get_policy(Category.ROAD_DAMAGE.value, "OTHER", PriorityLevel.MEDIUM)
    assert pol is not None
    assert pol.status == SLAPolicyStatus.PROVISIONAL
    assert pol.source_reference is None
    assert pol.source_title is None
    assert pol.acknowledgement_minutes == 360
    assert pol.resolution_minutes == 4320


# =====================================================================
# 2. Authoritative Policy Creation & Lookup Test
# =====================================================================
def test_authoritative_policy_with_source():
    create_req = {
        "policy_id": "sla_auth_pothole_blr",
        "jurisdiction_id": "bbmp_bengaluru",
        "category": "ROAD_DAMAGE",
        "subcategory": "POTHOLE",
        "priority_level": "HIGH",
        "acknowledgement_minutes": 30,
        "resolution_minutes": 720,
        "status": "AUTHORITATIVE",
        "source_reference": "BBMP Citizen Charter 2025 Sec 14-B",
        "source_title": "Bengaluru Municipal Pothole Resolution Standard",
    }
    resp = client.post("/api/v1/admin/sla-policies", json=create_req, headers=ADMIN_HEADER)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "AUTHORITATIVE"
    assert data["source_reference"] == "BBMP Citizen Charter 2025 Sec 14-B"

    # Verify resolution picks this authoritative policy for BBMP
    resolved_pol = sla_calculator.get_policy(
        category="ROAD_DAMAGE",
        subcategory="POTHOLE",
        priority_level=PriorityLevel.HIGH,
        jurisdiction_id="bbmp_bengaluru",
    )
    assert resolved_pol.policy_id == "sla_auth_pothole_blr"
    assert resolved_pol.status == SLAPolicyStatus.AUTHORITATIVE


# =====================================================================
# 3. Missing Source Validation Failure for Authoritative Policy
# =====================================================================
def test_authoritative_policy_missing_source_rejected():
    create_req = {
        "policy_id": "sla_invalid_auth",
        "category": "ROAD_DAMAGE",
        "priority_level": "HIGH",
        "acknowledgement_minutes": 30,
        "resolution_minutes": 300,
        "status": "AUTHORITATIVE",
        # source_reference missing
    }
    resp = client.post("/api/v1/admin/sla-policies", json=create_req, headers=ADMIN_HEADER)
    assert resp.status_code == 400
    assert "source_reference" in resp.json()["detail"]


# =====================================================================
# 4. Deterministic Precedence Test (Jurisdiction > Global, Subcat > Cat)
# =====================================================================
def test_sla_policy_precedence_hierarchy():
    now_str = datetime.now(timezone.utc).isoformat()

    # 1. Global Category policy
    global_cat_pol = SLAPolicy(
        policy_id="sla_global_road",
        jurisdiction_id=None,
        category="ROAD_DAMAGE",
        subcategory="*",
        priority_level=PriorityLevel.HIGH,
        acknowledgement_minutes=90,
        resolution_minutes=2000,
        status=SLAPolicyStatus.PROVISIONAL,
        created_at=now_str,
        updated_at=now_str,
    )
    sla_policy_store.save(global_cat_pol)

    # 2. Jurisdiction Category policy
    jur_cat_pol = SLAPolicy(
        policy_id="sla_jur_road",
        jurisdiction_id="city_mumbai",
        category="ROAD_DAMAGE",
        subcategory="*",
        priority_level=PriorityLevel.HIGH,
        acknowledgement_minutes=45,
        resolution_minutes=1000,
        status=SLAPolicyStatus.PROVISIONAL,
        created_at=now_str,
        updated_at=now_str,
    )
    sla_policy_store.save(jur_cat_pol)

    # 3. Jurisdiction Subcategory policy
    jur_sub_pol = SLAPolicy(
        policy_id="sla_jur_pothole",
        jurisdiction_id="city_mumbai",
        category="ROAD_DAMAGE",
        subcategory="POTHOLE",
        priority_level=PriorityLevel.HIGH,
        acknowledgement_minutes=20,
        resolution_minutes=500,
        status=SLAPolicyStatus.PROVISIONAL,
        created_at=now_str,
        updated_at=now_str,
    )
    sla_policy_store.save(jur_sub_pol)

    # Test 1: Mumbai + Road + Pothole -> Picks Jurisdiction Subcategory (jur_sub_pol)
    p1 = sla_calculator.get_policy("ROAD_DAMAGE", "POTHOLE", PriorityLevel.HIGH, jurisdiction_id="city_mumbai")
    assert p1.policy_id == "sla_jur_pothole"

    # Test 2: Mumbai + Road + CRACKED_ROAD -> Picks Jurisdiction Category (jur_cat_pol)
    p2 = sla_calculator.get_policy("ROAD_DAMAGE", "CRACKED_ROAD", PriorityLevel.HIGH, jurisdiction_id="city_mumbai")
    assert p2.policy_id == "sla_jur_road"

    # Test 3: Delhi + Road + POTHOLE -> Falls back to Global Override (sla_road_pothole_high)
    p3 = sla_calculator.get_policy("ROAD_DAMAGE", "POTHOLE", PriorityLevel.HIGH, jurisdiction_id="city_delhi")
    assert p3.policy_id == "sla_road_pothole_high"


# =====================================================================
# 5. Inactive Policy Skipping Test
# =====================================================================
def test_inactive_policy_skipped():
    now_str = datetime.now(timezone.utc).isoformat()
    inactive_pol = SLAPolicy(
        policy_id="sla_inactive_test",
        jurisdiction_id="city_pune",
        category="GARBAGE",
        subcategory="*",
        priority_level=PriorityLevel.LOW,
        acknowledgement_minutes=5,
        resolution_minutes=30,
        status=SLAPolicyStatus.INACTIVE,
        active=False,
        created_at=now_str,
        updated_at=now_str,
    )
    sla_policy_store.save(inactive_pol)

    resolved = sla_calculator.get_policy("GARBAGE", "OTHER", PriorityLevel.LOW, jurisdiction_id="city_pune")
    assert resolved.policy_id != "sla_inactive_test"
    assert resolved.policy_id == "sla_pol_low"


# =====================================================================
# 6. Admin API CRUD & Soft Delete Test
# =====================================================================
def test_admin_api_crud_and_soft_delete():
    # 1. Create policy via API
    create_payload = {
        "policy_id": "sla_admin_test_1",
        "category": "PARK",
        "subcategory": "VANDALISM",
        "priority_level": "MEDIUM",
        "acknowledgement_minutes": 120,
        "resolution_minutes": 1440,
        "status": "PROVISIONAL",
    }
    create_res = client.post("/api/v1/admin/sla-policies", json=create_payload, headers=ADMIN_HEADER)
    assert create_res.status_code == 201
    assert create_res.json()["policy_id"] == "sla_admin_test_1"

    # 2. Update policy via API
    update_payload = {"resolution_minutes": 2880}
    update_res = client.put("/api/v1/admin/sla-policies/sla_admin_test_1", json=update_payload, headers=ADMIN_HEADER)
    assert update_res.status_code == 200
    assert update_res.json()["resolution_minutes"] == 2880

    # 3. Soft Delete (Deactivate) policy
    del_res = client.delete("/api/v1/admin/sla-policies/sla_admin_test_1", headers=ADMIN_HEADER)
    assert del_res.status_code == 200
    assert del_res.json()["active"] is False
    assert del_res.json()["status"] == "INACTIVE"


# =====================================================================
# 7. Historical Policy Preservation Test
# =====================================================================
def test_historical_policy_preservation():
    # 1. Route issue with initial policy (sla_pol_medium: 360m ack, 4320m res)
    req = RoutingRequest(
        issue_id="issue_hist_preserve",
        category=Category.PARK,
        subcategory="OTHER",
        priority_score=45,
        priority_level=PriorityLevel.MEDIUM,
    )
    decision = routing_engine.route_issue(req)
    lifecycle = escalation_state_machine.initialize_lifecycle(decision)
    original_ack_deadline = lifecycle.acknowledgement_deadline

    # 2. Update global medium policy via Admin API
    update_res = client.put(
        "/api/v1/admin/sla-policies/sla_pol_medium",
        json={"acknowledgement_minutes": 10},
        headers=ADMIN_HEADER,
    )
    assert update_res.status_code == 200

    # 3. Verify existing lifecycle record preserved original deadline
    existing_lifecycle = escalation_store.get("issue_hist_preserve")
    assert existing_lifecycle.acknowledgement_deadline == original_ack_deadline
    assert existing_lifecycle.sla.acknowledgement_minutes == 360

    # 4. Verify newly routed issue uses updated policy
    req_new = RoutingRequest(
        issue_id="issue_hist_new",
        category=Category.PARK,
        subcategory="OTHER",
        priority_score=45,
        priority_level=PriorityLevel.MEDIUM,
    )
    decision_new = routing_engine.route_issue(req_new)
    assert decision_new.sla.acknowledgement_minutes == 10


# =====================================================================
# 8. Invalid Policy Rejections Test
# =====================================================================
def test_invalid_policy_rejections():
    # Resolution <= Ack
    r1 = client.post(
        "/api/v1/admin/sla-policies",
        json={
            "category": "GARBAGE",
            "priority_level": "LOW",
            "acknowledgement_minutes": 100,
            "resolution_minutes": 50,
        },
        headers=ADMIN_HEADER,
    )
    assert r1.status_code == 400

    # Invalid Category
    r2 = client.post(
        "/api/v1/admin/sla-policies",
        json={
            "category": "INVALID_CATEGORY_NAME",
            "priority_level": "LOW",
            "acknowledgement_minutes": 10,
            "resolution_minutes": 100,
        },
        headers=ADMIN_HEADER,
    )
    assert r2.status_code == 400

    # Invalid Date Range
    r3 = client.post(
        "/api/v1/admin/sla-policies",
        json={
            "category": "GARBAGE",
            "priority_level": "LOW",
            "acknowledgement_minutes": 10,
            "resolution_minutes": 100,
            "effective_from": "2026-12-31T00:00:00Z",
            "effective_until": "2026-01-01T00:00:00Z",
        },
        headers=ADMIN_HEADER,
    )
    assert r3.status_code == 400


# =====================================================================
# 9. Admin Security Boundary Test
# =====================================================================
def test_admin_endpoint_security_boundary():
    # Request without X-Admin-API-Key header -> 401 Unauthorized
    r_unauth = client.get("/api/v1/admin/sla-policies")
    assert r_unauth.status_code == 401

    # Request with invalid X-Admin-API-Key header -> 401 Unauthorized
    r_bad_key = client.get("/api/v1/admin/sla-policies", headers={"X-Admin-API-Key": "wrong-key"})
    assert r_bad_key.status_code == 401

    # Request with valid header -> 200 OK
    r_valid = client.get("/api/v1/admin/sla-policies", headers=ADMIN_HEADER)
    assert r_valid.status_code == 200
    assert isinstance(r_valid.json(), list)


# =====================================================================
# 10. API Routing Response SLA Payload Format Test (Section 10)
# =====================================================================
def test_routing_response_sla_payload_format():
    route_resp = client.post(
        "/api/v1/routing/route",
        json={
            "issue_id": "issue_sla_payload_check",
            "category": "ELECTRICITY",
            "subcategory": "SPARKING",
            "priority_score": 90,
            "priority_level": "CRITICAL",
            "jurisdiction_id": "ward_14",
        },
    )
    assert route_resp.status_code == 200
    data = route_resp.json()
    assert "sla" in data
    assert data["sla"] is not None
    assert data["sla"]["policy_id"] == "sla_elec_critical"
    assert data["sla"]["status"] == "PROVISIONAL"
    assert "acknowledgement_deadline" in data["sla"]
    assert "resolution_deadline" in data["sla"]
