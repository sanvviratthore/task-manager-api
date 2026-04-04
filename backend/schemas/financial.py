from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
import re
from models import RecordTypeEnum


class FinancialRecordCreate(BaseModel):
    amount: float
    type: RecordTypeEnum
    category: str
    date: str
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than 0.")
        if v > 10_000_000:
            raise ValueError("Amount is too large.")
        return round(v, 2)

    @field_validator("category")
    @classmethod
    def category_valid(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 100:
            raise ValueError("Category must be 1–100 characters.")
        return v

    @field_validator("date")
    @classmethod
    def date_valid(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Date must be in YYYY-MM-DD format.")
        return v

    @field_validator("notes")
    @classmethod
    def notes_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 500:
            raise ValueError("Notes must be 500 characters or fewer.")
        return v


class FinancialRecordUpdate(BaseModel):
    amount: Optional[float] = None
    type: Optional[RecordTypeEnum] = None
    category: Optional[str] = None
    date: Optional[str] = None
    notes: Optional[str] = None
    version: int  # required for optimistic locking

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v <= 0:
                raise ValueError("Amount must be greater than 0.")
            return round(v, 2)
        return v

    @field_validator("date")
    @classmethod
    def date_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Date must be in YYYY-MM-DD format.")
        return v


class FinancialRecordOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    amount: float
    type: RecordTypeEnum
    category: str
    date: str
    notes: Optional[str]
    user_id: int
    version: int
    created_at: datetime
    created_by: Optional[int]
    updated_at: datetime
    updated_by: Optional[int]


class PaginatedRecords(BaseModel):
    total: int
    page: int
    limit: int
    records: list[FinancialRecordOut]


class CategoryTotal(BaseModel):
    category: str
    total: float


class MonthlyTrend(BaseModel):
    month: str
    income: float
    expense: float
    net: float


class DashboardSummary(BaseModel):
    total_income: float
    total_expenses: float
    net_balance: float
    category_totals: list[CategoryTotal]
    monthly_trends: list[MonthlyTrend]
    recent_records: list[FinancialRecordOut]