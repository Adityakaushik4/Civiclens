import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import Category
from app.priority import PriorityLevel
from app.duplicates import master_issue_store, MasterIssueRecord
from app.analytics import (
    AnalyticsSummaryRequest,
    analytics_engine,
    hotspot_engine,
    hotspot_store,
)
from app.opportunities import (
    AIDraftProposalRequest,
    opportunity_engine,
    opportunity_store,
)
from app.proposals import (
    ProposalStatus,
    ProposalCreateRequest,
    ProposalUpdateRequest,
    proposal_engine,
    proposal_store,
)
from app.finance import (
    AddCostItemRequest,
    BudgetCycleCreateRequest,
    finance_engine,
    finance_store,
)
from app.voting import (
    CastVoteRequest,
    voting_engine,
    voting_store,
)
from app.allocation import (
    allocation_engine,
    allocation_store,
)

client = TestClient(app)
ADMIN_HEADER = {"X-Admin-API-Key": "admin-secret-key"}


@pytest.fixture(autouse=True)
def reset_phase7_stores():
    master_issue_store.clear()
    hotspot_store.clear()
    opportunity_store.clear()
    proposal_store.clear()
    finance_store.clear()
    voting_store.clear()
    allocation_store.clear()

    # Seed 1 Master Issue
    rec = MasterIssueRecord(
        id="mi_p7_1",
        title="Pothole on Main Corridor",
        category=Category.ROAD_DAMAGE,
        subcategory="POTHOLE",
        severity_score=4,
        latitude=12.9716,
        longitude=77.5946,
        address_description="Main Corridor Ward 7",
    )
    rec.citizen_reporter_count = 8
    master_issue_store.add(rec)





# =====================================================================
# 1 & 2. Master Issue Aggregation & Duplicate-Safe Counting
# =====================================================================
def test_analytics_master_issue_aggregation():
    resp = client.get("/api/v1/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_master_issues"] == 1
    assert data["total_citizen_reports"] == 8


# =====================================================================
# 3 & 25. Geographic Hotspot Detection & Small-Cell Suppression
# =====================================================================
def test_hotspot_detection_and_small_cell_suppression():
    hotspots = hotspot_engine.detect_hotspots(radius_meters=500)
    assert len(hotspots) == 1
    hs = hotspots[0]
    assert hs.citizen_report_count == 8
    assert hs.suppressed_publicly is False  # reports >= 5

    # Seed small-cell record (reports < 5)
    master_issue_store.clear()
    small_rec = MasterIssueRecord(
        id="mi_small",
        title="Isolated Light Flickering",
        category=Category.ELECTRICITY,
        subcategory="LIGHTING",
        severity_score=2,
        latitude=12.9800,
        longitude=77.6000,
        address_description="Quiet Alley",
    )
    small_rec.citizen_reporter_count = 2
    master_issue_store.add(small_rec)




    small_hotspots = hotspot_engine.detect_hotspots(radius_meters=500)
    assert len(small_hotspots) == 1
    assert small_hotspots[0].suppressed_publicly is True  # Small-cell suppressed!


# =====================================================================
# 4. Temporal Trend Calculations
# =====================================================================
def test_temporal_trend_calculations():
    resp = client.get("/api/v1/analytics/trends")
    assert resp.status_code == 200
    trends = resp.json()
    assert len(trends) > 0
    assert trends[0]["category"] == "ROAD_DAMAGE"


# =====================================================================
# 5. Project Opportunity Generation
# =====================================================================
def test_project_opportunity_generation():
    opps = opportunity_engine.detect_opportunities(jurisdiction_id="WARD_7")
    assert len(opps) == 1
    assert opps[0].linked_master_issue_ids == ["mi_p7_1"]


# =====================================================================
# 6 & 7. Proposal Creation & Evidence Panel Linking
# =====================================================================
def test_proposal_creation_and_evidence_linking():
    prop = proposal_engine.create_proposal(
        ProposalCreateRequest(
            jurisdiction_id="WARD_7",
            title="Main Corridor Resurfacing",
            description="Complete resurfacing of Main Corridor road.",
            proposer_id="citizen_101",
            category="ROAD_DAMAGE",
            requested_budget=500000.0,
            linked_master_issue_ids=["mi_p7_1"],
        )
    )
    assert prop.status == ProposalStatus.ELIGIBLE
    assert prop.proposer_id_hash.startswith("usr_")
    
    # Verify the eligibility record was created successfully
    from app.finance.engine import finance_store
    eligibility = finance_store.get_eligibility(prop.proposal_id)
    assert eligibility is not None
    assert eligibility.is_eligible is True

    panel = proposal_store.get_evidence_panel(prop.proposal_id)
    assert panel is not None
    assert panel.total_citizen_reports == 8


