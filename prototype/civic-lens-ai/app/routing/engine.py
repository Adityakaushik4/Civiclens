import uuid
from datetime import datetime, timezone
from typing import Dict, Optional
from pydantic import BaseModel, Field
from app.taxonomy import Category
from app.priority.schemas import PriorityLevel
from app.routing.registry import department_registry, DepartmentMapping
from app.sla import SLASnapshot, sla_calculator


class RoutingRequest(BaseModel):
    issue_id: Optional[str] = Field(default=None, description="Complaint or Master Issue UUID")
    category: Category = Field(..., description="Issue category")
    subcategory: str = Field(..., description="Issue subcategory")
    priority_score: int = Field(..., ge=0, le=100, description="Priority score from Priority Engine")
    priority_level: PriorityLevel = Field(..., description="Priority level: CRITICAL, HIGH, MEDIUM, LOW")
    jurisdiction_id: Optional[str] = Field(default=None, description="Optional target municipal jurisdiction or city ID")


class RoutingDecisionResult(BaseModel):
    decision_id: str = Field(..., description="Unique Routing Decision UUID")
    issue_id: str = Field(..., description="Target Issue UUID")
    jurisdiction_id: Optional[str] = Field(default=None, description="Jurisdiction or city ID if specified")
    category: str
    subcategory: str
    priority_score: int
    priority_level: PriorityLevel
    primary_department: str
    responsible_unit: str
    escalation_department: str
    selection_reason: str
    routed_at: str
    sla: Optional[SLASnapshot] = Field(default=None, description="Structured SLA policy provenance and deadline snapshot")


from app.database.connection import SessionLocal
from app.database.models import RoutingDecisionModel


class RoutingStore:
    """Persistent database-backed store for Routing Decision records."""

    def __init__(self):
        self._decisions: Dict[str, RoutingDecisionResult] = {}

    def _sync_to_db(self, decision: RoutingDecisionResult):
        db = SessionLocal()
        try:
            cat_str = decision.category.value if hasattr(decision.category, "value") else str(decision.category)
            db_obj = db.query(RoutingDecisionModel).filter_by(decision_id=decision.decision_id).first()
            if not db_obj:
                db_obj = RoutingDecisionModel(
                    decision_id=decision.decision_id,
                    issue_id=decision.issue_id,
                    jurisdiction_id=decision.jurisdiction_id or "GLOBAL",
                    category=cat_str,
                    subcategory=decision.subcategory,
                    primary_department=decision.primary_department,
                    secondary_departments_json=[decision.responsible_unit],
                    routing_rule_id="RULE_DEFAULT",
                    routing_reasons_json=[decision.selection_reason],
                    confidence_score=1.0,
                )
                db.add(db_obj)
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def save(self, decision: RoutingDecisionResult) -> None:
        self._decisions[decision.issue_id] = decision
        self._sync_to_db(decision)

    def get(self, issue_id: str) -> Optional[RoutingDecisionResult]:
        dec = self._decisions.get(issue_id)
        if dec:
            return dec
        db = SessionLocal()
        try:
            db_obj = db.query(RoutingDecisionModel).filter_by(issue_id=issue_id).first()
            if db_obj:
                dec = RoutingDecisionResult(
                    decision_id=db_obj.decision_id,
                    issue_id=db_obj.issue_id,
                    jurisdiction_id=db_obj.jurisdiction_id,
                    category=db_obj.category,
                    subcategory=db_obj.subcategory,
                    priority_score=80,
                    priority_level=PriorityLevel.HIGH,
                    primary_department=db_obj.primary_department,
                    responsible_unit=db_obj.secondary_departments_json[0] if db_obj.secondary_departments_json else "Unit 1",
                    escalation_department="Municipal Supervisor Board",
                    selection_reason=db_obj.routing_reasons_json[0] if db_obj.routing_reasons_json else "Routed by category",
                    routed_at=db_obj.created_at.isoformat() if db_obj.created_at else datetime.now(timezone.utc).isoformat(),
                )
                self._decisions[issue_id] = dec
            return dec
        except Exception:
            return None
        finally:
            db.close()

    def clear(self) -> None:
        self._decisions.clear()
        db = SessionLocal()
        try:
            db.query(RoutingDecisionModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()



routing_store = RoutingStore()


class RoutingEngine:
    """Deterministic routing decision engine matching issues to departments/units."""

    def route_issue(self, request: RoutingRequest) -> RoutingDecisionResult:
        issue_id = request.issue_id or f"issue_{uuid.uuid4().hex[:8]}"
        decision_id = f"route_{uuid.uuid4().hex[:8]}"

        cat_str = request.category.value if isinstance(request.category, Category) else str(request.category)
        sub_str = request.subcategory

        mapping, reason = department_registry.resolve_routing(cat_str, sub_str)
        now_dt = datetime.now(timezone.utc)

        # Resolve SLA policy and snapshot
        pol = sla_calculator.resolve_policy(
            category=cat_str,
            subcategory=sub_str,
            priority_level=request.priority_level,
            jurisdiction_id=request.jurisdiction_id,
            request_time=now_dt,
        )
        sla_snapshot = sla_calculator.create_sla_snapshot(pol, now_dt) if pol else None

        result = RoutingDecisionResult(
            decision_id=decision_id,
            issue_id=issue_id,
            jurisdiction_id=request.jurisdiction_id,
            category=cat_str,
            subcategory=sub_str,
            priority_score=request.priority_score,
            priority_level=request.priority_level,
            primary_department=mapping.primary_department,
            responsible_unit=mapping.responsible_unit,
            escalation_department=mapping.escalation_department,
            selection_reason=reason,
            routed_at=now_dt.isoformat(),
            sla=sla_snapshot,
        )

        routing_store.save(result)
        return result


routing_engine = RoutingEngine()
