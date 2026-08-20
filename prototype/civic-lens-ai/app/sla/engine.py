import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from app.priority.schemas import PriorityLevel
from app.taxonomy import Category
from app.sla.schemas import (
    SLAPolicy,
    SLAPolicyStatus,
    SLAPolicyCreateRequest,
    SLAPolicyUpdateRequest,
    SLASnapshot,
)


from app.database.connection import SessionLocal
from app.database.models import SLAPolicyModel


class NoMatchingSLAPolicyError(Exception):
    """Raised when no matching active SLA policy exists for an issue."""
    pass


class SLAPolicyStore:
    """Persistent database-backed store managing configurable SLA Policies."""

    def __init__(self):
        self._policies: Dict[str, SLAPolicy] = {}
        self.seed_default_policies()

    def _sync_to_db(self, policy: SLAPolicy) -> None:
        db = SessionLocal()
        try:
            db_obj = db.query(SLAPolicyModel).filter_by(policy_id=policy.policy_id).first()
            from_dt = datetime.fromisoformat(policy.effective_from) if policy.effective_from else None
            until_dt = datetime.fromisoformat(policy.effective_until) if policy.effective_until else None
            p_level = policy.priority_level.value if hasattr(policy.priority_level, "value") else str(policy.priority_level)
            p_status = policy.status.value if hasattr(policy.status, "value") else str(policy.status)
            if not db_obj:
                db_obj = SLAPolicyModel(
                    policy_id=policy.policy_id,
                    jurisdiction_id=policy.jurisdiction_id,
                    category=policy.category,
                    subcategory=policy.subcategory,
                    priority_level=p_level,
                    acknowledgement_minutes=policy.acknowledgement_minutes,
                    resolution_minutes=policy.resolution_minutes,
                    status=p_status,
                    source_reference=policy.source_reference,
                    source_title=policy.source_title,
                    effective_from=from_dt,
                    effective_until=until_dt,
                )
                db.add(db_obj)
                db.commit()
            else:
                db_obj.jurisdiction_id = policy.jurisdiction_id
                db_obj.category = policy.category
                db_obj.subcategory = policy.subcategory
                db_obj.priority_level = p_level
                db_obj.acknowledgement_minutes = policy.acknowledgement_minutes
                db_obj.resolution_minutes = policy.resolution_minutes
                db_obj.status = p_status
                db_obj.source_reference = policy.source_reference
                db_obj.source_title = policy.source_title
                db_obj.effective_from = from_dt
                db_obj.effective_until = until_dt
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def seed_default_policies(self) -> None:
        """Seed default PROVISIONAL policies for global fallback behavior."""
        self._policies.clear()

        # 1. Global Priority Defaults (jurisdiction_id=None, category="*", subcategory="*")
        priority_defaults = [
            ("sla_pol_critical", PriorityLevel.CRITICAL, 15, 120),       # 15 mins ack, 2 hrs res
            ("sla_pol_high", PriorityLevel.HIGH, 60, 1440),             # 60 mins ack, 24 hrs res
            ("sla_pol_medium", PriorityLevel.MEDIUM, 360, 4320),         # 6 hrs ack, 72 hrs res
            ("sla_pol_low", PriorityLevel.LOW, 1440, 10080),            # 24 hrs ack, 168 hrs res
        ]

        now_str = datetime.now(timezone.utc).isoformat()
        for pol_id, level, ack_mins, res_mins in priority_defaults:
            pol = SLAPolicy(
                policy_id=pol_id,
                jurisdiction_id=None,
                category="*",
                subcategory="*",
                priority_level=level,
                acknowledgement_minutes=ack_mins,
                resolution_minutes=res_mins,
                status=SLAPolicyStatus.PROVISIONAL,
                source_reference=None,
                source_title=None,
                created_at=now_str,
                updated_at=now_str,
                active=True,
            )
            self._policies[pol.policy_id] = pol
            self._sync_to_db(pol)

        # 2. Global Specialized Subcategory Overrides
        specialized_policies = [
            SLAPolicy(
                policy_id="sla_elec_critical",
                jurisdiction_id=None,
                category=Category.ELECTRICITY.value,
                subcategory="SPARKING",
                priority_level=PriorityLevel.CRITICAL,
                acknowledgement_minutes=15,
                resolution_minutes=120,
                status=SLAPolicyStatus.PROVISIONAL,
                source_reference=None,
                source_title=None,
                created_at=now_str,
                updated_at=now_str,
                active=True,
            ),
            SLAPolicy(
                policy_id="sla_sewer_manhole",
                jurisdiction_id=None,
                category=Category.SEWERAGE.value,
                subcategory="OPEN_MANHOLE",
                priority_level=PriorityLevel.CRITICAL,
                acknowledgement_minutes=30,
                resolution_minutes=240,
                status=SLAPolicyStatus.PROVISIONAL,
                source_reference=None,
                source_title=None,
                created_at=now_str,
                updated_at=now_str,
                active=True,
            ),
            SLAPolicy(
                policy_id="sla_road_pothole_high",
                jurisdiction_id=None,
                category=Category.ROAD_DAMAGE.value,
                subcategory="POTHOLE",
                priority_level=PriorityLevel.HIGH,
                acknowledgement_minutes=120,
                resolution_minutes=1440,
                status=SLAPolicyStatus.PROVISIONAL,
                source_reference=None,
                source_title=None,
                created_at=now_str,
                updated_at=now_str,
                active=True,
            ),
        ]

        for pol in specialized_policies:
            self._policies[pol.policy_id] = pol
            self._sync_to_db(pol)

    def save(self, policy: SLAPolicy) -> SLAPolicy:
        self._policies[policy.policy_id] = policy
        self._sync_to_db(policy)
        return policy

    def get(self, policy_id: str) -> Optional[SLAPolicy]:
        return self._policies.get(policy_id)

    def list_all(
        self,
        jurisdiction_id: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[SLAPolicyStatus] = None,
        active: Optional[bool] = None,
    ) -> List[SLAPolicy]:
        results = list(self._policies.values())

        if jurisdiction_id is not None:
            results = [p for p in results if p.jurisdiction_id == jurisdiction_id]
        if category is not None:
            results = [p for p in results if p.category.upper() == category.upper()]
        if status is not None:
            results = [p for p in results if p.status == status]
        if active is not None:
            results = [p for p in results if p.active == active]

        return results

    def delete(self, policy_id: str) -> SLAPolicy:
        """Deactivates a policy to preserve historical usage provenance."""
        pol = self._policies.get(policy_id)
        if not pol:
            raise KeyError(f"SLA policy '{policy_id}' not found.")

        now_str = datetime.now(timezone.utc).isoformat()
        updated_pol = pol.model_copy(
            update={
                "active": False,
                "status": SLAPolicyStatus.INACTIVE,
                "updated_at": now_str,
            }
        )
        self._policies[policy_id] = updated_pol
        self._sync_to_db(updated_pol)
        return updated_pol

    def clear(self) -> None:
        self._policies.clear()
        db = SessionLocal()
        try:
            db.query(SLAPolicyModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


sla_policy_store = SLAPolicyStore()


class SLACalculator:
    """Engine resolving SLA policies based on deterministic 6-tier precedence and computing deadlines."""

    def __init__(self, store: Optional[SLAPolicyStore] = None):
        self._store = store or sla_policy_store

    def resolve_policy(
        self,
        category: str,
        subcategory: Optional[str],
        priority_level: PriorityLevel,
        jurisdiction_id: Optional[str] = None,
        request_time: Optional[datetime] = None,
    ) -> Optional[SLAPolicy]:
        """
        Resolves active SLA policy using 6-tier deterministic precedence:
        1. Active jurisdiction + category + subcategory + priority
        2. Active jurisdiction + category + priority
        3. Global category + subcategory + priority
        4. Global category + priority
        5. Global priority fallback
        6. None (Missing SLA Policy)
        """
        now_dt = request_time or datetime.now(timezone.utc)
        cat_upper = category.upper().strip() if category else "*"
        sub_upper = subcategory.upper().strip() if subcategory and subcategory != "*" else None
        jur_clean = jurisdiction_id.strip() if jurisdiction_id and jurisdiction_id != "*" else None

        # Filter active and effective policies
        active_policies: List[SLAPolicy] = []
        for pol in self._store.list_all(active=True):
            if pol.status == SLAPolicyStatus.INACTIVE:
                continue

            # Effective date checks
            if pol.effective_from:
                from_dt = datetime.fromisoformat(pol.effective_from)
                if now_dt < from_dt:
                    continue
            if pol.effective_until:
                until_dt = datetime.fromisoformat(pol.effective_until)
                if now_dt > until_dt:
                    continue

            if pol.priority_level == priority_level:
                active_policies.append(pol)

        # Helper matching functions
        def is_jur_match(p: SLAPolicy, target_jur: Optional[str]) -> bool:
            if target_jur is None:
                return p.jurisdiction_id is None or p.jurisdiction_id == "*" or p.jurisdiction_id == ""
            return p.jurisdiction_id == target_jur

        def is_cat_match(p: SLAPolicy, target_cat: str) -> bool:
            return p.category.upper() == target_cat

        def is_sub_match(p: SLAPolicy, target_sub: Optional[str]) -> bool:
            if target_sub is None:
                return p.subcategory is None or p.subcategory == "*" or p.subcategory == ""
            return p.subcategory is not None and p.subcategory.upper() == target_sub

        # Tier 1: Active Jurisdiction + Category + Subcategory + Priority
        if jur_clean and sub_upper:
            for p in active_policies:
                if is_jur_match(p, jur_clean) and is_cat_match(p, cat_upper) and is_sub_match(p, sub_upper):
                    return p

        # Tier 2: Active Jurisdiction + Category + Priority
        if jur_clean:
            for p in active_policies:
                if is_jur_match(p, jur_clean) and is_cat_match(p, cat_upper) and (p.subcategory is None or p.subcategory in ["*", ""]):
                    return p

        # Tier 3: Global Category + Subcategory + Priority
        if sub_upper:
            for p in active_policies:
                if is_jur_match(p, None) and is_cat_match(p, cat_upper) and is_sub_match(p, sub_upper):
                    return p

        # Tier 4: Global Category + Priority
        for p in active_policies:
            if is_jur_match(p, None) and is_cat_match(p, cat_upper) and (p.subcategory is None or p.subcategory in ["*", ""]):
                return p

        # Tier 5: Global Priority Fallback (Category="*" and Subcategory="*")
        for p in active_policies:
            if is_jur_match(p, None) and (p.category == "*" or p.category == "") and (p.subcategory is None or p.subcategory in ["*", ""]):
                return p

        # Tier 6: No policy matched
        return None

    def get_policy(
        self,
        category: str,
        subcategory: Optional[str],
        priority_level: PriorityLevel,
        jurisdiction_id: Optional[str] = None,
        request_time: Optional[datetime] = None,
    ) -> SLAPolicy:
        pol = self.resolve_policy(category, subcategory, priority_level, jurisdiction_id, request_time)
        if not pol:
            raise NoMatchingSLAPolicyError(
                f"No active SLA policy configured for jurisdiction='{jurisdiction_id}', category='{category}', "
                f"subcategory='{subcategory}', priority='{priority_level.value}'."
            )
        return pol

    def calculate_deadlines(
        self, policy: SLAPolicy, start_time: Optional[datetime] = None
    ) -> Tuple[datetime, datetime]:
        base_time = start_time or datetime.now(timezone.utc)
        ack_deadline = base_time + timedelta(minutes=policy.acknowledgement_minutes)
        res_deadline = base_time + timedelta(minutes=policy.resolution_minutes)
        return ack_deadline, res_deadline

    def create_sla_snapshot(
        self, policy: SLAPolicy, start_time: Optional[datetime] = None
    ) -> SLASnapshot:
        ack_dt, res_dt = self.calculate_deadlines(policy, start_time)
        return SLASnapshot(
            policy_id=policy.policy_id,
            status=policy.status,
            source_reference=policy.source_reference,
            source_title=policy.source_title,
            acknowledgement_minutes=policy.acknowledgement_minutes,
            resolution_minutes=policy.resolution_minutes,
            acknowledgement_deadline=ack_dt.isoformat(),
            resolution_deadline=res_dt.isoformat(),
        )


sla_calculator = SLACalculator()
