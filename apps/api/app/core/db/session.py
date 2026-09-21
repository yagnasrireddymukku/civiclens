"""Engine/session lifecycle and the FastAPI database dependency.

Both `get_engine`/`get_sessionmaker` are lazily cached: constructing an
`Engine` does not open a connection (SQLAlchemy connects on first use), so
the app can still boot with no database reachable — a real connection is
only attempted the first time a request actually exercises `get_db`. This
preserves the Phase 1 rule that the app must not require a live database
just to start.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
        # Bounds both connection establishment and any single statement to
        # a few seconds. Verified necessary by hand: killing the database
        # process out from under a running app produced a readiness check
        # (and, absent this, any query) that hung indefinitely rather than
        # failing — a stale pooled connection or a half-closed socket has
        # no natural timeout of its own. Values are generous for normal
        # queries at this phase's scale, not tuned for a specific SLA.
        connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False
    )


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request.

    Convention (docs/DATABASE.md, this phase's transaction-management
    rule): the request boundary is the transaction boundary. A route/
    service that completes without raising gets its work committed here;
    any exception rolls the whole request back. Application code should
    not call `session.commit()` itself — that would create a transaction
    boundary narrower than the request and make partial-commit bugs
    possible.
    """
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
