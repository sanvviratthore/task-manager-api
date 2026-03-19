"""
Simple in-memory sliding-window rate limiter.
For production, swap the store with Redis via slowapi or similar.
"""
from collections import defaultdict, deque
from datetime import datetime, timezone
from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self):
        # { key: deque of timestamps }
        self._store: dict[str, deque] = defaultdict(deque)

    def _get_key(self, request: Request, identifier: str) -> str:
        ip = request.client.host if request.client else "unknown"
        return f"{identifier}:{ip}"

    def check(
        self,
        request: Request,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        """
        Raise 429 if the caller has exceeded max_requests
        within the last window_seconds.
        """
        key = self._get_key(request, identifier)
        now = datetime.now(timezone.utc).timestamp()
        window_start = now - window_seconds

        dq = self._store[key]

        # Remove timestamps outside the window
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


# Singleton used across routers
limiter = RateLimiter()


# ── Preset limiters for sensitive endpoints ────────────────────────────────────
def limit_login(request: Request):
    """5 attempts per 60 seconds per IP."""
    limiter.check(request, "login", max_requests=5, window_seconds=60)

def limit_register(request: Request):
    """3 registrations per 300 seconds per IP."""
    limiter.check(request, "register", max_requests=3, window_seconds=300)

def limit_password_reset(request: Request):
    """3 reset attempts per 300 seconds per IP."""
    limiter.check(request, "password_reset", max_requests=3, window_seconds=300)
