from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
from models import RoleEnum
import re


# ── Auth Schemas ───────────────────────────────────────────────────────────────

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

    @field_validator("username", "password")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty.")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User Schemas ───────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: RoleEnum
    is_active: bool
    created_at: datetime


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


# ── Generic ────────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str

# ──────────────────────────────────────────────────────────────────────────────
# ADD THIS BLOCK to your existing backend/schemas.py
# ──────────────────────────────────────────────────────────────────────────────

from datetime import date as Date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from models import RecordType   # already importable once you add the enum above


# ── Request schemas ────────────────────────────────────────────────────────────

class FinancialRecordCreate(BaseModel):
    amount:   float        = Field(..., gt=0, description="Must be a positive number")
    type:     RecordType
    category: str          = Field(..., min_length=1, max_length=100)
    date:     Date
    notes:    Optional[str] = Field(None, max_length=1000)

    @field_validator("category")
    @classmethod
    def category_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("category cannot be blank")
        return v.strip()


class FinancialRecordUpdate(BaseModel):
    amount:   Optional[float]       = Field(None, gt=0)
    type:     Optional[RecordType]  = None
    category: Optional[str]         = Field(None, min_length=1, max_length=100)
    date:     Optional[Date]        = None
    notes:    Optional[str]         = Field(None, max_length=1000)


# ── Response schemas ───────────────────────────────────────────────────────────

class FinancialRecordOut(BaseModel):
    id:         int
    amount:     float
    type:       RecordType
    category:   str
    date:       Date
    notes:      Optional[str]
    created_by: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PaginatedRecords(BaseModel):
    total:   int
    page:    int
    limit:   int
    records: list[FinancialRecordOut]


# ── Dashboard schemas ──────────────────────────────────────────────────────────

class CategoryTotal(BaseModel):
    category: str
    total:    float


class MonthlyTrend(BaseModel):
    month:    str          # e.g. "2024-03"
    income:   float
    expense:  float
    net:      float


class DashboardSummary(BaseModel):
    total_income:    float
    total_expenses:  float
    net_balance:     float
    category_totals: list[CategoryTotal]
    monthly_trends:  list[MonthlyTrend]
    recent_records:  list[FinancialRecordOut]