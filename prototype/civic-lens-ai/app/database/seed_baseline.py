"""
Phase 8B Database Baseline Seeding Script.
Populates minimum required baseline configuration records:
- SLA Policies (7 default policies)
- Budget Cycle (Ward 7 Participatory Budget Cycle 2027)
- Reopen Policy (Default 3-reopen threshold policy)
- Clean, clearly-marked Demo Master Issues (3 records)
"""
import sys
import datetime
from typing import Dict, Any

from app.database.connection import engine, SessionLocal, Base
from app.database.models import (
    SLAPolicyModel,
    BudgetCycleModel,
    ReopenPolicyModel,
    MasterIssueModel,
)
from app.sla.engine import sla_policy_store
from app.escalation.policy import reopen_policy_store
from app.finance.engine import finance_store
from app.schemas import Category
from app.duplicates.store import master_issue_store, MasterIssueRecord


def seed_baseline_data() -> Dict[str, Any]:
    """Seeds all baseline configuration and demo records into SQLite database."""
    Base.metadata.create_all(bind=engine)
    results = {}

    # 1. Seed SLA Policies
    sla_policy_store.seed_default_policies()
    db = SessionLocal()
    try:
        sla_count = db.query(SLAPolicyModel).count()
        results["sla_policies"] = sla_count
    finally:
        db.close()

    # 2. Seed Budget Cycles
    finance_store._seed_default_cycle()
    db = SessionLocal()
    try:
        cycle_count = db.query(BudgetCycleModel).count()
        results["budget_cycles"] = cycle_count
    finally:
        db.close()

    # 3. Seed Reopen Policies
    reopen_policy_store._seed_default_policy()
    db = SessionLocal()
    try:
        reopen_count = db.query(ReopenPolicyModel).count()
        results["reopen_policies"] = reopen_count
    finally:
        db.close()

    # 4. Seed Consistent Demo Master Issues (using distinct Ward 7 coordinates)
    demo_issues = [
        MasterIssueRecord(
            id="mi_demo_pothole_ward7",
            title="[DEMO] Severe Pothole Cluster on Janpath Road",
            category=Category.ROAD_DAMAGE,
            subcategory="POTHOLE",
            severity_score=4,
            latitude=20.3010,
            longitude=85.8310,
            address_description="Janpath Road near Master Canteen Square, Ward 7",
        ),
        MasterIssueRecord(
            id="mi_demo_light_ward7",
            title="[DEMO] Broken Streetlight Pole Junction",
            category=Category.ELECTRICITY,
            subcategory="STREET_LIGHT",
            severity_score=3,
            latitude=20.3025,
            longitude=85.8325,
            address_description="Ward 7 Streetlight Pole #42, Unit 9",
        ),
        MasterIssueRecord(
            id="mi_demo_drain_ward7",
            title="[DEMO] Overflowing Stormwater Drain",
            category=Category.WATER_SUPPLY,
            subcategory="DRAIN_BLOCKAGE",
            severity_score=5,
            latitude=20.3040,
            longitude=85.8340,
            address_description="Block C Stormwater Drain Outlet, Ward 7",
        ),
    ]

    for demo_issue in demo_issues:
        master_issue_store._sync_to_db(demo_issue)

    db = SessionLocal()
    try:
        master_count = db.query(MasterIssueModel).count()
        results["master_issues"] = master_count
    finally:
        db.close()

    return results


if __name__ == "__main__":
    summary = seed_baseline_data()
    print("Baseline Seeding Complete:")
    for k, v in summary.items():
        print(f"  {k}: {v} total rows")
