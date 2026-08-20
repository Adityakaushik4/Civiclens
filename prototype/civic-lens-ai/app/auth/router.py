import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import UserModel
from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    UserRoleEnum,
)
from app.auth.hash import hash_password, verify_password
from app.auth.jwt import create_access_token
from app.auth.dependencies import get_current_user

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & RBAC"])

def _to_user_response(user: UserModel) -> UserResponse:
    created_at_str = user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=UserRoleEnum(user.role),
        jurisdiction_id=user.jurisdiction_id,
        is_active=user.is_active,
        created_at=created_at_str
    )

@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user account with hashed password credentials."""
    existing = db.query(UserModel).filter(UserModel.email == payload.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account with email '{payload.email}' already exists."
        )
        
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    pwd_hash = hash_password(payload.password)
    
    new_user = UserModel(
        id=user_id,
        email=payload.email.lower().strip(),
        password_hash=pwd_hash,
        full_name=payload.full_name.strip(),
        role=payload.role.value if hasattr(payload.role, "value") else str(payload.role),
        jurisdiction_id=payload.jurisdiction_id or "GLOBAL",
        is_active=True,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return _to_user_response(new_user)

from fastapi.responses import Response

@auth_router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticates user credentials, sets HTTP-Only cookie, and issues a JWT access token."""
    user = db.query(UserModel).filter(UserModel.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive."
        )
        
    token_claims = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "jurisdiction_id": user.jurisdiction_id
    }
    access_token = create_access_token(token_claims)
    
    # Set HTTP-Only Cookie for session security
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24, # 24 hours
        path="/"
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=_to_user_response(user)
    )

@auth_router.post("/logout")
def logout_user(response: Response):
    """Clears the authenticated session HTTP-Only cookie."""
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Successfully logged out."}

@auth_router.get("/me", response_model=UserResponse)
def get_authenticated_user_profile(current_user: UserModel = Depends(get_current_user)):
    """Returns the authenticated user's profile."""
    return _to_user_response(current_user)
