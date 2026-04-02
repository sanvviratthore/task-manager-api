# backend/routers/dashboard.py
# ──────────────────────────────────────────────────────────────────────────────
# Dashboard Summary APIs
#   All authenticated roles can access these read-only endpoints.
# ──────────────────────────────────────────────────────────────────────────────

from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import FinancialRecord, RecordType, User
from schemas import CategoryTotal, DashboardSummary, MonthlyTrend, FinancialRecordOut
from auth import get_current_active_user

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Full dashboard summary (all roles)",
)
def get_summary(
    db: Session = Depends(get_db),
    _:  User    = Depends(get_current_active_user),
):
    active_records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.is_deleted == False)
        .all()
    )

    # ── Totals ─────────────────────────────────────────────────────────────────
    total_income   = sum(r.amount for r in active_records if r.type == RecordType.income)
    total_expenses = sum(r.amount for r in active_records if r.type == RecordType.expense)
    net_balance    = total_income - total_expenses

    # ── Category totals ────────────────────────────────────────────────────────
    cat_map: dict[str, float] = defaultdict(float)
    for r in active_records:
        cat_map[r.category] += r.amount
    category_totals = [
        CategoryTotal(category=cat, total=round(total, 2))
        for cat, total in sorted(cat_map.items())
    ]

    # ── Monthly trends ─────────────────────────────────────────────────────────
    month_map: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for r in active_records:
        month_key = r.date.strftime("%Y-%m")
        month_map[month_key][r.type.value] += r.amount

    monthly_trends = [
        MonthlyTrend(
            month   = month,
            income  = round(vals["income"],  2),
            expense = round(vals["expense"], 2),
            net     = round(vals["income"] - vals["expense"], 2),
        )
        for month, vals in sorted(month_map.items())
    ]

    # ── Recent activity (last 10) ──────────────────────────────────────────────
    recent = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.is_deleted == False)
        .order_by(FinancialRecord.date.desc(), FinancialRecord.created_at.desc())
        .limit(10)
        .all()
    )

    return DashboardSummary(
        total_income    = round(total_income,   2),
        total_expenses  = round(total_expenses, 2),
        net_balance     = round(net_balance,    2),
        category_totals = category_totals,
        monthly_trends  = monthly_trends,
        recent_records  = recent,
    )


# ── Standalone convenience endpoints (optional, but clean for a dashboard) ─────

@router.get("/totals", summary="Income / expense / net totals only")
def get_totals(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    active = db.query(FinancialRecord).filter(FinancialRecord.is_deleted == False).all()
    income  = round(sum(r.amount for r in active if r.type == RecordType.income),  2)
    expense = round(sum(r.amount for r in active if r.type == RecordType.expense), 2)
    return {"total_income": income, "total_expenses": expense, "net_balance": round(income - expense, 2)}


@router.get("/category-breakdown", response_model=list[CategoryTotal], summary="Category-wise totals")
def category_breakdown(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    rows = (
        db.query(FinancialRecord.category, func.sum(FinancialRecord.amount).label("total"))
        .filter(FinancialRecord.is_deleted == False)
        .group_by(FinancialRecord.category)
        .order_by(FinancialRecord.category)
        .all()
    )
    return [CategoryTotal(category=row.category, total=round(row.total, 2)) for row in rows]


@router.get("/monthly-trends", response_model=list[MonthlyTrend], summary="Monthly income vs expense trends")
def monthly_trends(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    active = db.query(FinancialRecord).filter(FinancialRecord.is_deleted == False).all()
    month_map: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for r in active:
        month_map[r.date.strftime("%Y-%m")][r.type.value] += r.amount
    return [
        MonthlyTrend(
            month   = m,
            income  = round(v["income"],  2),
            expense = round(v["expense"], 2),
            net     = round(v["income"] - v["expense"], 2),
        )
        for m, v in sorted(month_map.items())
    ]


@router.get("/recent", response_model=list[FinancialRecordOut], summary="Last 10 financial records")
def recent_activity(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return (
        db.query(FinancialRecord)
        .filter(FinancialRecord.is_deleted == False)
        .order_by(FinancialRecord.date.desc())
        .limit(10)
        .all()
    )