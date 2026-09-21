"""Tests the `get_db` FastAPI dependency's transaction-boundary contract
directly (app/core/db/session.py): commits on success, rolls back on
exception. Uses the real test database rather than a mock, per
docs/TESTING.md §3 — this is exactly the kind of behavior a mock session
would let pass without proving anything.
"""

from collections.abc import Generator

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

import app.core.db.session as db_session_module
from app.geography.enums import StateStatus
from app.geography.models import State


@pytest.fixture
def patched_get_db(migrated_engine: Engine, monkeypatch: pytest.MonkeyPatch):
    """Points the real `get_db` dependency at the test database instead
    of the settings-configured one, without changing its logic at all."""
    test_sessionmaker = sessionmaker(
        bind=migrated_engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    monkeypatch.setattr(db_session_module, "get_sessionmaker", lambda: test_sessionmaker)
    return db_session_module.get_db


def _state_count(engine: Engine, code: str) -> int:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT COUNT(*) FROM states WHERE code = :code"), {"code": code}
        ).scalar()


def _cleanup_state(engine: Engine, code: str) -> None:
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM states WHERE code = :code"), {"code": code})


def test_get_db_commits_on_successful_completion(patched_get_db, migrated_engine: Engine) -> None:
    generator: Generator[Session, None, None] = patched_get_db()
    session = next(generator)
    session.add(
        State(
            name="Commit Test State",
            code="ZC",
            slug="commit-test-state",
            status=StateStatus.PLANNED,
        )
    )

    # Simulate the request completing without error, as FastAPI would.
    with pytest.raises(StopIteration):
        next(generator)

    try:
        assert _state_count(migrated_engine, "ZC") == 1
    finally:
        _cleanup_state(migrated_engine, "ZC")


def test_get_db_rolls_back_on_exception(patched_get_db, migrated_engine: Engine) -> None:
    generator: Generator[Session, None, None] = patched_get_db()
    session = next(generator)
    session.add(
        State(
            name="Rollback Test State",
            code="ZR",
            slug="rollback-test-state",
            status=StateStatus.PLANNED,
        )
    )

    # Simulate the request raising, as FastAPI would propagate a route
    # exception back through the dependency generator.
    with pytest.raises(RuntimeError):
        generator.throw(RuntimeError("simulated route failure"))

    assert _state_count(migrated_engine, "ZR") == 0
