from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database import get_db
from models import User, RefreshToken
from schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, AccessTokenResponse, MessageResponse
from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_active_user,
)
from rate_limit import limit_login, limit_register, limit_password_reset

router = APIRouter(prefix="/auth", tags=["Auth"])


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
    return {"message": "Account created successfully. You can now log in."}


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(limit_login),
):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token_str, expires_at = create_refresh_token({"sub": str(user.id)})

    db_token = RefreshToken(
        token=refresh_token_str,
        user_id=user.id,
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token_str)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_token(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    decoded = decode_token(payload.refresh_token)
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type.")

    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == payload.refresh_token,
        RefreshToken.revoked == False,
    ).first()
    if not db_token:
        raise HTTPException(status_code=401, detail="Refresh token not found or revoked.")
    if db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        db_token.revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired.")

    user = db.query(User).filter(User.id == db_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    new_access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return AccessTokenResponse(access_token=new_access_token)


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: RefreshRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == payload.refresh_token,
        RefreshToken.user_id == current_user.id,
    ).first()
    if db_token:
        db_token.revoked = True
        db.commit()
    return {"message": "Logged out successfully."}


@router.post("/password-reset", response_model=MessageResponse)
def password_reset(
    request: Request,
    _: None = Depends(limit_password_reset),
):
    return {"message": "If that email exists, a reset link has been sent."}
