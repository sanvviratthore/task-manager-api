from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import User
from schemas import UserOut, UserUpdate, RoleUpdate, MessageResponse
from auth import get_current_active_user, require_admin

router = APIRouter(prefix="/users", tags=["Users"])


# ── My Profile ─────────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if payload.email:
        exists = db.query(User).filter(
            User.email == payload.email,
            User.id != current_user.id
        ).first()
        if exists:
            raise HTTPException(status_code=400, detail="Email already in use.")
        current_user.email = payload.email

    if payload.username:
        exists = db.query(User).filter(
            User.username == payload.username,
            User.id != current_user.id
        ).first()
        if exists:
            raise HTTPException(status_code=400, detail="Username already taken.")
        current_user.username = payload.username

    db.commit()
    db.refresh(current_user)
    return current_user


# ── Admin: List All Users ──────────────────────────────────────────────────────
@router.get("/", response_model=List[UserOut], dependencies=[Depends(require_admin)])
def list_users(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(User).offset(skip).limit(limit).all()


# ── Admin: Get User by ID ──────────────────────────────────────────────────────
@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(require_admin)])
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


# ── Admin: Update Role ─────────────────────────────────────────────────────────
@router.patch("/{user_id}/role", response_model=UserOut, dependencies=[Depends(require_admin)])
def update_role(user_id: int, payload: RoleUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


# ── Admin: Deactivate User ─────────────────────────────────────────────────────
@router.delete("/{user_id}", response_model=MessageResponse, dependencies=[Depends(require_admin)])
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = False
    db.commit()
    return {"message": f"User {user.username} has been deactivated."}
