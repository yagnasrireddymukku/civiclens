"""GET /api/v1/health — liveness check.

Deliberately has no dependency on the database or any other subsystem: it
answers "is the process up," not "is everything ready." A distinct
readiness probe (checking DB connectivity) is deferred to
docs/ROADMAP.md Phase 3, once there is a database dependency to check —
adding one now would just duplicate this endpoint.

The response shape is mirrored by `packages/types`' `HealthStatus`
(TypeScript) so the frontend and backend agree on the contract without
either hand-copying the other — see docs/API.md §10.
"""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

API_VERSION = "0.1.0"

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    timestamp: str


@router.get("/health", response_model=HealthStatus)
def get_health() -> HealthStatus:
    return HealthStatus(
        status="ok",
        service="civiclens-api",
        version=API_VERSION,
        timestamp=datetime.now(UTC).isoformat(),
    )
