import uuid
import hashlib
import datetime
from typing import Dict, List, Optional
from app.proposals.schemas import (
    ProposalStatus,
    CitizenProposal,
    ProposalCreateRequest,
    ProposalUpdateRequest,
    ProposalEvidencePanel,
)
from app.duplicates import master_issue_store
from app.escalation import escalation_store
from app.rag import rag_generation_engine, GroundedQARequest


from app.database.connection import SessionLocal
from app.database.models import CitizenProposalModel, ProposalEvidencePanelModel


class ProposalStore:
    """Persistent database-backed store for Citizen Proposals and Evidence Panels."""

    def __init__(self):
        pass

    def _sync_proposal_to_db(self, proposal: CitizenProposal):
        db = SessionLocal()
        try:
            cat_str = proposal.category.value if hasattr(proposal.category, "value") else str(proposal.category)
            stat_str = proposal.status.value if hasattr(proposal.status, "value") else str(proposal.status)
            db_obj = db.query(CitizenProposalModel).filter_by(proposal_id=proposal.proposal_id).first()
            if not db_obj:
                db_obj = CitizenProposalModel(
                    proposal_id=proposal.proposal_id,
                    opportunity_id=proposal.opportunity_id,
                    jurisdiction_id=proposal.jurisdiction_id,
                    title=proposal.title,
                    description=proposal.description,
                    proposer_id_hash=proposal.proposer_id_hash,
                    category=cat_str,
                    requested_budget=proposal.requested_budget,
                    cost_status=proposal.cost_status,
                    linked_master_issue_ids_json=proposal.linked_master_issue_ids,
                    status=stat_str,
                    ai_generated_draft=proposal.ai_generated_draft,
                )
                db.add(db_obj)
            else:
                db_obj.opportunity_id = proposal.opportunity_id
                db_obj.jurisdiction_id = proposal.jurisdiction_id
                db_obj.title = proposal.title
                db_obj.description = proposal.description
                db_obj.proposer_id_hash = proposal.proposer_id_hash
                db_obj.category = cat_str
                db_obj.requested_budget = proposal.requested_budget
                db_obj.cost_status = proposal.cost_status
                db_obj.linked_master_issue_ids_json = proposal.linked_master_issue_ids
                db_obj.status = stat_str
                db_obj.ai_generated_draft = proposal.ai_generated_draft
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def save(self, proposal: CitizenProposal) -> CitizenProposal:
        self._sync_proposal_to_db(proposal)
        return proposal

    def get(self, proposal_id: str) -> Optional[CitizenProposal]:
        db = SessionLocal()
        try:
            db_obj = db.query(CitizenProposalModel).filter_by(proposal_id=proposal_id).first()
            if db_obj:
                now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                try:
                    st = ProposalStatus(db_obj.status)
                except Exception:
                    st = ProposalStatus.SUBMITTED
                prop = CitizenProposal(
                    proposal_id=db_obj.proposal_id,
                    opportunity_id=db_obj.opportunity_id,
                    jurisdiction_id=db_obj.jurisdiction_id,
                    title=db_obj.title,
                    description=db_obj.description,
                    proposer_id_hash=db_obj.proposer_id_hash,
                    category=db_obj.category,
                    requested_budget=db_obj.requested_budget,
                    cost_status=db_obj.cost_status,
                    linked_master_issue_ids=db_obj.linked_master_issue_ids_json or [],
                    status=st,
                    ai_generated_draft=db_obj.ai_generated_draft,
                    created_at=now_str,
                    updated_at=now_str,
                )
            return prop
        except Exception:
            return None
        finally:
            db.close()

    def list_all(self, jurisdiction_id: Optional[str] = None) -> List[CitizenProposal]:
        db = SessionLocal()
        try:
            query = db.query(CitizenProposalModel)
            if jurisdiction_id:
                query = query.filter_by(jurisdiction_id=jurisdiction_id)
            
            db_objs = query.all()
            results = []
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            for db_obj in db_objs:
                try:
                    st = ProposalStatus(db_obj.status)
                except Exception:
                    st = ProposalStatus.SUBMITTED
                prop = CitizenProposal(
                    proposal_id=db_obj.proposal_id,
                    opportunity_id=db_obj.opportunity_id,
                    jurisdiction_id=db_obj.jurisdiction_id,
                    title=db_obj.title,
                    description=db_obj.description,
                    proposer_id_hash=db_obj.proposer_id_hash,
                    category=db_obj.category,
                    requested_budget=db_obj.requested_budget,
                    cost_status=db_obj.cost_status,
                    linked_master_issue_ids=db_obj.linked_master_issue_ids_json or [],
                    status=st,
                    ai_generated_draft=db_obj.ai_generated_draft,
                    created_at=now_str,
                    updated_at=now_str,
                )
                results.append(prop)
            return results
        finally:
            db.close()


    def save_evidence_panel(self, panel: ProposalEvidencePanel) -> ProposalEvidencePanel:
        db = SessionLocal()
        try:
            db_obj = db.query(ProposalEvidencePanelModel).filter_by(proposal_id=panel.proposal_id).first()
            if not db_obj:
                db_obj = ProposalEvidencePanelModel(
                    proposal_id=panel.proposal_id,
                    linked_master_issues_json=panel.linked_master_issues if panel.linked_master_issues else [],
                    total_citizen_reports=panel.total_citizen_reports,
                    safety_risk_count=panel.safety_risk_count,
                    historical_reopening_avg=panel.historical_reopening_avg,
                    rag_citations_json=panel.rag_citations,
                )
                db.add(db_obj)
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        return panel

    def get_evidence_panel(self, proposal_id: str) -> Optional[ProposalEvidencePanel]:
        db = SessionLocal()
        try:
            db_obj = db.query(ProposalEvidencePanelModel).filter_by(proposal_id=proposal_id).first()
            if db_obj:
                return ProposalEvidencePanel(
                    proposal_id=db_obj.proposal_id,
                    linked_master_issues=db_obj.linked_master_issues_json or [],
                    total_citizen_reports=db_obj.total_citizen_reports,
                    safety_risk_count=db_obj.safety_risk_count,
                    historical_reopening_avg=db_obj.historical_reopening_avg,
                    rag_citations=db_obj.rag_citations_json or []
                )
            return None
        except Exception:
            return None
        finally:
            db.close()

    def clear(self) -> None:
        db = SessionLocal()
        try:
            db.query(ProposalEvidencePanelModel).delete()
            db.query(CitizenProposalModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


proposal_store = ProposalStore()



class ProposalEngine:
    """Engine managing citizen proposal creation, status state machine, and evidence panel generation."""

    def hash_identity(self, raw_id: str) -> str:
        return f"usr_{hashlib.sha256(raw_id.encode('utf-8')).hexdigest()[:12]}"

    def create_proposal(self, request: ProposalCreateRequest) -> CitizenProposal:
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        prop_id = f"prop_{uuid.uuid4().hex[:8]}"

        proposal = CitizenProposal(
            proposal_id=prop_id,
            opportunity_id=request.opportunity_id,
            jurisdiction_id=request.jurisdiction_id,
            title=request.title,
            description=request.description,
            proposer_id_hash=self.hash_identity(request.proposer_id),
            category=request.category,
            requested_budget=request.requested_budget,
            cost_status="ESTIMATED",
            linked_master_issue_ids=request.linked_master_issue_ids,
            status=ProposalStatus.SUBMITTED,
            ai_generated_draft=request.ai_generated_draft,
            created_at=now_str,
            updated_at=now_str,
        )

        proposal_store.save(proposal)
        self.generate_evidence_panel(prop_id)

        # Trigger eligibility evaluation automatically
        from app.finance.engine import finance_engine
        finance_engine.evaluate_eligibility(prop_id)

        return proposal_store.get(prop_id)

    def update_proposal(self, proposal_id: str, request: ProposalUpdateRequest) -> CitizenProposal:
        prop = proposal_store.get(proposal_id)
        if not prop:
            raise KeyError(f"Proposal '{proposal_id}' not found.")

        update_dict = request.model_dump(exclude_unset=True)

        if "status" in update_dict and update_dict["status"] in [ProposalStatus.ELIGIBLE, ProposalStatus.VOTING]:
            from app.finance.engine import finance_store
            eligibility = finance_store.get_eligibility(proposal_id)
            if not eligibility or not eligibility.is_eligible:
                raise ValueError("Cannot transition to ELIGIBLE or VOTING without a valid passed eligibility record.")

        update_dict["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        updated_prop = prop.model_copy(update=update_dict)
        proposal_store.save(updated_prop)

        if request.linked_master_issue_ids is not None:
            self.generate_evidence_panel(proposal_id)

        return updated_prop

    def generate_evidence_panel(self, proposal_id: str) -> ProposalEvidencePanel:
        prop = proposal_store.get(proposal_id)
        if not prop:
            raise KeyError(f"Proposal '{proposal_id}' not found.")

        linked_issues_data = []
        total_reports = 0
        safety_risks = 0
        reopen_counts = []

        for mid in prop.linked_master_issue_ids:
            mi = master_issue_store.get(mid)
            if mi:
                total_reports += mi.citizen_reporter_count
                lifecycle = escalation_store.get(mid)
                reopen_cnt = lifecycle.reopened_count if lifecycle else 0
                reopen_counts.append(reopen_cnt)

                issue_info = {
                    "master_issue_id": mi.id,
                    "title": mi.title,
                    "category": mi.category.value if hasattr(mi.category, "value") else str(mi.category),
                    "citizen_report_count": mi.citizen_reporter_count,
                    "severity_score": mi.severity_score,
                    "reopen_count": reopen_cnt,
                }
                linked_issues_data.append(issue_info)

        avg_reopen = round(sum(reopen_counts) / max(len(reopen_counts), 1), 2)

        # Grounded RAG Citation lookup
        rag_citations = []
        try:
            rag_res = rag_generation_engine.generate_grounded_answer(
                GroundedQARequest(query=f"Municipal policy and rate guidelines for {prop.category} infrastructure project")
            )
            rag_citations = [c.model_dump() for c in rag_res.citations]
        except Exception:
            pass

        panel = ProposalEvidencePanel(
            proposal_id=proposal_id,
            linked_master_issues=linked_issues_data,
            total_citizen_reports=total_reports,
            safety_risk_count=safety_risks,
            historical_reopening_avg=avg_reopen,
            rag_citations=rag_citations,
        )

        proposal_store.save_evidence_panel(panel)
        return panel


proposal_engine = ProposalEngine()
