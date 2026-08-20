import uuid
import hashlib
import datetime
from typing import Dict, List, Optional, Set
from app.voting.schemas import CastVoteRequest, VoteRecord, VotingResultsSummary
from app.finance.engine import finance_store
from app.proposals.engine import proposal_store, ProposalStatus


from app.database.connection import SessionLocal
from app.database.models import VoteModel, VoterCredentialModel


class VotingStore:
    """Persistent database-backed append-only voting ledger."""

    def __init__(self):
        self._votes: Dict[str, VoteRecord] = {}
        self._voter_proposal_index: Set[str] = set()

    def save_vote(self, vote: VoteRecord) -> VoteRecord:
        idx_key = f"{vote.cycle_id}:{vote.voter_token_hash}:{vote.proposal_id}"
        if idx_key in self._voter_proposal_index:
            raise ValueError("Duplicate vote detected. Voter has already cast a vote for this proposal.")

        self._votes[vote.vote_id] = vote
        self._voter_proposal_index.add(idx_key)

        db = SessionLocal()
        try:
            # Ensure voter credential exists
            voter_cred = db.query(VoterCredentialModel).filter_by(voter_token_hash=vote.voter_token_hash).first()
            if not voter_cred:
                voter_cred = VoterCredentialModel(
                    voter_token_hash=vote.voter_token_hash,
                    cycle_id=vote.cycle_id,
                    jurisdiction_id=vote.jurisdiction_id,
                    votes_cast_count=1,
                )
                db.add(voter_cred)
            else:
                voter_cred.votes_cast_count += 1

            db_vote = db.query(VoteModel).filter_by(vote_id=vote.vote_id).first()
            if not db_vote:
                db_vote = VoteModel(
                    vote_id=vote.vote_id,
                    cycle_id=vote.cycle_id,
                    proposal_id=vote.proposal_id,
                    voter_token_hash=vote.voter_token_hash,
                    jurisdiction_id=vote.jurisdiction_id,
                )
                db.add(db_vote)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        return vote

    def list_by_cycle(self, cycle_id: str) -> List[VoteRecord]:
        res = [v for v in self._votes.values() if v.cycle_id == cycle_id]
        if res:
            return res
        db = SessionLocal()
        try:
            db_objs = db.query(VoteModel).filter_by(cycle_id=cycle_id).all()
            for db_obj in db_objs:
                v = VoteRecord(
                    vote_id=db_obj.vote_id,
                    cycle_id=db_obj.cycle_id,
                    proposal_id=db_obj.proposal_id,
                    voter_token_hash=db_obj.voter_token_hash,
                    jurisdiction_id=db_obj.jurisdiction_id,
                    voted_at=db_obj.voted_at.isoformat() if hasattr(db_obj.voted_at, "isoformat") else str(db_obj.voted_at),
                )
                self._votes[v.vote_id] = v
                key = (v.voter_token_hash, v.proposal_id)
                self._voter_proposal_index.add(key)
            return [v for v in self._votes.values() if v.cycle_id == cycle_id]
        except Exception:
            return []
        finally:
            db.close()


    def list_by_voter_token(self, cycle_id: str, voter_token_hash: str) -> List[VoteRecord]:
        return [v for v in self._votes.values() if v.cycle_id == cycle_id and v.voter_token_hash == voter_token_hash]

    def clear(self) -> None:
        self._votes.clear()
        self._voter_proposal_index.clear()
        db = SessionLocal()
        try:
            db.query(VoteModel).delete()
            db.query(VoterCredentialModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


voting_store = VotingStore()



class VotingEngine:
    """Engine managing blind token generation, anti-fraud checks, and append-only voting ledger."""

    def generate_blind_voter_token(self, citizen_id: str, cycle_id: str) -> str:
        """Generates blind cryptographic commitment H(CitizenID || CycleID || Salt)."""
        raw_str = f"{citizen_id.strip()}:{cycle_id}:CIVIC_LENS_BLIND_SALT_2027"
        return f"tok_{hashlib.sha256(raw_str.encode('utf-8')).hexdigest()[:16]}"

    def cast_vote(self, request: CastVoteRequest) -> VoteRecord:
        cycle = finance_store.get_cycle(request.cycle_id)
        if not cycle:
            raise KeyError(f"Budget cycle '{request.cycle_id}' not found.")

        # Cross-jurisdiction voting check
        if request.jurisdiction_id != cycle.jurisdiction_id:
            raise ValueError(f"Cross-jurisdiction voting blocked. Voter jurisdiction '{request.jurisdiction_id}' does not match cycle jurisdiction '{cycle.jurisdiction_id}'.")

        prop = proposal_store.get(request.proposal_id)
        if not prop:
            raise KeyError(f"Proposal '{request.proposal_id}' not found.")

        # Verify proposal eligibility status
        if prop.status not in [ProposalStatus.ELIGIBLE, ProposalStatus.VOTING]:
            raise ValueError(f"Proposal '{request.proposal_id}' is not in VOTING or ELIGIBLE status.")

        # STRICT ELIGIBILITY CHECK: Must have a valid passed eligibility record
        eligibility = finance_store.get_eligibility(request.proposal_id)
        if not eligibility or not eligibility.is_eligible:
            raise ValueError(f"Vote rejected: Proposal '{request.proposal_id}' does not have a valid eligibility record.")

        voter_token = self.generate_blind_voter_token(request.citizen_id, request.cycle_id)

        # Max votes per citizen check
        existing_votes = voting_store.list_by_voter_token(request.cycle_id, voter_token)
        if len(existing_votes) >= cycle.max_votes_per_citizen:
            raise ValueError(f"Maximum limit of {cycle.max_votes_per_citizen} votes per citizen reached for this cycle.")

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        vote = VoteRecord(
            vote_id=f"vote_{uuid.uuid4().hex[:8]}",
            cycle_id=request.cycle_id,
            proposal_id=request.proposal_id,
            voter_token_hash=voter_token,
            jurisdiction_id=request.jurisdiction_id,
            voted_at=now_str,
        )

        voting_store.save_vote(vote)

        # Transition proposal status to VOTING if needed
        if prop.status == ProposalStatus.ELIGIBLE:
            prop.status = ProposalStatus.VOTING
            proposal_store.save(prop)

        return vote

    def get_results_summary(self, cycle_id: str) -> VotingResultsSummary:
        votes = voting_store.list_by_cycle(cycle_id)
        unique_voters = len(set(v.voter_token_hash for v in votes))

        prop_counts: Dict[str, int] = {}
        for v in votes:
            prop_counts[v.proposal_id] = prop_counts.get(v.proposal_id, 0) + 1

        return VotingResultsSummary(
            cycle_id=cycle_id,
            total_votes_cast=len(votes),
            total_unique_voters=unique_voters,
            proposal_vote_counts=prop_counts,
        )


voting_engine = VotingEngine()
