"""
services/rate_limiter_service.py
In-memory sliding window rate limiter implementing RateLimiterBase.
To switch to Redis, implement RateLimiterBase with Redis commands
and swap the singleton — no route code changes needed.
"""
from collections import defaultdict, deque
from datetime import datetime, timezone
from fastapi import HTTPException, Request, status

from services.interfaces import RateLimiterBase


class InMemoryRateLimiter(RateLimiterBase):
    """
    Sliding window counter rate limiter backed by in-memory deques.

    Tradeoff: resets on server restart, doesn't work across
    multiple instances. For production swap with RedisRateLimiter.
    """

    def __init__(self):
        self._store: dict[str, deque] = defaultdict(deque)

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = datetime.now(timezone.utc).timestamp()
        window_start = now - window_seconds
        dq = self._store[key]

        # Remove timestamps outside window
        while dq and dq[0] < window_start:
            dq.popleft()

        if len(dq) >= max_requests:
            retry_after = int(dq[0] + window_seconds - now) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Please wait {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        dq.append(now)


# ── Singleton ─────────────────────────────────────────────────────────────────
_limiter = InMemoryRateLimiter()


def _get_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ── Preset FastAPI dependency functions ───────────────────────────────────────
def limit_login(request: Request) -> None:
    """5 attempts per 60 seconds per IP."""
    _limiter.check(f"login:{_get_ip(request)}", max_requests=5, window_seconds=60)


def limit_register(request: Request) -> None:
    """3 registrations per 300 seconds per IP."""
    _limiter.check(f"register:{_get_ip(request)}", max_requests=3, window_seconds=300)


def limit_password_reset(request: Request) -> None:
    """3 reset attempts per 300 seconds per IP."""
    _limiter.check(f"pwd_reset:{_get_ip(request)}", max_requests=3, window_seconds=300)