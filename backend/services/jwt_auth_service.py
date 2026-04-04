"""
services/jwt_auth_service.py
Concrete JWT implementation of AuthServiceBase.
To switch to session-based auth, implement AuthServiceBase differently
and swap the dependency — no route code changes needed.
"""
from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError as JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status
import os
from dotenv import load_dotenv

from services.interfaces import AuthServiceBase

load_dotenv()

SECRET_KEY                  = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
ALGORITHM                   = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS   = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class JWTAuthService(AuthServiceBase):
    """JWT-based authentication service."""

    def __init__(self):
        self._pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__ident="2b",
        )

    def create_access_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def create_refresh_token(self, data: dict) -> tuple[str, datetime]:
        to_encode = data.copy()
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expires_at, "type": "refresh"})
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return token, expires_at

    def decode_token(self, token: str) -> dict:
        try:
            return jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"verify_exp": True},
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def hash_password(self, password: str) -> str:
        return self._pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return self._pwd_context.verify(plain, hashed)


# ── Singleton instance used across the app ────────────────────────────────────
jwt_auth_service = JWTAuthService()