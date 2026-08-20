import uuid
import json
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.routing.engine import routing_store, RoutingDecisionResult
from app.sla import SLASnapshot, sla_calculator, SLAPolicy
from app.escalation.policy import reopen_policy_store, reopen_idempotency_store



class IssueStatus(str, Enum):
    REGISTERED = "REGISTERED"
    ROUTED = "ROUTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_VERIFICATION = "AWAITING_VERIFICATION"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"
    OVERDUE = "OVERDUE"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class ActorType(str, Enum):
    SYSTEM = "SYSTEM"
    OPERATOR = "OPERATOR"
    SUPERVISOR = "SUPERVISOR"
    CITIZEN = "CITIZEN"


class EscalationReason(str, Enum):
    SLA_BREACH_ACK = "SLA_BREACH_ACK"
    SLA_BREACH_RES = "SLA_BREACH_RES"
    MANUAL_REASSIGNMENT = "MANUAL_REASSIGNMENT"
    OPERATOR_ESCALATED = "OPERATOR_ESCALATED"
    REOPEN_THRESHOLD_EXCEEDED = "REOPEN_THRESHOLD_EXCEEDED"


class StatusHistory(BaseModel):
    history_id: str
    issue_id: str
    from_status: IssueStatus
    to_status: IssueStatus
    changed_by: str
    actor_type: ActorType = Field(default=ActorType.OPERATOR, description="SYSTEM, OPERATOR, SUPERVISOR, CITIZEN")
    actor_id: str = Field(default="system", description="Explicit actor identity")
    notes: Optional[str] = None
    changed_at: str


class EscalationLog(BaseModel):
    escalation_id: str
    issue_id: str
    previous_department: str
    escalated_to_department: str
    reason: EscalationReason
    operator_id: Optional[str] = None
    actor_type: ActorType = Field(default=ActorType.SYSTEM, description="SYSTEM, OPERATOR, SUPERVISOR, CITIZEN")
    actor_id: str = Field(default="SYSTEM_ESCALATION_ENGINE", description="Explicit actor identity")
    reopen_count: Optional[int] = Field(default=None, description="Reopen count at time of auto-escalation")
    escalated_at: str
    notes: Optional[str] = None


class IssueLifecycleRecord(BaseModel):
    issue_id: str
    jurisdiction_id: Optional[str] = Field(default=None)
    current_status: IssueStatus
    current_department: str
    responsible_unit: str
    escalation_department: str
    routed_at: str
    acknowledgement_deadline: str
    resolution_deadline: str
    sla: Optional[SLASnapshot] = Field(default=None, description="Structured SLA policy provenance and snapshot")
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    assigned_operator_id: Optional[str] = None
    work_started_at: Optional[str] = None
    completion_submitted_at: Optional[str] = None
    resolved_at: Optional[str] = None
    reopened_count: int = Field(default=0, description="Total times issue was reopened")
    idempotency_replay: bool = Field(default=False, description="True if response was served from idempotency cache")
    is_overdue: bool = False
    status_history: List[StatusHistory] = Field(default_factory=list)
    escalation_logs: List[EscalationLog] = Field(default_factory=list)



from app.database.connection import SessionLocal
from app.database.models import IssueLifecycleModel as DBIssueLifecycleModel


