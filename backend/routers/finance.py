# backend/routers/finance.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import FinancialRecord, RecordTypeEnum, User
from schemas import (
    FinancialRecordCreate,
    FinancialRecordOut,
    FinancialRecordUpdate,
    PaginatedRecords,
)
from auth import get_current_active_user, require_admin

router = APIRouter(prefix="/api/v1/finance", tags=["Finance Records"])


def _get_record_or_404(record_id: int, db: Session) -> FinancialRecord:
    record = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


# ── CREATE ─────────────────────────────────────────────────────────────────────

@router.post("/", response_model=FinancialRecordOut, status_code=status.HTTP_201_CREATED,
             summary="Create a financial record (Admin only)")
def create_record(
    payload: FinancialRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    record = FinancialRecord(
        amount=payload.amount,
        type=payload.type,
        category=payload.category,
        date=payload.date,
        notes=payload.notes,
        user_id=current_user.id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── LIST ───────────────────────────────────────────────────────────────────────

@router.get("/", response_model=PaginatedRecords,
            summary="List financial records (all roles)")
def list_records(
    type:      Optional[RecordTypeEnum] = Query(None),
    category:  Optional[str]            = Query(None),
    date_from: Optional[str]            = Query(None, description="YYYY-MM-DD"),
    date_to:   Optional[str]            = Query(None, description="YYYY-MM-DD"),
    page:      int                      = Query(1,  ge=1),
    limit:     int                      = Query(20, ge=1, le=100),
    db:        Session                  = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    query = db.query(FinancialRecord)

    if type:
        query = query.filter(FinancialRecord.type == type)
    if category:
        query = query.filter(FinancialRecord.category.ilike(f"%{category}%"))
    if date_from:
        query = query.filter(FinancialRecord.date >= date_from)
    if date_to:
        query = query.filter(FinancialRecord.date <= date_to)

    total   = query.count()
    records = (
        query.order_by(FinancialRecord.date.desc())
             .offset((page - 1) * limit)
             .limit(limit)
             .all()
    )
    return PaginatedRecords(total=total, page=page, limit=limit, records=records)


# ── GET SINGLE ─────────────────────────────────────────────────────────────────

@router.get("/{record_id}", response_model=FinancialRecordOut,
            summary="Get a single record (all roles)")
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    return _get_record_or_404(record_id, db)


# ── UPDATE ─────────────────────────────────────────────────────────────────────

@router.patch("/{record_id}", response_model=FinancialRecordOut,
              summary="Update a financial record (Admin only)")
def update_record(
    record_id: int,
    payload: FinancialRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    record = _get_record_or_404(record_id, db)

    # Optimistic locking check
    if record.version != payload.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Record was modified by someone else (expected version {record.version}).",
        )

    update_data = payload.model_dump(exclude_unset=True, exclude={"version"})
    for field, value in update_data.items():
        setattr(record, field, value)

    record.version    += 1
    record.updated_by  = current_user.id
    db.commit()
    db.refresh(record)
    return record


# ── DELETE (soft via is_deleted if you add it, or hard delete) ─────────────────

@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a financial record (Admin only)")
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    record = _get_record_or_404(record_id, db)
    db.delete(record)
    db.commit()