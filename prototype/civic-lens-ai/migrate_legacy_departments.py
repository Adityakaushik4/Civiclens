import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()


# Add app to path if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import engine, SessionLocal, init_db
from app.database.models import RoutingDecisionModel, IssueLifecycleModel, WorkAssignmentModel
from app.taxonomy import Department

legacy_mapping = {
    "Road Maintenance": Department.ROADS_PWD.value,
    "Sanitation": Department.SANITATION_WASTE.value,
    "Water Supply Board": Department.WATER_SUPPLY.value,
    "Electrical/Municipal Lighting": Department.ELECTRICAL_LIGHTING.value,
    "Drainage/Public Works": Department.DRAINAGE_SEWERAGE.value,
    "Sewerage Operations": Department.DRAINAGE_SEWERAGE.value,
    "Power Distribution": Department.ELECTRICAL_LIGHTING.value,
    "Public Health & Sanitation": Department.PUBLIC_TOILETS.value, # Defaulted previously
    "Horticulture & Parks": Department.PARKS_HORTICULTURE.value,
    "Traffic Management": Department.TRAFFIC_SAFETY.value,
    "Civic Helpdesk": Department.OTHER_GENERAL.value
}

def migrate_legacy_departments():
    init_db()
    db = SessionLocal()
    try:
        updated_routing = 0
        updated_lifecycle = 0
        updated_work = 0

        # Update RoutingDecisionModel
        routing_decisions = db.query(RoutingDecisionModel).all()
        for decision in routing_decisions:
            if decision.primary_department in legacy_mapping:
                decision.primary_department = legacy_mapping[decision.primary_department]
                updated_routing += 1
        
        # Update IssueLifecycleModel
        lifecycles = db.query(IssueLifecycleModel).all()
        for lifecycle in lifecycles:
            if lifecycle.current_department in legacy_mapping:
                lifecycle.current_department = legacy_mapping[lifecycle.current_department]
                updated_lifecycle += 1

        # Update WorkAssignmentModel
        work_assignments = db.query(WorkAssignmentModel).all()
        for assignment in work_assignments:
            if assignment.department in legacy_mapping:
                assignment.department = legacy_mapping[assignment.department]
                updated_work += 1

        db.commit()
        print(f"Migration successful!")
        print(f"Updated {updated_routing} RoutingDecisionModel records.")
        print(f"Updated {updated_lifecycle} IssueLifecycleModel records.")
        print(f"Updated {updated_work} WorkAssignmentModel records.")

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_legacy_departments()
