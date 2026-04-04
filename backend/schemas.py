from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from models import RoleEnum, RecordTypeEnum
import re


# ── Auth ───────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3–50 characters.")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username may only contain letters, numbers, _ and -.")
        return v

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(v) > 128:
            raise ValueError("Password must be 128 characters or fewer.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit.")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── UserSession ────────────────────────────────────────────────────────────────

class UserSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: Optional[str]
    user_agent: Optional[str]
    expires_at: datetime
    revoked: bool
    created_at: datetime


# ── User ───────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: RoleEnum
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3–50 characters.")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username may only contain letters, numbers, _ and -.")
        return v


class RoleUpdate(BaseModel):
    role: RoleEnum


# ── FinancialRecord ────────────────────────────────────────────────────────────

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
    version: int  # Required for optimistic locking

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
    model_config = ConfigDict(from_attributes=True)

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
    total:   int
    page:    int
    limit:   int
    records: list[FinancialRecordOut]

# ── ADD THESE to the bottom of backend/schemas.py (before MessageResponse) ────

class PaginatedRecords(BaseModel):
    total:   int
    page:    int
    limit:   int
    records: list[FinancialRecordOut]


class CategoryTotal(BaseModel):
    category: str
    total:    float


class MonthlyTrend(BaseModel):
    month:   str    # "YYYY-MM"
    income:  float
    expense: float
    net:     float


class DashboardSummary(BaseModel):
    total_income:    float
    total_expenses:  float
    net_balance:     float
    category_totals: list[CategoryTotal]
    monthly_trends:  list[MonthlyTrend]
    recent_records:  list[FinancialRecordOut]


# ── Generic ────────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str