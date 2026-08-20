import pytest
import os
import json
from app.proposals.engine import proposal_engine, proposal_store, ProposalCreateRequest, ProposalUpdateRequest
from app.proposals.schemas import ProposalStatus
from app.finance.engine import finance_store, finance_engine
from app.voting.engine import voting_engine, voting_store
from app.voting.schemas import CastVoteRequest
from app.database.connection import DATABASE_URL, SessionLocal
from app.database.models import CitizenProposalModel, VoteModel

def test_database_url_is_test():
    assert "test.db" in DATABASE_URL, f"DATABASE_URL is not test.db: {DATABASE_URL}"

@pytest.fixture(autouse=True)
def seed_test_data():
    # Explicitly seed the default cycle after the test db is recreated
    finance_store._seed_default_cycle()
    yield

def test_waterlogging_proposal_eligibility_flow():
    # Phase 3
    req = ProposalCreateRequest(
        jurisdiction_id="WARD_7",
        title="Fix Waterlogging on Main Ave",
        description="Drainage fix",
        proposer_id="citizen_tester",
        category="DRAINAGE",
        requested_budget=150000.0,
        linked_master_issue_ids=["CIVIC-2026-457A"],
        ai_generated_draft=False
    )
    
    # 1. Create Proposal (will automatically trigger evaluate_eligibility)
    prop = proposal_engine.create_proposal(req)
    
    # 2. Verify Eligibility Record
    eligibility = finance_store.get_eligibility(prop.proposal_id)
    assert eligibility is not None, "ProposalEligibility was not persisted"
    assert eligibility.is_eligible is True, "Proposal should be eligible"
    
    # 3. Verify Proposal Status
    prop = proposal_store.get(prop.proposal_id)
    assert prop.status == ProposalStatus.ELIGIBLE, f"Status is {prop.status}, expected ELIGIBLE"
    
    # Simulate Backend Reload
    db = SessionLocal()
    db_prop = db.query(CitizenProposalModel).filter_by(proposal_id=prop.proposal_id).first()
    assert db_prop is not None
    assert db_prop.status == "ELIGIBLE"
    db.close()
    
    # 4. Phase 4 - Voting Regression
    vote_req = CastVoteRequest(
        citizen_id="voter_1",
        cycle_id="cycle_ward7_2027",
        jurisdiction_id="WARD_7",
        proposal_id=prop.proposal_id
    )
    
    vote = voting_engine.cast_vote(vote_req)
    assert vote is not None, "Vote was not accepted"
    
    votes = voting_store.list_by_cycle("cycle_ward7_2027")
    assert len(votes) > 0, "Vote record not persisted"
    
    prop_after_vote = proposal_store.get(prop.proposal_id)
    assert prop_after_vote.status == ProposalStatus.VOTING
    
    # Enforce Vote Limits
    with pytest.raises(ValueError):
        for _ in range(5):
            voting_engine.cast_vote(vote_req)

def test_voting_rejection_rules():
    # Missing eligibility record
    req2 = ProposalCreateRequest(
        jurisdiction_id="WARD_7",
        title="Invalid Proposal",
        description="Desc",
        proposer_id="citizen_2",
        category="DRAINAGE",
        requested_budget=999999999.0, # Too expensive, will fail eligibility
        linked_master_issue_ids=[],
        ai_generated_draft=False
    )
    prop2 = proposal_engine.create_proposal(req2)
    assert prop2.status == ProposalStatus.INELIGIBLE
    
    # Attempt to vote on ineligible
    vote_req2 = CastVoteRequest(
        citizen_id="voter_2",
        cycle_id="cycle_ward7_2027",
        jurisdiction_id="WARD_7",
        proposal_id=prop2.proposal_id
    )
    with pytest.raises(ValueError, match="is not in VOTING or ELIGIBLE status"):
        voting_engine.cast_vote(vote_req2)
        
    # Attempt to hack status
    with pytest.raises(ValueError, match="Cannot transition to ELIGIBLE"):
        proposal_engine.update_proposal(prop2.proposal_id, ProposalUpdateRequest(status=ProposalStatus.ELIGIBLE))
