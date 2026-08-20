import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ReopenPolicy(BaseModel):
    policy_id: str
    jurisdiction_id: Optional[str] = Field(default=None, description="Nullable for global default policy")
    enabled: bool = Field(default=True, description="Whether auto-escalation on reopen is enabled")
    reopen_threshold: int = Field(default=3, ge=1, description="Reopen count threshold to trigger auto-escalation")
    escalation_target: Optional[str] = Field(default=None, description="Custom target department or null to fallback to issue default")
    status: str = Field(default="PROVISIONAL", description="PROVISIONAL or AUTHORITATIVE")
    source_reference: Optional[str] = Field(default=None, description="Reference source if authoritative")
    source_title: Optional[str] = Field(default=None, description="Title of municipal policy")
    effective_from: Optional[str] = Field(default=None, description="ISO timestamp effective start")
    effective_until: Optional[str] = Field(default=None, description="ISO timestamp effective end")
    created_at: str
    updated_at: str
    active: bool = Field(default=True, description="Active status for soft deletion")


class ReopenPolicyCreateRequest(BaseModel):
    policy_id: Optional[str] = Field(default=None, description="Optional custom policy ID")
    jurisdiction_id: Optional[str] = Field(default=None, description="Target jurisdiction ID")
    enabled: bool = Field(default=True, description="Whether policy is enabled")
    reopen_threshold: int = Field(default=3, ge=1, description="Threshold count for auto-escalation")
    escalation_target: Optional[str] = Field(default=None, description="Optional target department")
    status: str = Field(default="PROVISIONAL", description="PROVISIONAL or AUTHORITATIVE")
    source_reference: Optional[str] = Field(default=None, description="Reference source if authoritative")
    source_title: Optional[str] = Field(default=None, description="Title of policy")


class ReopenPolicyUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    reopen_threshold: Optional[int] = None
    escalation_target: Optional[str] = None
    status: Optional[str] = None
    source_reference: Optional[str] = None
    source_title: Optional[str] = None


from app.database.connection import SessionLocal
from app.database.models import ReopenPolicyModel, ReopenIdempotencyModel


class ReopenPolicyStore:
    """Persistent database-backed store for Reopen Escalation Policies."""

    def __init__(self):
        self._policies: Dict[str, ReopenPolicy] = {}
        self._seed_default_policy()

    def _seed_default_policy(self) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        default_policy = ReopenPolicy(
            policy_id="reopen_pol_default",
            jurisdiction_id=None,
            enabled=True,
            reopen_threshold=3,
            escalation_target=None,
            status="PROVISIONAL",
            source_reference="CIVIC-LENS-PROVISIONAL-REOPEN-V1",
            source_title="Provisional Municipal Reopen Threshold Policy (3 Reopenings)",
            created_at=now_str,
            updated_at=now_str,
            active=True,
        )
        self.save(default_policy)

    def save(self, policy: ReopenPolicy) -> ReopenPolicy:
        self._policies[policy.policy_id] = policy
        db = SessionLocal()
        try:
            db_obj = db.query(ReopenPolicyModel).filter_by(policy_id=policy.policy_id).first()
            if not db_obj:
                eff_dt = datetime.fromisoformat(policy.effective_from) if policy.effective_from else None
                db_obj = ReopenPolicyModel(
                    policy_id=policy.policy_id,
                    jurisdiction_id=policy.jurisdiction_id,
                    category="ALL",
                    reopen_threshold=policy.reopen_threshold,
                    status=policy.status,
                    effective_from=eff_dt,
                )
                db.add(db_obj)
            else:
                db_obj.reopen_threshold = policy.reopen_threshold
                db_obj.status = policy.status
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        return policy

    def get(self, policy_id: str) -> Optional[ReopenPolicy]:
        pol = self._policies.get(policy_id)
        if pol and pol.active:
            return pol
        return None

    def list_all(self) -> List[ReopenPolicy]:
        return [p for p in self._policies.values() if p.active]

    def delete(self, policy_id: str) -> ReopenPolicy:
        pol = self._policies.get(policy_id)
        if not pol or not pol.active:
            raise KeyError(f"Reopen policy '{policy_id}' not found.")
        pol.active = False
        pol.enabled = False
        pol.updated_at = datetime.now(timezone.utc).isoformat()
        self._policies[policy_id] = pol
        return pol

    def resolve_policy(self, jurisdiction_id: Optional[str] = None) -> Optional[ReopenPolicy]:
        """Resolves active reopen policy with deterministic precedence: Jurisdiction -> Global."""
        active_policies = [p for p in self._policies.values() if p.active and p.enabled]

        if jurisdiction_id:
            j_matches = [p for p in active_policies if p.jurisdiction_id == jurisdiction_id]
            if j_matches:
                return j_matches[0]

        g_matches = [p for p in active_policies if not p.jurisdiction_id or p.jurisdiction_id == "*"]
        if g_matches:
            return g_matches[0]

        return None

    def reset_to_defaults(self) -> None:
        self._policies.clear()
        self._seed_default_policy()


reopen_policy_store = ReopenPolicyStore()


class ReopenIdempotencyStore:
    """Persistent database-backed store caching processed reopen operations by (issue_id, idempotency_key)."""

    def __init__(self):
        self._cache: Dict[str, Dict] = {}

    def get(self, issue_id: str, idempotency_key: str) -> Optional[Dict]:
        cache_key = f"{issue_id}:{idempotency_key}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        db = SessionLocal()
        try:
            db_obj = db.query(ReopenIdempotencyModel).filter_by(issue_id=issue_id, idempotency_key=idempotency_key).first()
            if db_obj:
                cached = db_obj.replay_response_json
                self._cache[cache_key] = cached
            return cached
        except Exception:
            return None
        finally:
            db.close()

    def save(self, issue_id: str, idempotency_key: str, result_dict: Dict) -> None:
        cache_key = f"{issue_id}:{idempotency_key}"
        self._cache[cache_key] = result_dict
        db = SessionLocal()
        try:
            db_obj = db.query(ReopenIdempotencyModel).filter_by(issue_id=issue_id, idempotency_key=idempotency_key).first()
            if not db_obj:
                db_obj = ReopenIdempotencyModel(
                    issue_id=issue_id,
                    idempotency_key=idempotency_key,
                    replay_response_json=result_dict,
                )
                db.add(db_obj)
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def clear(self) -> None:
        self._cache.clear()
        db = SessionLocal()
        try:
            db.query(ReopenIdempotencyModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


reopen_idempotency_store = ReopenIdempotencyStore()

