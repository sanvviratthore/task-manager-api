"""
services/interfaces.py
Abstract base classes defining contracts for swappable services.
If you need to switch from JWT to sessions, or from in-memory to Redis
rate limiting, implement these interfaces — no route code changes needed.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class AuthServiceBase(ABC):
    """Contract for authentication token operations."""

    @abstractmethod
    def create_access_token(self, data: dict) -> str:
        """Create a short-lived access token."""
        ...

    @abstractmethod
    def create_refresh_token(self, data: dict) -> tuple[str, datetime]:
        """Create a long-lived refresh token. Returns (token, expires_at)."""
        ...

    @abstractmethod
    def decode_token(self, token: str) -> dict:
        """Decode and verify a token. Raises HTTPException on failure."""
        ...

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a plain-text password."""
        ...

    @abstractmethod
    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify a plain password against a hash."""
        ...


class RateLimiterBase(ABC):
    """Contract for rate limiting operations."""

    @abstractmethod
    def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        """
        Check rate limit for a given key.
        Raises HTTPException(429) if limit exceeded.
        """
        ...