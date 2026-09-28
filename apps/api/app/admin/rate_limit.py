"""In-process, per-user sliding-window rate limiting for mutating
`/api/v1/admin/*` routes only — see `Settings.admin_rate_limit_*`'s
docstring for why this deliberately mirrors `app.ai.rate_limit`'s MVP
posture rather than sharing code with it. Module-level state means this
resets on process restart and does not coordinate across multiple
server processes/instances — disclosed, not hidden.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.users.models import User

_hits: dict[str, deque[float]] = defaultdict(deque)


def enforce_admin_rate_limit(current_user: User = Depends(get_current_user)) -> None:
    settings = get_settings()
    window = settings.admin_rate_limit_window_seconds
    limit = settings.admin_rate_limit_requests

    key = str(current_user.id)
    now = time.monotonic()
    bucket = _hits[key]
    while bucket and now - bucket[0] > window:
        bucket.popleft()

    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many administrative actions. Please wait before trying again.",
            headers={"Retry-After": str(int(window))},
        )
    bucket.append(now)
