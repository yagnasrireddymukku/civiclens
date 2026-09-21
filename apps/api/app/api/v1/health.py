"""GET /api/v1/health — liveness check.
GET /api/v1/health/ready — readiness check (Phase 3 onward).

`health` deliberately has no dependency on the database or any other
subsystem: it answers "is the process up," not "is everything ready."

The liveness response shape is mirrored by `packages/types`' `HealthStatus`
(TypeScript) so the frontend and backend agree on the contract without
either hand-copying the other — see docs/API.md §10.
"""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from starlette.responses import JSONResponse

from app.core.db import session as db_session

API_VERSION = "0.1.0"

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    timestamp: str


class ReadinessStatus(BaseModel):
    status: Literal["ready"]
    database: Literal["ok"]


@router.get("/health", response_model=HealthStatus)
def get_health() -> HealthStatus:
    return HealthStatus(
        status="ok",
        service="civiclens-api",
        version=API_VERSION,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/health/ready", response_model=ReadinessStatus)
def get_readiness() -> ReadinessStatus | JSONResponse:
    """Checks the one real dependency introduced in Phase 3: the database.

    Uses its own short-lived connection via `get_engine()` rather than the
    request-scoped `get_db` dependency (docs/API.md §19's DI pattern,
    exercised by future business routes): a readiness probe is testing raw
    connectivity, not doing request work, and a request-scoped session
    that fails mid-transaction would tangle this check's error handling
    with commit/rollback semantics that don't apply here.

    Calls `db_session.get_engine()` through the module (not a
    `from ... import get_engine`) so tests can monkeypatch
    `app.core.db.session.get_engine` and have it actually take effect here.
    """
    try:
        with db_session.get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "NOT_READY",
                    "message": "Database is not reachable.",
                }
            },
        )

    return ReadinessStatus(status="ready", database="ok")
