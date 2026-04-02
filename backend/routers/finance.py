from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional

from database import get_db
from models import User, FinancialRecord, RoleEnum
from schemas import FinancialRecordCreate, FinancialRecordUpdate, FinancialRecordOut, MessageResponse
from auth import get_current_active_user, require_analyst, require_viewer

router = APIRouter(prefix="/finance", tags=["Finance"])


# ── Create Record (admin + analyst only) ──────────────────────────────────────
@router.post("/records", response_model=FinancialRecordOut, status_code=201)
def create_record(
    payload: FinancialRecordCreate,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    record = FinancialRecord(
        amount=payload.amount,
        type=payload.type,
        category=payload.category,
        date=payload.date,
        notes=payload.notes,
        user_id=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── List Records (all roles, with filters) ────────────────────────────────────
@router.get("/records", response_model=List[FinancialRecordOut])
def list_records(
    type: Optional[str] = Query(None, description="Filter by type: income or expense"),
    category: Optional[str] = Query(None, description="Filter by category"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    # Admins see all records, others see only their own
    query = db.query(FinancialRecord)
    if current_user.role != RoleEnum.admin:
        query = query.filter(FinancialRecord.user_id == current_user.id)

    if type:
        query = query.filter(FinancialRecord.type == type)
    if category:
        query = query.filter(FinancialRecord.category.ilike(f"%{category}%"))
    if date_from:
        query = query.filter(FinancialRecord.date >= date_from)
    if date_to:
        query = query.filter(FinancialRecord.date <= date_to)

    return query.order_by(FinancialRecord.date.desc()).offset(skip).limit(limit).all()


# ── Get Single Record ─────────────────────────────────────────────────────────
@router.get("/records/{record_id}", response_model=FinancialRecordOut)
def get_record(
    record_id: int,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    record = db.query(FinancialRecord).filter(FinancialRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")
    # Non-admins can only view their own records
    if current_user.role != RoleEnum.admin and record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return record


# ── Update Record (admin + analyst, own records only unless admin) ─────────────
@router.patch("/records/{record_id}", response_model=FinancialRecordOut)
def update_record(
    record_id: int,
    payload: FinancialRecordUpdate,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    record = db.query(FinancialRecord).filter(FinancialRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")
    if current_user.role != RoleEnum.admin and record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your own records.")

    if payload.amount is not None:
        record.amount = payload.amount
    if payload.type is not None:
        record.type = payload.type
    if payload.category is not None:
        record.category = payload.category
    if payload.date is not None:
        record.date = payload.date
    if payload.notes is not None:
        record.notes = payload.notes

    db.commit()
    db.refresh(record)
    return record


# ── Delete Record (admin only) ────────────────────────────────────────────────
@router.delete("/records/{record_id}", response_model=MessageResponse)
def delete_record(
    record_id: int,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    record = db.query(FinancialRecord).filter(FinancialRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")
    if current_user.role != RoleEnum.admin and record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own records.")

    db.delete(record)
    db.commit()
    return {"message": f"Record {record_id} deleted successfully."}