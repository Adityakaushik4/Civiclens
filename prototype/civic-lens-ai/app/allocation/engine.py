import math
import uuid
import datetime
from typing import Dict, List, Optional, Tuple, Any
from app.allocation.schemas import ProposalScore, BudgetAllocationResult
from app.proposals.engine import proposal_store, ProposalStatus
from app.finance.engine import finance_store
from app.voting.engine import voting_store
from app.duplicates import master_issue_store
from app.escalation import escalation_store


from app.database.connection import SessionLocal
from app.database.models import ProposalScoreModel, BudgetAllocationModel


class AllocationStore:
    """Persistent database-backed store for Proposal Scores and Budget Allocation Decisions."""

    def __init__(self):
        self._scores: Dict[str, ProposalScore] = {}
        self._allocations: Dict[str, BudgetAllocationResult] = {}

    def save_score(self, score: ProposalScore) -> ProposalScore:
        self._scores[score.proposal_id] = score
        db = SessionLocal()
        try:
            db_obj = db.query(ProposalScoreModel).filter_by(proposal_id=score.proposal_id).first()
            if not db_obj:
                db_obj = ProposalScoreModel(
                    proposal_id=score.proposal_id,
                    cycle_id=score.cycle_id,
                    need_score=score.need_score,
                    affected_population_score=score.affected_population_score,
                    safety_impact_score=score.safety_impact_score,
                    recurrence_score=score.recurrence_score,
                    vulnerability_score=score.vulnerability_score,
                    community_support_score=score.community_support_score,
                    final_score=score.final_score,
                    score_breakdown_json=score.score_breakdown,
                )
                db.add(db_obj)
            else:
                db_obj.final_score = score.final_score
                db_obj.score_breakdown_json = score.score_breakdown
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        return score

    def get_score(self, proposal_id: str) -> Optional[ProposalScore]:
        return self._scores.get(proposal_id)

    def save_allocation(self, result: BudgetAllocationResult) -> BudgetAllocationResult:
        self._allocations[result.cycle_id] = result
        db = SessionLocal()
        try:
            db_obj = db.query(BudgetAllocationModel).filter_by(allocation_id=result.allocation_id).first()
            if not db_obj:
                db_obj = BudgetAllocationModel(
                    allocation_id=result.allocation_id,
                    cycle_id=result.cycle_id,
                    total_budget=result.total_budget,
                    allocated_budget=result.allocated_budget,
                    remaining_budget=result.remaining_budget,
                    selected_proposals_json=result.selected_proposals,
                    rejected_proposals_json=result.rejected_proposals,
                    decision_log_json=result.decision_log,
                )
                db.add(db_obj)
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        return result

    def get_allocation(self, cycle_id: str) -> Optional[BudgetAllocationResult]:
        alloc = self._allocations.get(cycle_id)
        if alloc:
            return alloc
        db = SessionLocal()
        try:
            db_obj = db.query(BudgetAllocationModel).filter_by(cycle_id=cycle_id).first()
            if db_obj:
                now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                alloc = BudgetAllocationResult(
                    allocation_id=db_obj.allocation_id,
                    cycle_id=db_obj.cycle_id,
                    total_budget=db_obj.total_budget,
                    allocated_budget=db_obj.allocated_budget,
                    remaining_budget=db_obj.remaining_budget,
                    selected_proposals=db_obj.selected_proposals_json or [],
                    rejected_proposals=db_obj.rejected_proposals_json or [],
                    decision_log=db_obj.decision_log_json or [],
                    allocated_at=db_obj.allocated_at.isoformat() if hasattr(db_obj.allocated_at, "isoformat") else str(db_obj.allocated_at or now_str),
                )
                self._allocations[cycle_id] = alloc
            return alloc
        except Exception:
            return None
        finally:
            db.close()


    def clear(self) -> None:
        self._scores.clear()
        self._allocations.clear()
        db = SessionLocal()
        try:
            db.query(BudgetAllocationModel).delete()
            db.query(ProposalScoreModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


allocation_store = AllocationStore()



class AllocationEngine:
    """Deterministic 6-Factor Proposal Scoring & 0/1 Knapsack Budget Allocation Engine with Explicit Tie-Breaking."""

    def calculate_proposal_score(self, proposal_id: str, cycle_id: str = "cycle_ward7_2027") -> ProposalScore:
        prop = proposal_store.get(proposal_id)
        if not prop:
            raise KeyError(f"Proposal '{proposal_id}' not found.")

        # 1. Civic Need (Weight 0.25): Average priority score of linked master issues
        priorities = [75.0]  # Baseline default
        m_issues = [master_issue_store.get(mid) for mid in prop.linked_master_issue_ids if master_issue_store.get(mid)]
        if m_issues:
            priorities = [float(m.severity_score * 20.0) for m in m_issues]
        raw_need = sum(priorities) / len(priorities)
        need_contrib = round(0.25 * raw_need, 2)

        # 2. Affected Citizens (Weight 0.20): Logarithmic report scaling
        total_reports = sum(m.citizen_reporter_count for m in m_issues) if m_issues else 1
        raw_citizens = min(100.0, math.log(total_reports + 1, 2) * 15.0)
        citizens_contrib = round(0.20 * raw_citizens, 2)

        # 3. Safety Impact (Weight 0.20): Safety risk prevalence
        safety_flagged = sum(1 for m in m_issues if m.severity_score >= 4) if m_issues else 0
        raw_safety = (float(safety_flagged) / max(len(m_issues), 1)) * 100.0 if m_issues else 50.0
        safety_contrib = round(0.20 * raw_safety, 2)

        # 4. Recurrence (Weight 0.15): Average reopening count
        reopen_counts = []
        for mid in prop.linked_master_issue_ids:
            lifecycle = escalation_store.get(mid)
            if lifecycle:
                reopen_counts.append(lifecycle.reopened_count)
        avg_reopen = (sum(reopen_counts) / max(len(reopen_counts), 1)) if reopen_counts else 0.0
        raw_recurrence = min(100.0, avg_reopen * 33.3)
        recurrence_contrib = round(0.15 * raw_recurrence, 2)

        # 5. Vulnerability Proximity (Weight 0.10): Static GIS vulnerability score
        raw_vulnerability = 60.0
        vulnerability_contrib = round(0.10 * raw_vulnerability, 2)

        # 6. Community Support (Weight 0.10): Election vote percentage
        all_cycle_votes = voting_store.list_by_cycle(cycle_id)
        total_votes = len(all_cycle_votes)
        prop_votes = sum(1 for v in all_cycle_votes if v.proposal_id == proposal_id)
        raw_support = (float(prop_votes) / max(total_votes, 1)) * 100.0 if total_votes > 0 else 0.0
        support_contrib = round(0.10 * raw_support, 2)

        final_score = round(
            need_contrib + citizens_contrib + safety_contrib + recurrence_contrib + vulnerability_contrib + support_contrib,
            2,
        )

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        score_record = ProposalScore(
            proposal_id=proposal_id,
            cycle_id=cycle_id,
            need_score=need_contrib,
            affected_population_score=citizens_contrib,
            safety_impact_score=safety_contrib,
            recurrence_score=recurrence_contrib,
            vulnerability_score=vulnerability_contrib,
            community_support_score=support_contrib,
            final_score=final_score,
            score_breakdown={
                "civic_need": {"weight": 0.25, "raw_val": raw_need, "contribution": need_contrib},
                "affected_citizens": {"weight": 0.20, "raw_val": raw_citizens, "contribution": citizens_contrib},
                "safety_impact": {"weight": 0.20, "raw_val": raw_safety, "contribution": safety_contrib},
                "recurrence": {"weight": 0.15, "raw_val": raw_recurrence, "contribution": recurrence_contrib},
                "vulnerability": {"weight": 0.10, "raw_val": raw_vulnerability, "contribution": vulnerability_contrib},
                "community_support": {"weight": 0.10, "raw_val": raw_support, "contribution": support_contrib},
            },
            calculated_at=now_str,
        )

        allocation_store.save_score(score_record)
        return score_record

    def run_budget_allocation(self, cycle_id: str = "cycle_ward7_2027") -> BudgetAllocationResult:
        cycle = finance_store.get_cycle(cycle_id)
        if not cycle:
            raise KeyError(f"Budget cycle '{cycle_id}' not found.")

        # Fetch eligible & voting proposals for jurisdiction
        proposals = [p for p in proposal_store.list_all(cycle.jurisdiction_id) if p.status in [ProposalStatus.ELIGIBLE, ProposalStatus.VOTING]]
        if not proposals:
            proposals = proposal_store.list_all()

        scored_proposals: List[Tuple[Any, ProposalScore]] = []
        for p in proposals:
            sc = self.calculate_proposal_score(p.proposal_id, cycle_id)
            scored_proposals.append((p, sc))

        # Deterministic 4-Tier Sorting & Tie-Breaking
        # 1. Final Score Descending
        # 2. Safety Score Descending
        # 3. Community Support Score Descending
        # 4. Need Score Descending
        sorted_candidates = sorted(
            scored_proposals,
            key=lambda x: (
                x[1].final_score,
                x[1].safety_impact_score,
                x[1].community_support_score,
                x[1].need_score,
            ),
            reverse=True,
        )

        total_budget = cycle.total_budget
        allocated_budget = 0.0
        selected_proposals = []
        rejected_proposals = []
        decision_log = []

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Deterministic Greedy Knapsack Selection
        for prop, sc in sorted_candidates:
            cost = prop.requested_budget
            if allocated_budget + cost <= total_budget:
                allocated_budget += cost
                prop.status = ProposalStatus.SELECTED
                proposal_store.save(prop)

                selected_info = {
                    "proposal_id": prop.proposal_id,
                    "title": prop.title,
                    "final_score": sc.final_score,
                    "requested_budget": cost,
                }
                selected_proposals.append(selected_info)
                decision_log.append(f"SELECTED proposal '{prop.proposal_id}' (Score {sc.final_score}, Cost ₹{cost:,.2f}). Remaining Budget: ₹{total_budget - allocated_budget:,.2f}")
            else:
                prop.status = ProposalStatus.REJECTED
                proposal_store.save(prop)

                rejected_info = {
                    "proposal_id": prop.proposal_id,
                    "title": prop.title,
                    "final_score": sc.final_score,
                    "requested_budget": cost,
                    "rejection_reason": "Budget Exhaustion",
                }
                rejected_proposals.append(rejected_info)
                decision_log.append(f"REJECTED proposal '{prop.proposal_id}' due to budget exhaustion (Cost ₹{cost:,.2f} exceeds remaining ₹{total_budget - allocated_budget:,.2f}).")

        remaining_budget = round(total_budget - allocated_budget, 2)
        cycle.status = "ALLOCATED"
        finance_store.save_cycle(cycle)

        result = BudgetAllocationResult(
            allocation_id=f"alloc_{uuid.uuid4().hex[:8]}",
            cycle_id=cycle_id,
            total_budget=total_budget,
            allocated_budget=round(allocated_budget, 2),
            remaining_budget=remaining_budget,
            selected_proposals=selected_proposals,
            rejected_proposals=rejected_proposals,
            decision_log=decision_log,
            allocated_at=now_str,
        )

        allocation_store.save_allocation(result)
        return result


allocation_engine = AllocationEngine()
