import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import Category
from app.priority import (
    PriorityCalculateRequest,
    PriorityLevel,
    priority_calculator,
    priority_store,
)
from app.gis import (
    VulnerableAsset,
    VulnerableAssetType,
    vulnerable_location_evaluator,
)
from app.routing import (
    RoutingRequest,
    routing_engine,
    routing_store,
)
from app.escalation import (
    IssueStatus,
    EscalationReason,
    escalation_state_machine,
    escalation_store,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_stores():
    priority_store.clear()
    routing_store.clear()
    escalation_store.clear()


# =====================================================================
# 1. High Safety Risk Test
# =====================================================================
def test_high_safety_risk_priority():
    req = PriorityCalculateRequest(
        issue_id="issue_high_risk",
        severity=5,
        safety_risk=True,
        public_impact=5,
        category=Category.ELECTRICITY,
        subcategory="SPARKING",
        citizen_reporter_count=1,
    )
    res = priority_calculator.calculate_priority(req)
    assert res.priority_score >= 80
    assert res.priority_level == PriorityLevel.CRITICAL
    assert res.factors.safety_risk.raw_value is True
    assert res.factors.safety_risk.contribution == 25.0



# =====================================================================
# 2. Low Severity Test
# =====================================================================
def test_low_severity_priority():
    req = PriorityCalculateRequest(
        issue_id="issue_low_sev",
        severity=1,
        safety_risk=False,
        public_impact=1,
        category=Category.GARBAGE,
        subcategory="UNCOLLECTED_GARBAGE",
        citizen_reporter_count=1,
        hours_unresolved=0.0,
    )
    res = priority_calculator.calculate_priority(req)
    assert res.priority_score <= 35
    assert res.priority_level == PriorityLevel.LOW
    assert res.factors.severity.raw_value == 1


# =====================================================================
# 3. Many Citizen Reports Test
# =====================================================================
def test_many_citizen_reports_boost():
    req_single = PriorityCalculateRequest(
        issue_id="issue_single_report",
        severity=2,
        safety_risk=False,
        public_impact=2,
        category=Category.ROAD_DAMAGE,
        subcategory="POTHOLE",
        citizen_reporter_count=1,
    )
    res_single = priority_calculator.calculate_priority(req_single)

    req_multi = PriorityCalculateRequest(
        issue_id="issue_multi_report",
        severity=2,
        safety_risk=False,
        public_impact=2,
        category=Category.ROAD_DAMAGE,
        subcategory="POTHOLE",
        citizen_reporter_count=25,
    )
    res_multi = priority_calculator.calculate_priority(req_multi)

    assert res_multi.priority_score > res_single.priority_score
    assert res_multi.factors.citizen_reports.boost_applied > 15.0


# =====================================================================
# 4. Vulnerable Location Proximity Test
# =====================================================================
def test_vulnerable_location_proximity():
    # St. Mary School is at (12.9716, 77.5946)
    # Target issue reported 40m away at (12.9718, 77.5946)
    req_near_school = PriorityCalculateRequest(
        issue_id="issue_near_school",
        severity=3,
        safety_risk=False,
        public_impact=3,
        category=Category.ROAD_DAMAGE,
        subcategory="POTHOLE",
        latitude=12.9718,
        longitude=77.5946,
    )
    res = priority_calculator.calculate_priority(req_near_school)

    assert res.factors.vulnerable_location.multiplier > 1.0
    assert len(res.factors.vulnerable_location.nearby_sensitive_assets) > 0
    asset_names = [a["name"] for a in res.factors.vulnerable_location.nearby_sensitive_assets]
    assert "St. Mary Primary School" in asset_names


# =====================================================================
# 5. Overdue Issue SLA Breach Test
# =====================================================================
def test_overdue_issue_sla_breach():
    routing_req = RoutingRequest(
        issue_id="issue_overdue_test",
        category=Category.ELECTRICITY,
        subcategory="SPARKING",
        priority_score=90,
        priority_level=PriorityLevel.CRITICAL,
    )
    decision = routing_engine.route_issue(routing_req)
    lifecycle = escalation_state_machine.initialize_lifecycle(decision)

    assert lifecycle.current_status == IssueStatus.ROUTED

    # Simulate time 30 mins past acknowledgement deadline (ack SLA is 15 mins)
    future_time = datetime.now(timezone.utc) + timedelta(minutes=45)
    updated_lifecycle = escalation_state_machine.check_and_apply_sla_breach("issue_overdue_test", current_time=future_time)

    assert updated_lifecycle.current_status == IssueStatus.ESCALATED
    assert updated_lifecycle.is_overdue is True
    assert len(updated_lifecycle.escalation_logs) == 1
    assert updated_lifecycle.escalation_logs[0].reason == EscalationReason.SLA_BREACH_ACK


# =====================================================================
# 6. Category Baseline Routing Test
# =====================================================================
def test_category_routing():
    req = RoutingRequest(
        issue_id="issue_road_cat",
        category=Category.ROAD_DAMAGE,
        subcategory="OTHER",
        priority_score=50,
        priority_level=PriorityLevel.MEDIUM,
    )
    decision = routing_engine.route_issue(req)
    assert decision.primary_department == "Roads & PWD"
    assert decision.responsible_unit == "Asphalt Patching Unit"
    assert decision.escalation_department == "Dept of Public Works (DPW)"


# =====================================================================
# 7. Subcategory Specific Routing Test
# =====================================================================
def test_subcategory_specialized_routing():
    req = RoutingRequest(
        issue_id="issue_exposed_wiring",
        category=Category.STREETLIGHT,
        subcategory="EXPOSED_WIRING",
        priority_score=85,
        priority_level=PriorityLevel.CRITICAL,
    )
    decision = routing_engine.route_issue(req)
    assert decision.primary_department == "Electrical / Street Lighting"
    assert decision.responsible_unit == "Rapid Hazard Electrical Crew"
    assert decision.escalation_department == "Chief Electrical Officer"


# =====================================================================
# 8. Unknown Category Fallback Test
# =====================================================================
def test_unknown_category_fallback_routing():
    req = RoutingRequest(
        issue_id="issue_unknown_cat",
        category=Category.OTHER,
        subcategory="UNKNOWN_SUBCAT_XYZ",
        priority_score=30,
        priority_level=PriorityLevel.LOW,
    )
    decision = routing_engine.route_issue(req)
    assert decision.primary_department == "Other / General"
    assert decision.responsible_unit == "Customer Support Triage Unit"


# =====================================================================
# 9. Manual Escalation & Acknowledgement API Test
# =====================================================================
def test_acknowledgement_and_escalation_api_flow():
    # 1. Route issue
    route_resp = client.post(
        "/api/v1/routing/route",
        json={
            "issue_id": "issue_api_flow",
            "category": "GARBAGE",
            "subcategory": "OVERFLOWING_BIN",
            "priority_score": 45,
            "priority_level": "MEDIUM",
        },
    )
    assert route_resp.status_code == 200
    assert route_resp.json()["primary_department"] == "Sanitation & Waste Management"

    # 2. Acknowledge issue
    ack_resp = client.post(
        "/api/v1/routing/issue_api_flow/acknowledge",
        json={"operator_id": "sanitation_op_42", "notes": "Dispatched crew to location"},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["current_status"] == "ACKNOWLEDGED"
    assert ack_resp.json()["acknowledged_by"] == "sanitation_op_42"

    # 3. Escalate issue
    esc_resp = client.post(
        "/api/v1/routing/issue_api_flow/escalate",
        json={
            "target_department": "Director of Sanitation",
            "reason": "OPERATOR_ESCALATED",
            "operator_id": "supervisor_1",
            "notes": "Crew delayed due to vehicle breakdown",
        },
    )
    assert esc_resp.status_code == 200
    assert esc_resp.json()["current_status"] == "ESCALATED"
    assert esc_resp.json()["current_department"] == "Director of Sanitation"


# =====================================================================
# 10. Explainability Test
# =====================================================================
def test_priority_and_routing_explainability():
    # Priority Explainability
    calc_resp = client.post(
        "/api/v1/priority/calculate",
        json={
            "issue_id": "issue_explainable",
            "severity": 4,
            "safety_risk": True,
            "public_impact": 4,
            "category": "ELECTRICITY",
            "subcategory": "SPARKING",
            "citizen_reporter_count": 5,
            "hours_unresolved": 12.0,
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert calc_resp.status_code == 200
    p_data = calc_resp.json()
    assert "score_computation_log" in p_data
    assert "factors" in p_data
    assert p_data["factors"]["safety_risk"]["normalized_score"] == 100.0

    # Routing Explainability
    route_resp = client.post(
        "/api/v1/routing/route",
        json={
            "issue_id": "issue_explainable",
            "category": "ELECTRICITY",
            "subcategory": "SPARKING",
            "priority_score": p_data["priority_score"],
            "priority_level": p_data["priority_level"],
        },
    )
    assert route_resp.status_code == 200
    r_data = route_resp.json()
    assert "selection_reason" in r_data
    assert "Exact subcategory rule match" in r_data["selection_reason"]


# =====================================================================
# 11. Priority Request Schema Validation Test
# =====================================================================
def test_priority_calculate_request_validation():
    # 1. Missing subcategory -> Must fail with 422
    invalid_resp = client.post(
        "/api/v1/priority/calculate",
        json={
            "severity": 4,
            "safety_risk": True,
            "public_impact": 4,
            "category": "ROAD_DAMAGE",
            "latitude": 20.2961,
            "longitude": 85.8245,
        },
    )
    assert invalid_resp.status_code == 422

    # 2. Complete payload with subcategory -> Must succeed with 200
    valid_resp = client.post(
        "/api/v1/priority/calculate",
        json={
            "severity": 4,
            "safety_risk": True,
            "public_impact": 4,
            "category": "ROAD_DAMAGE",
            "subcategory": "POTHOLE",
            "latitude": 20.2961,
            "longitude": 85.8245,
        },
    )
    assert valid_resp.status_code == 200
    data = valid_resp.json()
    assert data["priority_score"] >= 80
    assert data["priority_level"] == "CRITICAL"

