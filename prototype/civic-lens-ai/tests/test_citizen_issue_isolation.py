import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.jwt import create_access_token
from app.database.connection import SessionLocal
from app.database.models import UserModel
from app.duplicates import master_issue_store, MasterIssueRecord
from app.taxonomy import Category

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_users():
    """Seeds test users (Citizen A, Citizen B, Operator, Supervisor) in DB."""
    db = SessionLocal()
    try:
        # Citizen A
        user_a = db.query(UserModel).filter_by(id="usr_citizen_a").first()
        if not user_a:
            user_a = UserModel(
                id="usr_citizen_a",
                email="citizen_a@test.com",
                password_hash="hashed_pw_a",
                full_name="Citizen A",
                role="CITIZEN",
                is_active=True
            )
            db.add(user_a)

        # Citizen B
        user_b = db.query(UserModel).filter_by(id="usr_citizen_b").first()
        if not user_b:
            user_b = UserModel(
                id="usr_citizen_b",
                email="citizen_b@test.com",
                password_hash="hashed_pw_b",
                full_name="Citizen B",
                role="CITIZEN",
                is_active=True
            )
            db.add(user_b)

        # Operator
        user_op = db.query(UserModel).filter_by(id="usr_operator_1").first()
        if not user_op:
            user_op = UserModel(
                id="usr_operator_1",
                email="operator@test.com",
                password_hash="hashed_pw_op",
                full_name="Operator One",
                role="OPERATOR",
                is_active=True
            )
            db.add(user_op)

        # Supervisor
        user_sup = db.query(UserModel).filter_by(id="usr_supervisor_1").first()
        if not user_sup:
            user_sup = UserModel(
                id="usr_supervisor_1",
                email="supervisor@test.com",
                password_hash="hashed_pw_sup",
                full_name="Supervisor One",
                role="SUPERVISOR",
                is_active=True
            )
            db.add(user_sup)

        db.commit()
    finally:
        db.close()


def get_token(user_id: str, role: str = "CITIZEN") -> str:
    return create_access_token(data={"sub": user_id, "role": role})


def test_1_and_2_my_issues_isolation():
    """TEST 1 & 2: Citizen A sees Issue A; Citizen A does NOT see Citizen B's Issue B."""
    token_a = get_token("usr_citizen_a")
    token_b = get_token("usr_citizen_b")

    # Create Issue A for Citizen A
    rec_a = master_issue_store.create_master_issue(
        title="Pothole in Ward 1",
        category=Category.ROAD_DAMAGE,
        subcategory="Pothole",
        latitude=20.2961,
        longitude=85.8245,
        description="Issue A by Citizen A",
        reporter_id="usr_citizen_a"
    )

    # Create Issue B for Citizen B
    rec_b = master_issue_store.create_master_issue(
        title="Garbage in Ward 2",
        category=Category.GARBAGE,
        subcategory="Public Dump",
        latitude=20.3000,
        longitude=85.8300,
        description="Issue B by Citizen B",
        reporter_id="usr_citizen_b"
    )

    # Citizen A requests My Issues
    res_a = client.get("/api/v1/ai/master-issues", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    issues_a = res_a.json()
    issue_ids_a = [i["id"] for i in issues_a]
    assert rec_a.id in issue_ids_a
    assert rec_b.id not in issue_ids_a

    # Citizen B requests My Issues
    res_b = client.get("/api/v1/ai/master-issues", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    issues_b = res_b.json()
    issue_ids_b = [i["id"] for i in issues_b]
    assert rec_b.id in issue_ids_b
    assert rec_a.id not in issue_ids_b


def test_3_and_4_direct_single_issue_access():
    """TEST 3 & 4: Citizen A blocked (403) from Citizen B's issue; Citizen B allowed for own issue."""
    token_a = get_token("usr_citizen_a")
    token_b = get_token("usr_citizen_b")

    rec_b = master_issue_store.create_master_issue(
        title="Private Issue B",
        category=Category.STREETLIGHT,
        subcategory="No Power",
        latitude=20.2500,
        longitude=85.8000,
        description="Citizen B private issue",
        reporter_id="usr_citizen_b"
    )

    # Citizen A tries to view Citizen B's issue details directly
    res_unauth = client.get(f"/api/v1/public/issues/{rec_b.id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_unauth.status_code == 403

    # Citizen A tries to view evidence of Citizen B's issue
    res_ev_unauth = client.get(f"/api/v1/evidence/{rec_b.id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_ev_unauth.status_code == 403

    # Citizen B views own issue
    res_auth = client.get(f"/api/v1/public/issues/{rec_b.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_auth.status_code == 200


def test_5_and_6_operator_supervisor_role_access():
    """TEST 5 & 6: Operator & Supervisor retain authorized access to issues."""
    token_op = get_token("usr_operator_1", role="OPERATOR")
    token_sup = get_token("usr_supervisor_1", role="SUPERVISOR")

    rec = master_issue_store.create_master_issue(
        title="Drainage Overflow",
        category=Category.DRAINAGE,
        subcategory="Overflow",
        latitude=20.2800,
        longitude=85.8100,
        reporter_id="usr_citizen_a"
    )

    # Operator sees all master issues
    res_op = client.get("/api/v1/ai/master-issues", headers={"Authorization": f"Bearer {token_op}"})
    assert res_op.status_code == 200
    op_issue_ids = [i["id"] for i in res_op.json()]
    assert rec.id in op_issue_ids

    # Supervisor verification queue works
    res_sup = client.get("/api/v1/supervisor/verification-queue", headers={"Authorization": f"Bearer {token_sup}"})
    assert res_sup.status_code == 200