class EscalationStore:
    """Persistent database-backed store for Issue Lifecycle, Status History, and Escalations."""

    def __init__(self):
        self._records: Dict[str, IssueLifecycleRecord] = {}

    def _sync_to_db(self, record: IssueLifecycleRecord):
        db = SessionLocal()
        try:
            curr_stat = record.current_status.value if hasattr(record.current_status, "value") else str(record.current_status)
            db_obj = db.query(DBIssueLifecycleModel).filter_by(issue_id=record.issue_id).first()
            sla_val = record.sla.model_dump() if hasattr(record.sla, "model_dump") else record.sla
            if not db_obj:
                db_obj = DBIssueLifecycleModel(
                    issue_id=record.issue_id,
                    current_status=curr_stat,
                    current_department=record.current_department,
                    jurisdiction_id=record.jurisdiction_id or "GLOBAL",
                    reopened_count=record.reopened_count,
                    is_overdue=record.is_overdue,
                    sla_snapshot_json=sla_val,
                    status_history_json=[h.model_dump() for h in record.status_history] if record.status_history else [],
                    escalation_history_json=[e.model_dump() for e in record.escalation_logs] if record.escalation_logs else [],
                    idempotency_replay=record.idempotency_replay,
                )
                db.add(db_obj)
            else:
                db_obj.current_status = curr_stat
                db_obj.current_department = record.current_department
                db_obj.jurisdiction_id = record.jurisdiction_id or "GLOBAL"

                db_obj.reopened_count = record.reopened_count
                db_obj.is_overdue = record.is_overdue
                db_obj.sla_snapshot_json = sla_val
                db_obj.status_history_json = [h.model_dump() for h in record.status_history] if record.status_history else []
                db_obj.escalation_history_json = [e.model_dump() for e in record.escalation_logs] if record.escalation_logs else []
                db_obj.idempotency_replay = record.idempotency_replay
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"\n[EscalationStore DB Error]: {e}\n")
        finally:
            db.close()


    def save(self, record: IssueLifecycleRecord) -> None:
        self._records[record.issue_id] = record
        self._sync_to_db(record)

    def get(self, issue_id: str) -> Optional[IssueLifecycleRecord]:
        rec = self._records.get(issue_id)
        if rec:
            return rec
        db = SessionLocal()
        try:
            db_obj = db.query(DBIssueLifecycleModel).filter_by(issue_id=issue_id).first()
            if db_obj:
                now_str = datetime.now(timezone.utc).isoformat()

                rec = IssueLifecycleRecord.model_validate({
                    "issue_id": db_obj.issue_id,
                    "current_status": db_obj.current_status,
                    "current_department": db_obj.current_department,
                    "responsible_unit": getattr(db_obj, "responsible_unit", "Unit 1") or "Unit 1",
                    "escalation_department": getattr(db_obj, "escalation_department", "Board") or "Board",
                    "routed_at": getattr(db_obj, "routed_at", now_str) or now_str,
                    "acknowledgement_deadline": getattr(db_obj, "acknowledgement_deadline", now_str) or now_str,
                    "resolution_deadline": getattr(db_obj, "resolution_deadline", now_str) or now_str,
                    "jurisdiction_id": db_obj.jurisdiction_id,
                    "reopened_count": db_obj.reopened_count,
                    "is_overdue": db_obj.is_overdue,
                    "sla": json.loads(db_obj.sla_snapshot_json) if isinstance(db_obj.sla_snapshot_json, str) else db_obj.sla_snapshot_json,
                    "status_history": json.loads(db_obj.status_history_json) if isinstance(db_obj.status_history_json, str) else (db_obj.status_history_json or []),
                    "escalation_logs": json.loads(db_obj.escalation_history_json) if isinstance(db_obj.escalation_history_json, str) else (db_obj.escalation_history_json or []),
                    "idempotency_replay": db_obj.idempotency_replay,
                })
                self._records[rec.issue_id] = rec
            return rec
        except Exception as e:
            print(f"\n[EscalationStore.get Error]: {e}\n")
            return None
        finally:
            db.close()


    def clear(self) -> None:
        self._records.clear()
        db = SessionLocal()
        try:
            db.query(DBIssueLifecycleModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()



escalation_store = EscalationStore()



class EscalationStateMachine:
    """State machine governing issue acknowledgment, status transitions, SLA breach checks, and escalation."""

    VALID_TRANSITIONS: Dict[IssueStatus, List[IssueStatus]] = {
        IssueStatus.REGISTERED: [IssueStatus.ROUTED],
        IssueStatus.ROUTED: [IssueStatus.ACKNOWLEDGED, IssueStatus.OVERDUE, IssueStatus.ESCALATED],
        IssueStatus.ACKNOWLEDGED: [IssueStatus.IN_PROGRESS, IssueStatus.OVERDUE, IssueStatus.ESCALATED],
        IssueStatus.IN_PROGRESS: [IssueStatus.AWAITING_VERIFICATION, IssueStatus.RESOLVED, IssueStatus.OVERDUE, IssueStatus.ESCALATED],
        IssueStatus.AWAITING_VERIFICATION: [IssueStatus.RESOLVED, IssueStatus.REOPENED, IssueStatus.OVERDUE, IssueStatus.ESCALATED],
        IssueStatus.RESOLVED: [IssueStatus.CLOSED, IssueStatus.REOPENED],
        IssueStatus.REOPENED: [IssueStatus.ACKNOWLEDGED, IssueStatus.IN_PROGRESS, IssueStatus.OVERDUE, IssueStatus.ESCALATED],
        IssueStatus.OVERDUE: [IssueStatus.ESCALATED, IssueStatus.IN_PROGRESS, IssueStatus.AWAITING_VERIFICATION, IssueStatus.RESOLVED, IssueStatus.REOPENED],
        IssueStatus.ESCALATED: [IssueStatus.ACKNOWLEDGED, IssueStatus.IN_PROGRESS, IssueStatus.AWAITING_VERIFICATION, IssueStatus.RESOLVED, IssueStatus.REOPENED],
        IssueStatus.CLOSED: [],
    }


    def initialize_lifecycle(
        self, routing_decision: RoutingDecisionResult
    ) -> IssueLifecycleRecord:
        routed_dt = datetime.fromisoformat(routing_decision.routed_at)

        if routing_decision.sla:
            sla_snapshot = routing_decision.sla
            ack_deadline_str = sla_snapshot.acknowledgement_deadline
            res_deadline_str = sla_snapshot.resolution_deadline
        else:
            pol = sla_calculator.resolve_policy(
                routing_decision.category,
                routing_decision.subcategory,
                routing_decision.priority_level,
                routing_decision.jurisdiction_id,
                routed_dt,
            )
            if pol:
                sla_snapshot = sla_calculator.create_sla_snapshot(pol, routed_dt)
                ack_deadline_str = sla_snapshot.acknowledgement_deadline
                res_deadline_str = sla_snapshot.resolution_deadline
            else:
                sla_snapshot = None
                ack_deadline_str = routed_dt.isoformat()
                res_deadline_str = routed_dt.isoformat()

        history_entry = StatusHistory(
            history_id=f"hist_{uuid.uuid4().hex[:8]}",
            issue_id=routing_decision.issue_id,
            from_status=IssueStatus.REGISTERED,
            to_status=IssueStatus.ROUTED,
            changed_by="system_router",
            notes=f"Routed to primary department '{routing_decision.primary_department}'",
            changed_at=datetime.now(timezone.utc).isoformat(),
        )

        record = IssueLifecycleRecord(
            issue_id=routing_decision.issue_id,
            jurisdiction_id=routing_decision.jurisdiction_id,
            current_status=IssueStatus.ROUTED,
            current_department=routing_decision.primary_department,
            responsible_unit=routing_decision.responsible_unit,
            escalation_department=routing_decision.escalation_department,
            routed_at=routing_decision.routed_at,
            acknowledgement_deadline=ack_deadline_str,
            resolution_deadline=res_deadline_str,
            sla=sla_snapshot,
            status_history=[history_entry],
        )

        escalation_store.save(record)
        return record

    def acknowledge_issue(
        self, issue_id: str, operator_id: str = "operator_1", notes: Optional[str] = None
    ) -> IssueLifecycleRecord:
        record = escalation_store.get(issue_id)
        if not record:
            raise ValueError(f"Issue lifecycle record for '{issue_id}' not found.")

        now_str = datetime.now(timezone.utc).isoformat()
        old_status = record.current_status
        if IssueStatus.ACKNOWLEDGED not in self.VALID_TRANSITIONS.get(old_status, []):
            raise ValueError(f"Invalid transition from {old_status} to IssueStatus.ACKNOWLEDGED")
        record.current_status = IssueStatus.ACKNOWLEDGED
        record.acknowledged_at = now_str
        record.acknowledged_by = operator_id

        history_entry = StatusHistory(
            history_id=f"hist_{uuid.uuid4().hex[:8]}",
            issue_id=issue_id,
            from_status=old_status,
            to_status=IssueStatus.ACKNOWLEDGED,
            changed_by=operator_id,
            notes=notes or f"Acknowledged by operator '{operator_id}'",
            changed_at=now_str,
        )
        record.status_history.append(history_entry)
        escalation_store.save(record)
        return record

    def escalate_issue(
        self,
        issue_id: str,
        target_department: Optional[str] = None,
        reason: EscalationReason = EscalationReason.OPERATOR_ESCALATED,
        operator_id: Optional[str] = "system_supervisor",
        notes: Optional[str] = None,
    ) -> IssueLifecycleRecord:
        record = escalation_store.get(issue_id)
        if not record:
            raise ValueError(f"Issue lifecycle record for '{issue_id}' not found.")

        new_dept = target_department or record.escalation_department
        prev_dept = record.current_department
        now_str = datetime.now(timezone.utc).isoformat()

        old_status = record.current_status
        record.current_status = IssueStatus.ESCALATED
        record.current_department = new_dept
        record.is_overdue = True

        esc_log = EscalationLog(
            escalation_id=f"esc_{uuid.uuid4().hex[:8]}",
            issue_id=issue_id,
            previous_department=prev_dept,
            escalated_to_department=new_dept,
            reason=reason,
            operator_id=operator_id,
            escalated_at=now_str,
            notes=notes or f"Escalated from '{prev_dept}' to '{new_dept}' due to {reason.value}",
        )
        record.escalation_logs.append(esc_log)

        history_entry = StatusHistory(
            history_id=f"hist_{uuid.uuid4().hex[:8]}",
            issue_id=issue_id,
            from_status=old_status,
            to_status=IssueStatus.ESCALATED,
            changed_by=operator_id or "system",
            notes=notes or f"Issue escalated to '{new_dept}'",
            changed_at=now_str,
        )
        record.status_history.append(history_entry)

        escalation_store.save(record)
        return record

    def check_and_apply_sla_breach(self, issue_id: str, current_time: Optional[datetime] = None) -> IssueLifecycleRecord:
        record = escalation_store.get(issue_id)
        if not record:
            raise ValueError(f"Issue lifecycle record for '{issue_id}' not found.")

        now_dt = current_time or datetime.now(timezone.utc)
        ack_deadline_dt = datetime.fromisoformat(record.acknowledgement_deadline)
        res_deadline_dt = datetime.fromisoformat(record.resolution_deadline)

        # Check Acknowledgement Breach
        if record.current_status == IssueStatus.ROUTED and now_dt > ack_deadline_dt:
            return self.escalate_issue(
                issue_id=issue_id,
                reason=EscalationReason.SLA_BREACH_ACK,
                notes=f"Response SLA breached. Acknowledgement deadline was {record.acknowledgement_deadline}",
            )

        # Check Resolution Breach
        if record.current_status in [IssueStatus.ACKNOWLEDGED, IssueStatus.IN_PROGRESS, IssueStatus.AWAITING_VERIFICATION] and now_dt > res_deadline_dt:
            return self.escalate_issue(
                issue_id=issue_id,
                reason=EscalationReason.SLA_BREACH_RES,
                notes=f"Resolution SLA breached. Resolution deadline was {record.resolution_deadline}",
            )

        return record

    def start_work(
        self, issue_id: str, operator_id: str = "operator_1", notes: Optional[str] = None
    ) -> IssueLifecycleRecord:
        record = escalation_store.get(issue_id)
        if not record:
            raise ValueError(f"Issue lifecycle record for '{issue_id}' not found.")

        now_str = datetime.now(timezone.utc).isoformat()
        old_status = record.current_status
        if IssueStatus.IN_PROGRESS not in self.VALID_TRANSITIONS.get(old_status, []):
            raise ValueError(f"Invalid transition from {old_status} to IssueStatus.IN_PROGRESS")
        record.current_status = IssueStatus.IN_PROGRESS
        record.work_started_at = now_str
        record.assigned_operator_id = operator_id

        history_entry = StatusHistory(
            history_id=f"hist_{uuid.uuid4().hex[:8]}",
            issue_id=issue_id,
            from_status=old_status,
            to_status=IssueStatus.IN_PROGRESS,
            changed_by=operator_id,
            notes=notes or f"Field work started by operator '{operator_id}'",
            changed_at=now_str,
        )
        record.status_history.append(history_entry)
        escalation_store.save(record)
        return record

    def submit_completion(
        self, issue_id: str, operator_id: str = "operator_1", notes: Optional[str] = None
    ) -> IssueLifecycleRecord:
        record = escalation_store.get(issue_id)
        if not record:
            raise ValueError(f"Issue lifecycle record for '{issue_id}' not found.")

        now_str = datetime.now(timezone.utc).isoformat()
        old_status = record.current_status
        if IssueStatus.AWAITING_VERIFICATION not in self.VALID_TRANSITIONS.get(old_status, []):
            raise ValueError(f"Invalid transition from {old_status} to IssueStatus.AWAITING_VERIFICATION")
        record.current_status = IssueStatus.AWAITING_VERIFICATION
        record.completion_submitted_at = now_str

        history_entry = StatusHistory(
            history_id=f"hist_{uuid.uuid4().hex[:8]}",
            issue_id=issue_id,
            from_status=old_status,
            to_status=IssueStatus.AWAITING_VERIFICATION,
            changed_by=operator_id,
            notes=notes or f"Resolution completion submitted by operator '{operator_id}'. Pending verifier review.",
            changed_at=now_str,
        )
        record.status_history.append(history_entry)
        escalation_store.save(record)
        return record

    def resolve_issue(
        self, issue_id: str, verifier_id: str = "verifier_1", notes: Optional[str] = None
    ) -> IssueLifecycleRecord:
        record = escalation_store.get(issue_id)
        if not record:
            raise ValueError(f"Issue lifecycle record for '{issue_id}' not found.")

        now_str = datetime.now(timezone.utc).isoformat()
        old_status = record.current_status
        record.current_status = IssueStatus.RESOLVED
        record.resolved_at = now_str

        history_entry = StatusHistory(
            history_id=f"hist_{uuid.uuid4().hex[:8]}",
            issue_id=issue_id,
            from_status=old_status,
            to_status=IssueStatus.RESOLVED,
            changed_by=verifier_id,
            notes=notes or f"Resolution verified and approved by '{verifier_id}'",
            changed_at=now_str,
        )
        record.status_history.append(history_entry)
        escalation_store.save(record)
        return record

    def reopen_issue(
        self,
        issue_id: str,
        actor_id: str = "citizen_1",
        reason: str = "Dissatisfied with work",
        notes: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> IssueLifecycleRecord:
        record = escalation_store.get(issue_id)
        if not record:
            raise ValueError(f"Issue lifecycle record for '{issue_id}' not found.")

        # Idempotency check
        if idempotency_key:
            cached_data = reopen_idempotency_store.get(issue_id, idempotency_key)
            if cached_data:
                cached_record = IssueLifecycleRecord.model_validate(cached_data)
                cached_record.idempotency_replay = True
                return cached_record

        now_str = datetime.now(timezone.utc).isoformat()
        old_status = record.current_status
        record.current_status = IssueStatus.REOPENED
        record.reopened_count += 1
        record.idempotency_replay = False

        # Determine actor type safely
        actor_clean = (actor_id or "").lower()
        if actor_clean.startswith("system") or actor_clean == "system_escalation_engine":
            act_type = ActorType.SYSTEM
        elif "supervisor" in actor_clean or "verifier" in actor_clean:
            act_type = ActorType.SUPERVISOR
        elif "operator" in actor_clean or "crew" in actor_clean:
            act_type = ActorType.OPERATOR
        else:
            act_type = ActorType.CITIZEN

        history_entry = StatusHistory(
            history_id=f"hist_{uuid.uuid4().hex[:8]}",
            issue_id=issue_id,
            from_status=old_status,
            to_status=IssueStatus.REOPENED,
            changed_by=actor_id,
            actor_type=act_type,
            actor_id=actor_id,
            notes=notes or f"Issue reopened by '{actor_id}': {reason}",
            changed_at=now_str,
        )
        record.status_history.append(history_entry)

        # Configurable Reopen Policy Evaluation
        policy = reopen_policy_store.resolve_policy(record.jurisdiction_id)
        if policy and policy.enabled and record.reopened_count >= policy.reopen_threshold:
            target_dept = policy.escalation_target or record.escalation_department
            prev_dept = record.current_department

            esc_log = EscalationLog(
                escalation_id=f"esc_{uuid.uuid4().hex[:8]}",
                issue_id=issue_id,
                previous_department=prev_dept,
                escalated_to_department=target_dept,
                reason=EscalationReason.REOPEN_THRESHOLD_EXCEEDED,
                operator_id="SYSTEM_ESCALATION_ENGINE",
                actor_type=ActorType.SYSTEM,
                actor_id="SYSTEM_ESCALATION_ENGINE",
                reopen_count=record.reopened_count,
                escalated_at=now_str,
                notes=f"Auto-escalated: Reopen threshold ({policy.reopen_threshold}) reached at count {record.reopened_count}.",
            )
            record.escalation_logs.append(esc_log)
            record.current_department = target_dept
            record.is_overdue = True
            # Preserves record.sla snapshot completely unchanged!

        escalation_store.save(record)

        if idempotency_key:
            reopen_idempotency_store.save(issue_id, idempotency_key, record.model_dump())

        return record



escalation_state_machine = EscalationStateMachine()

