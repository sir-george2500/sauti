"""In-memory fixed-window rate limiter (rent-rwanda pattern).

Swap for a shared store when running more than one node.
Keys: user id when authenticated, else first hop of X-Forwarded-For / client host.
"""
from __future__ import annotations

import threading
import time

from fastapi import Request

from sauti.errors import ApiError


class RateLimiter:
    def __init__(self, window_s: int = 60, default_max: int = 10):
        self.window_s = window_s
        self.default_max = default_max
        self._lock = threading.Lock()
        self._buckets: dict[str, tuple[int, int]] = {}  # key -> (window_start, count)

    def check(self, key: str, max_requests: int | None = None) -> bool:
        """Return True if allowed, False if over the cap for the current window."""
        cap = max_requests if max_requests is not None else self.default_max
        now = int(time.time())
        window_start = now - (now % self.window_s)
        with self._lock:
            start, count = self._buckets.get(key, (window_start, 0))
            if start != window_start:
                start, count = window_start, 0
            count += 1
            self._buckets[key] = (start, count)
            return count <= cap

    def enforce(self, key: str, max_requests: int | None = None) -> None:
        if not self.check(key, max_requests):
            raise ApiError(429, "RATE_LIMITED", "Too many requests, slow down.")


def client_key(
    request: Request, user_id: str | None = None, trust_forwarded_for: bool = False
) -> str:
    if user_id:
        return f"u:{user_id}"
    # X-Forwarded-For is attacker-controlled unless a proxy we operate sets it;
    # only key on it when the deployment says so (TRUST_PROXY_HEADERS=1).
    if trust_forwarded_for:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return f"ip:{fwd.split(',')[0].strip()}"
    return f"ip:{request.client.host if request.client else 'unknown'}"
