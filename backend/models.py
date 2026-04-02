from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    id          = Column(Integer, primary_key=True, index=True)
    email       = Column(String(255), unique=True, index=True, nullable=False)
    username    = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role        = Column(Enum(RoleEnum), default=RoleEnum.viewer, nullable=False)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    tokens  = relationship("RefreshToken", back_populates="owner", cascade="all, delete")
    records = relationship("FinancialRecord", back_populates="owner", cascade="all, delete")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    token      = Column(String(512), unique=True, index=True, nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked    = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="tokens")


class RecordTypeEnum(str, enum.Enum):
    income  = "income"
    expense = "expense"


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id          = Column(Integer, primary_key=True, index=True)
    amount      = Column(Float, nullable=False)
    type        = Column(Enum(RecordTypeEnum), nullable=False)
    category    = Column(String(100), nullable=False)
    date        = Column(String(10), nullable=False)  # YYYY-MM-DD
    notes       = Column(Text, nullable=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="records")