# =====================================================================
# 8. AI Proposal Grounding & Disclaimer
# =====================================================================
def test_ai_proposal_grounding():
    opps = opportunity_engine.detect_opportunities(jurisdiction_id="WARD_7")
    ai_draft = opportunity_engine.generate_ai_draft_proposal(
        AIDraftProposalRequest(opportunity_id=opps[0].opportunity_id)
    )
    assert ai_draft.ai_generated_draft is True
    assert "Financial costs and government approval are NOT calculated by AI" in ai_draft.ai_disclaimer
    assert "mi_p7_1" in ai_draft.linked_master_issue_ids


# =====================================================================
# 9 & 10. Cost Calculation & Unit-Rate Provenance
# =====================================================================
def test_cost_calculation_and_provenance():
    prop = proposal_engine.create_proposal(
        ProposalCreateRequest(
            jurisdiction_id="WARD_7",
            title="Road Upgrade",
            description="Upgrade road.",
            category="ROAD_DAMAGE",
            requested_budget=0.0,
            linked_master_issue_ids=["mi_p7_1"],
        )
    )
    item = finance_engine.add_cost_item(
        AddCostItemRequest(
            proposal_id=prop.proposal_id,
            unit_item_name="Asphalt Resurfacing (sqm)",
            quantity=500.0,
            unit_rate=1000.0,
            provenance="AUTHORITATIVE",
            rate_table_ref="PWD-2026-RATE-04",
        )
    )
    assert item.subtotal == 500000.0
    updated_prop = proposal_store.get(prop.proposal_id)
    assert updated_prop.requested_budget == 500000.0
    assert updated_prop.cost_status == "AUTHORITATIVE"


# =====================================================================
# 11 & 12. Budget Cycle & 8-Rule Eligibility Engine
# =====================================================================
def test_8_rule_eligibility_engine():
    prop = proposal_engine.create_proposal(
        ProposalCreateRequest(
            jurisdiction_id="WARD_7",
            title="Ward 7 Road Upgrade",
            description="Road repair.",
            category="ROAD_DAMAGE",
            requested_budget=500000.0,
            linked_master_issue_ids=["mi_p7_1"],
        )
    )
    el = finance_engine.evaluate_eligibility(prop.proposal_id, cycle_id="cycle_ward7_2027")
    assert el.is_eligible is True
    assert len(el.rule_results) == 8
    assert all(el.rule_results.values())


# =====================================================================
# 14, 15, 16, 17, 18. Voting Ledger, Privacy, Fraud & Jurisdiction Guard
# =====================================================================
def test_participatory_voting_and_anti_fraud():
    prop = proposal_engine.create_proposal(
        ProposalCreateRequest(
            jurisdiction_id="WARD_7",
            title="Road Project",
            description="Desc.",
            category="ROAD_DAMAGE",
            requested_budget=500000.0,
            linked_master_issue_ids=["mi_p7_1"],
        )
    )
    finance_engine.evaluate_eligibility(prop.proposal_id, "cycle_ward7_2027")

    # Valid Vote
    vote = voting_engine.cast_vote(
        CastVoteRequest(
            cycle_id="cycle_ward7_2027",
            proposal_id=prop.proposal_id,
            citizen_id="cit_101",
            jurisdiction_id="WARD_7",
        )
    )
    assert vote.voter_token_hash.startswith("tok_")

    # Duplicate Vote Blocked
    with pytest.raises(ValueError, match="Duplicate vote detected"):
        voting_engine.cast_vote(
            CastVoteRequest(
                cycle_id="cycle_ward7_2027",
                proposal_id=prop.proposal_id,
                citizen_id="cit_101",
                jurisdiction_id="WARD_7",
            )
        )

    # Cross-Jurisdiction Blocked
    with pytest.raises(ValueError, match="Cross-jurisdiction voting blocked"):
        voting_engine.cast_vote(
            CastVoteRequest(
                cycle_id="cycle_ward7_2027",
                proposal_id=prop.proposal_id,
                citizen_id="cit_999",
                jurisdiction_id="DELHI_CENTRAL",
            )
        )


