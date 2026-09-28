"""In-process, per-IP sliding-window rate limiting for `/api/v1/ai/*`
only — see `app.core.config.Settings.ai_rate_limit_requests`'s docstring
for why this is a deliberately minimal MVP (no rate-limiting
infrastructure of any kind exists elsewhere in this codebase, verified
by hand) rather than a claim of production-grade abuse prevention.
Module-level state means this resets on process restart and does not
coordinate across multiple server processes/instances — disclosed, not
hidden.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def enforce_ai_rate_limit(request: Request) -> None:
    settings = get_settings()
    window = settings.ai_rate_limit_window_seconds
    limit = settings.ai_rate_limit_requests

    ip = _client_ip(request)
    now = time.monotonic()
    bucket = _hits[ip]
    while bucket and now - bucket[0] > window:
        bucket.popleft()

    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many AI requests. Please wait before trying again.",
            headers={"Retry-After": str(int(window))},
        )
    bucket.append(now)
