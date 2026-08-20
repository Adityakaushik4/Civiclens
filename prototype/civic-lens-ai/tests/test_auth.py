import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth.hash import hash_password, verify_password
from app.auth.jwt import create_access_token, decode_access_token
from app.database.connection import SessionLocal
from app.database.models import UserModel, MasterIssueModel

def test_password_hashing():
    pwd = "securepassword123"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_jwt_token_creation_and_decoding():
    payload = {"sub": "usr_test123", "role": "CITIZEN"}
    token = create_access_token(payload, expires_delta_minutes=15)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "usr_test123"
    assert decoded["role"] == "CITIZEN"

def test_jwt_invalid_token():
    assert decode_access_token("invalid.token.str") is None

@pytest.mark.asyncio
async def test_auth_registration_and_duplicate():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        email = f"citizen_{uuid.uuid4().hex[:6]}@civiclens.gov"
        reg_payload = {
            "email": email,
            "password": "password123",
            "full_name": "Jane Citizen",
            "role": "CITIZEN"
        }
        
        # 1. Registration Success
        r_reg = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert r_reg.status_code == 201
        assert r_reg.json()["email"] == email
        
        # 2. Duplicate Registration Fails
        r_dup = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert r_dup.status_code == 400

@pytest.mark.asyncio
async def test_valid_login_and_cookie():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r_login = await ac.post("/api/v1/auth/login", json={"email": "admin@civiclens.gov", "password": "admin123"})
        assert r_login.status_code == 200
        data = r_login.json()
        assert "access_token" in data
        assert "set-cookie" in r_login.headers or "access_token" in r_login.headers.get("set-cookie", "")

@pytest.mark.asyncio
async def test_invalid_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r_bad = await ac.post("/api/v1/auth/login", json={"email": "admin@civiclens.gov", "password": "wrongpassword"})
        assert r_bad.status_code == 401

@pytest.mark.asyncio
async def test_invalid_expired_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r_me = await ac.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.expired.token"})
        assert r_me.status_code == 401

@pytest.mark.asyncio
async def test_auth_me_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r_login = await ac.post("/api/v1/auth/login", json={"email": "citizen@civiclens.gov", "password": "citizen123"})
        token = r_login.json()["access_token"]
        
        r_me = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r_me.status_code == 200
        assert r_me.json()["email"] == "citizen@civiclens.gov"

@pytest.mark.asyncio
async def test_unauthenticated_protected_route():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r_unauth = await ac.get("/api/v1/auth/me")
        assert r_unauth.status_code == 401

@pytest.mark.asyncio
async def test_role_access_matrix_403_and_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Citizen -> Admin API = 403
        r_cit = await ac.post("/api/v1/auth/login", json={"email": "citizen@civiclens.gov", "password": "citizen123"})
        cit_token = r_cit.json()["access_token"]
        r_cit_admin = await ac.get("/api/v1/admin/sla-policies", headers={"Authorization": f"Bearer {cit_token}"})
        assert r_cit_admin.status_code == 403

        # 2. Operator -> Admin API = 403
        r_op = await ac.post("/api/v1/auth/login", json={"email": "operator@civiclens.gov", "password": "operator123"})
        op_token = r_op.json()["access_token"]
        r_op_admin = await ac.get("/api/v1/admin/sla-policies", headers={"Authorization": f"Bearer {op_token}"})
        assert r_op_admin.status_code == 403

        # 3. Supervisor -> Admin API = 403
        r_sup = await ac.post("/api/v1/auth/login", json={"email": "supervisor@civiclens.gov", "password": "supervisor123"})
        sup_token = r_sup.json()["access_token"]
        r_sup_admin = await ac.get("/api/v1/admin/sla-policies", headers={"Authorization": f"Bearer {sup_token}"})
        assert r_sup_admin.status_code == 403

        # 4. Authorized Admin -> Admin API = 200
        r_adm = await ac.post("/api/v1/auth/login", json={"email": "admin@civiclens.gov", "password": "admin123"})
        adm_token = r_adm.json()["access_token"]
        r_adm_admin = await ac.get("/api/v1/admin/sla-policies", headers={"Authorization": f"Bearer {adm_token}"})
        assert r_adm_admin.status_code == 200

@pytest.mark.asyncio
async def test_citizen_resource_ownership():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create issue owned by reporter "usr_citizen01"
        issue_id = f"iss_own_{uuid.uuid4().hex[:6]}"
        db = SessionLocal()
        try:
            iss = MasterIssueModel(
                id=issue_id,
                title="Test Ownership Issue",
                category="ROADS",
                subcategory="POTHOLE",
                status="RESOLVED",
                severity_score=3,
                latitude=20.2961,
                longitude=85.8245,
            )
            db.add(iss)
            db.commit()
        finally:
            db.close()

        # Login as Citizen B (usr_test_b)
        reg_b = await ac.post("/api/v1/auth/register", json={
            "email": f"cit_b_{uuid.uuid4().hex[:6]}@civiclens.gov",
            "password": "password123",
            "full_name": "Citizen B",
            "role": "CITIZEN"
        })
        token_b = (await ac.post("/api/v1/auth/login", json={
            "email": reg_b.json()["email"],
            "password": "password123"
        })).json()["access_token"]

        # Citizen B attempting to specify Citizen A's actor_id -> 403 Forbidden
        r_reopen = await ac.post(
            f"/api/v1/issues/{issue_id}/reopen",
            json={"actor_id": "usr_citizen01", "reason": "Dissatisfied"},
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert r_reopen.status_code == 403

@pytest.mark.asyncio
async def test_public_endpoint_without_authentication():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r_pub = await ac.get("/api/v1/analytics/summary")
        assert r_pub.status_code == 200

@pytest.mark.asyncio
async def test_inactive_user_cannot_authenticate():
    db = SessionLocal()
    email = f"inactive_{uuid.uuid4().hex[:6]}@civiclens.gov"
    try:
        user = UserModel(
            id=f"usr_inact_{uuid.uuid4().hex[:6]}",
            email=email,
            password_hash=hash_password("password123"),
            full_name="Inactive User",
            role="CITIZEN",
            is_active=False
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r_login = await ac.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
        assert r_login.status_code == 403
