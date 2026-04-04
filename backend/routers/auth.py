from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database import get_db
from models import User, UserSession
from schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshRequest, AccessTokenResponse, MessageResponse, UserSessionOut
)
from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_active_user,
)
from services.rate_limiter_service import limit_login, limit_register, limit_password_reset

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Register ───────────────────────────────────────────────────────────────────
@router.post("/register", response_model=MessageResponse, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(limit_register),
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken.")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # Set audit fields
    user.created_by = user.id
    user.updated_by = user.id
    db.commit()
    return {"message": "Account created successfully. You can now log in."}


# ── Login ──────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(limit_login),
):
    user = db.query(User).filter(User.username == payload.username).first()

    # Constant-time failure — prevents user enumeration
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token_str, expires_at = create_refresh_token({"sub": str(user.id)})

    # Store as UserSession with device info
    session = UserSession(
        token=refresh_token_str,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:255],
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token_str)


# ── Refresh ────────────────────────────────────────────────────────────────────
@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_token(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    decoded = decode_token(payload.refresh_token)
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type.")

    session = db.query(UserSession).filter(
        UserSession.token == payload.refresh_token,
        UserSession.revoked == False,
    ).first()

    if not session:
        raise HTTPException(status_code=401, detail="Session not found or revoked.")

    if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        session.revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    new_access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return AccessTokenResponse(access_token=new_access_token)


# ── Logout ─────────────────────────────────────────────────────────────────────
@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: RefreshRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = db.query(UserSession).filter(
        UserSession.token == payload.refresh_token,
        UserSession.user_id == current_user.id,
    ).first()
    if session:
        session.revoked = True
        db.commit()
    return {"message": "Logged out successfully."}


# ── List Sessions ──────────────────────────────────────────────────────────────
@router.get("/sessions", response_model=list[UserSessionOut])
def list_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all active sessions for the current user (device management)."""
    return db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.revoked == False,
    ).all()


# ── Revoke All Sessions (logout everywhere) ────────────────────────────────────
@router.post("/logout-all", response_model=MessageResponse)
def logout_all(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke all active sessions — logs out from all devices."""
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.revoked == False,
    ).update({"revoked": True})
    db.commit()
    return {"message": "Logged out from all devices."}


# ── Password Reset stub ────────────────────────────────────────────────────────
@router.post("/password-reset", response_model=MessageResponse)
def password_reset(
    request: Request,
    _: None = Depends(limit_password_reset),
):
    """Rate-limited. In production: send reset link via SMTP."""
    return {"message": "If that email exists, a reset link has been sent."}