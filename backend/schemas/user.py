from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
import re
from models import RoleEnum


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

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