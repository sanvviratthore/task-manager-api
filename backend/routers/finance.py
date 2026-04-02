# backend/routers/finance.py
# ──────────────────────────────────────────────────────────────────────────────
# Financial Records CRUD
#   Viewer  → GET only
#   Analyst → GET only
#   Admin   → full CRUD
# ──────────────────────────────────────────────────────────────────────────────

from datetime import date as Date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import FinancialRecord, RecordType, User
from schemas import (
    FinancialRecordCreate,
    FinancialRecordOut,
    FinancialRecordUpdate,
    PaginatedRecords,
)
from auth import get_current_active_user, require_role   # your existing helpers

router = APIRouter(prefix="/api/v1/finance", tags=["Finance Records"])


# ── helpers ────────────────────────────────────────────────────────────────────

def _get_record_or_404(record_id: int, db: Session) -> FinancialRecord:
    record = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.id == record_id, FinancialRecord.is_deleted == False)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


# ── CREATE ─────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=FinancialRecordOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a financial record (Admin only)",
)
def create_record(
    payload: FinancialRecordCreate,
    db:      Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),   # admin guard
):
    record = FinancialRecord(**payload.model_dump(), created_by=current_user.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── LIST (with filters + pagination) ──────────────────────────────────────────

@router.get(
    "/",
    response_model=PaginatedRecords,
    summary="List financial records (Viewer / Analyst / Admin)",
)
def list_records(
    type:       Optional[RecordType] = Query(None, description="Filter by income or expense"),
    category:   Optional[str]        = Query(None, description="Filter by category name"),
    date_from:  Optional[Date]       = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to:    Optional[Date]       = Query(None, description="End date (YYYY-MM-DD)"),
    page:       int                  = Query(1,    ge=1),
    limit:      int                  = Query(20,   ge=1, le=100),
    db:         Session              = Depends(get_db),
    _: User = Depends(get_current_active_user),           # any authenticated user
):
    query = db.query(FinancialRecord).filter(FinancialRecord.is_deleted == False)

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

@router.get(
    "/{record_id}",
    response_model=FinancialRecordOut,
    summary="Get a single record (Viewer / Analyst / Admin)",
)
def get_record(
    record_id: int,
    db:        Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    return _get_record_or_404(record_id, db)


# ── UPDATE ─────────────────────────────────────────────────────────────────────

@router.patch(
    "/{record_id}",
    response_model=FinancialRecordOut,
    summary="Update a financial record (Admin only)",
)
def update_record(
    record_id: int,
    payload:   FinancialRecordUpdate,
    db:        Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    record = _get_record_or_404(record_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


# ── SOFT DELETE ────────────────────────────────────────────────────────────────

@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a financial record (Admin only)",
)
def delete_record(
    record_id: int,
    db:        Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    record = _get_record_or_404(record_id, db)
    record.is_deleted = True
    db.commit()