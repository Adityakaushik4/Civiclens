from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CastVoteRequest(BaseModel):
    cycle_id: str = Field(default="cycle_ward7_2027", description="Target voting budget cycle ID")
    proposal_id: str = Field(..., description="Target proposal UUID to vote for")
    citizen_id: str = Field(..., description="Raw citizen identifier, blinded on storage")
    jurisdiction_id: str = Field(default="WARD_7", description="Voter jurisdiction ID")


class VoteRecord(BaseModel):
    vote_id: str
    cycle_id: str
    proposal_id: str
    voter_token_hash: str = Field(..., description="Blind cryptographic token commitment H(CitizenID || CycleID)")
    jurisdiction_id: str
    voted_at: str


class VotingResultsSummary(BaseModel):
    cycle_id: str
    total_votes_cast: int
    total_unique_voters: int
    proposal_vote_counts: Dict[str, int]
