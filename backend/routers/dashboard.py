from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from collections import defaultdict

from database import get_db
from models import User, FinancialRecord, RoleEnum, RecordTypeEnum
from auth import require_analyst, require_viewer

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_records_query(db: Session, current_user: User, date_from=None, date_to=None):
    query = db.query(FinancialRecord)
    if current_user.role != RoleEnum.admin:
        query = query.filter(FinancialRecord.user_id == current_user.id)
    if date_from:
        query = query.filter(FinancialRecord.date >= date_from)
    if date_to:
        query = query.filter(FinancialRecord.date <= date_to)
    return query


# ── Summary (total income, expenses, net balance) ─────────────────────────────
@router.get("/summary")
def get_summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    records = get_records_query(db, current_user, date_from, date_to).all()

    total_income  = sum(r.amount for r in records if r.type == RecordTypeEnum.income)
    total_expense = sum(r.amount for r in records if r.type == RecordTypeEnum.expense)
    net_balance   = total_income - total_expense

    return {
        "total_income":   round(total_income, 2),
        "total_expenses": round(total_expense, 2),
        "net_balance":    round(net_balance, 2),
        "total_records":  len(records),
        "date_from":      date_from,
        "date_to":        date_to,
    }


# ── Category-wise Totals ──────────────────────────────────────────────────────
@router.get("/by-category")
def get_by_category(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    records = get_records_query(db, current_user, date_from, date_to).all()

    income_by_cat  = defaultdict(float)
    expense_by_cat = defaultdict(float)

    for r in records:
        if r.type == RecordTypeEnum.income:
            income_by_cat[r.category] += r.amount
        else:
            expense_by_cat[r.category] += r.amount

    all_categories = set(income_by_cat.keys()) | set(expense_by_cat.keys())

    result = []
    for cat in sorted(all_categories):
        result.append({
            "category":      cat,
            "total_income":  round(income_by_cat.get(cat, 0), 2),
            "total_expense": round(expense_by_cat.get(cat, 0), 2),
            "net":           round(income_by_cat.get(cat, 0) - expense_by_cat.get(cat, 0), 2),
        })

    return {"categories": result, "total_categories": len(result)}


# ── Monthly Trends ────────────────────────────────────────────────────────────
@router.get("/monthly-trends")
def get_monthly_trends(
    year: Optional[int] = Query(None, description="Filter by year e.g. 2026"),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    query = db.query(FinancialRecord)
    if current_user.role != RoleEnum.admin:
        query = query.filter(FinancialRecord.user_id == current_user.id)
    if year:
        query = query.filter(FinancialRecord.date.startswith(str(year)))

    records = query.order_by(FinancialRecord.date).all()

    monthly = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for r in records:
        month_key = r.date[:7]  # YYYY-MM
        if r.type == RecordTypeEnum.income:
            monthly[month_key]["income"] += r.amount
        else:
            monthly[month_key]["expense"] += r.amount

    trends = []
    for month in sorted(monthly.keys()):
        data = monthly[month]
        trends.append({
            "month":         month,
            "total_income":  round(data["income"], 2),
            "total_expense": round(data["expense"], 2),
            "net":           round(data["income"] - data["expense"], 2),
        })

    return {"trends": trends, "months_count": len(trends)}


# ── Recent Activity ───────────────────────────────────────────────────────────
@router.get("/recent")
def get_recent(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    query = db.query(FinancialRecord)
    if current_user.role != RoleEnum.admin:
        query = query.filter(FinancialRecord.user_id == current_user.id)

    records = query.order_by(FinancialRecord.created_at.desc()).limit(limit).all()

    return {
        "recent_records": [
            {
                "id":       r.id,
                "amount":   r.amount,
                "type":     r.type,
                "category": r.category,
                "date":     r.date,
                "notes":    r.notes,
            }
            for r in records
        ],
        "count": len(records),
    }