import hashlib
import datetime
from typing import Dict, List, Optional
from app.opportunities.schemas import (
    CivicProjectOpportunity,
    AIDraftProposalRequest,
    AIDraftProposalResponse,
)
from app.analytics.hotspots import hotspot_engine, hotspot_store
from app.duplicates import master_issue_store
from app.llm import get_llm_provider


from app.database.connection import SessionLocal
from app.database.models import CivicProjectOpportunityModel


class OpportunityStore:
    """Persistent database-backed store for Civic Project Opportunities."""

    def __init__(self):
        self._opportunities: Dict[str, CivicProjectOpportunity] = {}

    def save(self, opportunity: CivicProjectOpportunity) -> CivicProjectOpportunity:
        self._opportunities[opportunity.opportunity_id] = opportunity
        db = SessionLocal()
        try:
            cat_str = opportunity.category.value if hasattr(opportunity.category, "value") else str(opportunity.category)
            db_obj = db.query(CivicProjectOpportunityModel).filter_by(opportunity_id=opportunity.opportunity_id).first()
            if not db_obj:
                db_obj = CivicProjectOpportunityModel(
                    opportunity_id=opportunity.opportunity_id,
                    jurisdiction_id=opportunity.jurisdiction_id,
                    title=opportunity.title,
                    category=cat_str,
                    hotspot_id=opportunity.hotspot_id,
                    linked_master_issue_ids_json=opportunity.linked_master_issue_ids,
                    total_citizen_reports=opportunity.total_citizen_reports,
                    estimated_priority_avg=opportunity.estimated_priority_avg,
                    status=opportunity.status,
                )
                db.add(db_obj)
            else:
                db_obj.title = opportunity.title
                db_obj.category = cat_str
                db_obj.linked_master_issue_ids_json = opportunity.linked_master_issue_ids
                db_obj.total_citizen_reports = opportunity.total_citizen_reports
                db_obj.estimated_priority_avg = opportunity.estimated_priority_avg
                db_obj.status = opportunity.status

            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        return opportunity

    def get(self, opportunity_id: str) -> Optional[CivicProjectOpportunity]:
        return self._opportunities.get(opportunity_id)

    def list_all(self, jurisdiction_id: Optional[str] = None) -> List[CivicProjectOpportunity]:
        if jurisdiction_id:
            return [o for o in self._opportunities.values() if not o.jurisdiction_id or o.jurisdiction_id == jurisdiction_id]
        return list(self._opportunities.values())

    def clear(self) -> None:
        self._opportunities.clear()
        db = SessionLocal()
        try:
            db.query(CivicProjectOpportunityModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


opportunity_store = OpportunityStore()



CATEGORY_DEPARTMENT_MAP = {
    "ROAD_DAMAGE": "Roads & PWD",
    "GARBAGE": "Sanitation & Waste Management",
    "DRAINAGE": "Drainage & Sewerage",
    "STREETLIGHT": "Electrical / Street Lighting",
}


class OpportunityEngine:
    """Engine detecting civic project opportunities from hotspots and generating AI draft proposals."""

    def detect_opportunities(self, jurisdiction_id: Optional[str] = None) -> List[CivicProjectOpportunity]:
        hotspots = hotspot_store.list_all(jurisdiction_id)
        if not hotspots:
            hotspots = hotspot_engine.detect_hotspots(jurisdiction_id=jurisdiction_id)

        detected_opps: List[CivicProjectOpportunity] = []
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for hs in hotspots:
            stable_hash = hashlib.md5(hs.hotspot_id.encode()).hexdigest()[:8]
            opp_id = f"opp_{stable_hash}"
            title = f"{hs.category.title()} Rehabilitation & Infrastructure Project ({hs.ward_name})"

            dept = None
            if hs.linked_master_issue_ids:
                first_mi = master_issue_store.get(hs.linked_master_issue_ids[0])
                if first_mi:
                    dept = getattr(first_mi, "department", None) or getattr(first_mi, "assigned_department", None)
            if not dept:
                dept = CATEGORY_DEPARTMENT_MAP.get(hs.category.upper(), "Municipal Services")

            opp = CivicProjectOpportunity(
                opportunity_id=opp_id,
                jurisdiction_id=jurisdiction_id or hs.jurisdiction_id,
                title=title,
                category=hs.category,
                department=dept,
                suggested_budget=None,  # Preserved as None if no formal cost estimate has been generated
                hotspot_id=hs.hotspot_id,
                linked_master_issue_ids=hs.linked_master_issue_ids,
                total_citizen_reports=hs.citizen_report_count,
                estimated_priority_avg=hs.severity_score_weighted * 15.0,  # Normalized Priority Estimate
                status="DETECTED",
                created_at=now_str,
            )

            opportunity_store.save(opp)
            detected_opps.append(opp)

        return detected_opps

    def generate_ai_draft_proposal(self, request: AIDraftProposalRequest) -> AIDraftProposalResponse:
        opp = opportunity_store.get(request.opportunity_id)
        if not opp:
            raise ValueError(f"Project opportunity '{request.opportunity_id}' not found.")

        # Gather evidence facts
        master_issues = [master_issue_store.get(mid) for mid in opp.linked_master_issue_ids if master_issue_store.get(mid)]
        reports_count = sum(m.citizen_reporter_count for m in master_issues) if master_issues else opp.total_citizen_reports

        suggested_title = f"Public Infrastructure Improvement: {opp.title}"
        suggested_description = (
            f"This proposal addresses recurring {opp.category} issues across {len(opp.linked_master_issue_ids)} Master Issues "
            f"supported by {reports_count} citizen reports. Objective: Comprehensive repair and upgrade of infrastructure corridor."
        )

        return AIDraftProposalResponse(
            opportunity_id=opp.opportunity_id,
            suggested_title=suggested_title,
            suggested_description=suggested_description,
            linked_master_issue_ids=opp.linked_master_issue_ids,
            total_citizen_reports=reports_count,
            ai_disclaimer="AI-assisted draft. Statistics and evidence cited from Master Issues. Financial costs and government approval are NOT calculated by AI.",
            ai_generated_draft=True,
        )


opportunity_engine = OpportunityEngine()
