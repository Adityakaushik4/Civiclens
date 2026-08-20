from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_participatory_proposal_eligibility_flow():
    from app.finance.engine import finance_store
    finance_store.clear()
    
    # Create proposal preserving linked_master_issue_ids
    proposal_payload = {
        "title": "Drainage Fix",
        "description": "Fix drainage",
        "category": "DRAINAGE",
        "opportunity_id": "opp_ward7_drainage",
        "author_citizen_id": "citizen_999",
        "requested_budget": 500000,
        "linked_master_issue_ids": ["CIVIC-2026-457A"]
    }
    
    prop_res = client.post("/api/v1/proposals", json=proposal_payload)
    assert prop_res.status_code == 201
    prop_data = prop_res.json()
    proposal_id = prop_data["proposal_id"]
    
    assert "CIVIC-2026-457A" in prop_data["linked_master_issue_ids"]
    
    # Evaluate Eligibility
    elig_res = client.post(f"/api/v1/proposals/{proposal_id}/eligibility?cycle_id=cycle_ward7_2027")
    assert elig_res.status_code == 200
    elig_data = elig_res.json()
    
    assert elig_data["is_eligible"] is True
    assert elig_data["rule_results"]["rule_5_sufficient_master_issue_evidence"] is True
    
    # Vote on ELIGIBLE proposal
    vote_payload = {
        "cycle_id": "cycle_ward7_2027",
        "proposal_id": proposal_id,
        "citizen_id": "citizen_1",
        "jurisdiction_id": "WARD_7"
    }
    vote_res = client.post(f"/api/v1/voting/cycle_ward7_2027/vote", json=vote_payload)
    assert vote_res.status_code == 201
    
    bad_proposal_payload = {
        "title": "Bad Proposal",
        "description": "No evidence",
        "category": "DRAINAGE",
        "author_citizen_id": "citizen_999",
        "requested_budget": 500000,
        "linked_master_issue_ids": []
    }
    bad_prop_res = client.post("/api/v1/proposals", json=bad_proposal_payload)
    bad_proposal_id = bad_prop_res.json()["proposal_id"]
    
    # Evaluates to INELIGIBLE
    bad_elig_res = client.post(f"/api/v1/proposals/{bad_proposal_id}/eligibility?cycle_id=cycle_ward7_2027")
    assert bad_elig_res.json()["is_eligible"] is False
    
    # Try voting on INELIGIBLE proposal
    bad_vote_payload = {
        "cycle_id": "cycle_ward7_2027",
        "proposal_id": bad_proposal_id,
        "citizen_id": "citizen_2",
        "jurisdiction_id": "WARD_7"
    }
    bad_vote_res = client.post(f"/api/v1/voting/cycle_ward7_2027/vote", json=bad_vote_payload)
    assert bad_vote_res.status_code == 400
    assert "not in VOTING or ELIGIBLE status" in bad_vote_res.json()["detail"]


def test_participatory_cache_invalidation():
    from app.database.connection import SessionLocal
    from app.database.models import CitizenProposalModel
    from app.finance.engine import finance_store
    
    finance_store.clear()
    
    # 1. Create proposal with NO linked issues
    proposal_payload = {
        "title": "Cache Test",
        "description": "Testing cache",
        "category": "DRAINAGE",
        "opportunity_id": "opp_ward7_drainage",
        "author_citizen_id": "citizen_999",
        "requested_budget": 500000,
        "linked_master_issue_ids": []
    }
    
    prop_res = client.post("/api/v1/proposals", json=proposal_payload)
    assert prop_res.status_code == 201
    proposal_id = prop_res.json()["proposal_id"]
    
    # 2. Evaluate Eligibility -> should be False
    elig_res = client.post(f"/api/v1/proposals/{proposal_id}/eligibility?cycle_id=cycle_ward7_2027")
    assert elig_res.json()["is_eligible"] is False
    
    # 3. Modify DB directly (simulate external script)
    db = SessionLocal()
    db_obj = db.query(CitizenProposalModel).filter_by(proposal_id=proposal_id).first()
    db_obj.linked_master_issue_ids_json = ["CIVIC-2026-457A"]
    db.commit()
    db.close()
    
    # 4. Evaluate Eligibility again -> should be True (proves stateless DB read)
    elig_res2 = client.post(f"/api/v1/proposals/{proposal_id}/eligibility?cycle_id=cycle_ward7_2027")
    assert elig_res2.json()["is_eligible"] is True