# =====================================================================
# 19 & 20. Deterministic 6-Factor Scoring & Explainability Matrix
# =====================================================================
def test_deterministic_6_factor_scoring():
    prop = proposal_engine.create_proposal(
        ProposalCreateRequest(
            jurisdiction_id="WARD_7",
            title="Road Resurfacing",
            description="Road repair.",
            category="ROAD_DAMAGE",
            requested_budget=500000.0,
            linked_master_issue_ids=["mi_p7_1"],
        )
    )
    sc = allocation_engine.calculate_proposal_score(prop.proposal_id, "cycle_ward7_2027")
    assert 0.0 <= sc.final_score <= 100.0
    assert "civic_need" in sc.score_breakdown
    assert "affected_citizens" in sc.score_breakdown
    assert "safety_impact" in sc.score_breakdown


# =====================================================================
# 21, 22, 23, 26. Knapsack Allocation, Budget Exhaustion & Audit Log
# =====================================================================
def test_knapsack_budget_allocation_and_exhaustion():
    # Proposal 1 (Within budget)
    p1 = proposal_engine.create_proposal(
        ProposalCreateRequest(
            jurisdiction_id="WARD_7",
            title="P1 High Priority Road Repair",
            description="Repair.",
            category="ROAD_DAMAGE",
            requested_budget=3000000.0,
            linked_master_issue_ids=["mi_p7_1"],
        )
    )
    finance_engine.evaluate_eligibility(p1.proposal_id, "cycle_ward7_2027")

    # Proposal 2 (Exceeds remaining budget)
    p2 = proposal_engine.create_proposal(
        ProposalCreateRequest(
            jurisdiction_id="WARD_7",
            title="P2 Expensive Bridge Upgrade",
            description="Bridge upgrade.",
            category="ROAD_DAMAGE",
            requested_budget=4000000.0,
            linked_master_issue_ids=["mi_p7_1"],
        )
    )
    finance_engine.evaluate_eligibility(p2.proposal_id, "cycle_ward7_2027")

    # Run allocation (Total Budget ₹50,00,000)
    alloc = client.post("/api/v1/admin/budget-cycles/cycle_ward7_2027/allocate", headers=ADMIN_HEADER)
    assert alloc.status_code == 200
    data = alloc.json()
    assert data["allocated_budget"] == 3000000.0
    assert data["remaining_budget"] == 2000000.0
    assert len(data["selected_proposals"]) == 1
    assert len(data["rejected_proposals"]) == 1
    assert len(data["decision_log"]) > 0


# =====================================================================
# 24. Public Dashboard Privacy Isolation
# =====================================================================
def test_public_dashboard_privacy_isolation():
    resp = client.get("/api/v1/public/participatory-budgeting/cycle_ward7_2027")
    assert resp.status_code == 200
    data = resp.json()
    assert "cycle_name" in data
    assert "proposals" in data
    # Ensure no raw citizen IDs or credentials are present
    assert "cit_101" not in str(data)

# =====================================================================
# 25. Regression Test: AI Draft Proposal requires valid opportunity_id
# =====================================================================
def test_ai_draft_proposal_requires_real_opportunity():
    # 1. Missing opportunity_id should return 422
    payload_missing = {
        "proposer_id": "citizen_1"
    }
    resp1 = client.post("/api/v1/proposals/ai-draft", json=payload_missing)
    assert resp1.status_code == 422
    
    # 2. Fake opportunity_id should return 404
    payload_fake = {
        "opportunity_id": "fake_opportunity_123",
        "proposer_id": "citizen_1"
    }
    resp2 = client.post("/api/v1/proposals/ai-draft", json=payload_fake)
    assert resp2.status_code == 404
    assert "not found" in resp2.json()["detail"].lower()

    # 3. Valid opportunity_id should succeed
    from app.opportunities.schemas import CivicProjectOpportunity
    from app.opportunities import opportunity_store
    
    # Create a mock opportunity in the store
    opp = CivicProjectOpportunity(
        opportunity_id="opp_p7_valid",
        jurisdiction_id="jurisdiction_test",
        title="Test Opportunity",
        category="ROAD_DAMAGE",
        total_citizen_reports=5,
        estimated_priority_avg=10.0,
        status="DETECTED",
        created_at="2026-08-16T00:00:00Z"
    )
    opportunity_store.save(opp)

    payload_valid = {
        "opportunity_id": "opp_p7_valid",
        "proposer_id": "citizen_1"
    }
    resp3 = client.post("/api/v1/proposals/ai-draft", json=payload_valid)
    assert resp3.status_code == 200
    data = resp3.json()
    assert data["opportunity_id"] == "opp_p7_valid"
    assert "suggested_title" in data
    assert "suggested_description" in data
