"""
models.py
SQLAlchemy ORM models.

Audit fields on all mutable models:
  created_at, created_by, updated_at, updated_by

Optimistic locking:
  version field on FinancialRecord prevents concurrent update conflicts.

UserSession replaces bare RefreshToken — tracks device, IP, user agent.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Enum, Float, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


# ── Enums ──────────────────────────────────────────────────────────────────────

class RoleEnum(str, enum.Enum):
    admin   = "admin"
    analyst = "analyst"
    viewer  = "viewer"


class RecordTypeEnum(str, enum.Enum):
    income  = "income"
    expense = "expense"


# ── Audit mixin ────────────────────────────────────────────────────────────────

class AuditMixin:
    """
    Reusable audit fields for all mutable models.
    created_by / updated_by store the user ID who made the change.
    Provides a full audit trail for compliance and debugging.
    """
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(Integer, nullable=True)   # user_id of creator
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(Integer, nullable=True)   # user_id of last updater


# ── User ───────────────────────────────────────────────────────────────────────

class User(AuditMixin, Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    username        = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(Enum(RoleEnum), default=RoleEnum.viewer, nullable=False)
    is_active       = Column(Boolean, default=True)

    sessions = relationship("UserSession", back_populates="owner", cascade="all, delete")
    records  = relationship("FinancialRecord", back_populates="owner", cascade="all, delete",
                            foreign_keys="FinancialRecord.user_id")


# ── UserSession ────────────────────────────────────────────────────────────────

class UserSession(Base):
    """
    Replaces bare RefreshToken table.
    Tracks device, IP, user agent per session for security visibility.
    Allows users to see all active sessions and revoke specific devices.
    """
    __tablename__ = "user_sessions"

    id         = Column(Integer, primary_key=True, index=True)
    token      = Column(String(512), unique=True, index=True, nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked    = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="sessions")


# ── FinancialRecord ────────────────────────────────────────────────────────────

class FinancialRecord(AuditMixin, Base):
    """
    Financial entry (income or expense).

    Optimistic locking via `version` field:
      On update, client must send the current version.
      If version doesn't match, the record was modified concurrently -> 409 Conflict.
      Prevents lost updates when two users edit the same record simultaneously.
    """
    __tablename__ = "financial_records"

    id       = Column(Integer, primary_key=True, index=True)
    amount   = Column(Float, nullable=False)
    type     = Column(Enum(RecordTypeEnum), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    date     = Column(String(10), nullable=False, index=True)   # YYYY-MM-DD
    notes    = Column(Text, nullable=True)
    user_id  = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Optimistic locking — incremented on every update
    version  = Column(Integer, default=1, nullable=False)

    owner = relationship("User", back_populates="records", foreign_keys=[user_id])