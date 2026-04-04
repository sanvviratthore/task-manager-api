from sqlalchemy import Column, Integer, Float, String, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from database import Base
from models.user import AuditMixin


class RecordTypeEnum(str, enum.Enum):
    income  = "income"
    expense = "expense"


class FinancialRecord(AuditMixin, Base):
    __tablename__ = "financial_records"

    id       = Column(Integer, primary_key=True, index=True)
    amount   = Column(Float, nullable=False)
    type     = Column(Enum(RecordTypeEnum), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    date     = Column(String(10), nullable=False, index=True)   # YYYY-MM-DD
    notes    = Column(Text, nullable=True)
    user_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    version  = Column(Integer, default=1, nullable=False)

    owner = relationship("User", back_populates="records", foreign_keys=[user_id])