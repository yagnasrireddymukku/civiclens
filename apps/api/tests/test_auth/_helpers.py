"""Shared fixture-building helpers for auth tests."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.users.enums import UserRole
from app.users.models import User


def make_user(session: Session, **overrides: Any) -> User:
    defaults: dict[str, Any] = dict(
        email=f"test-user-{uuid.uuid4().hex[:8]}@example-test.invalid",
        password_hash=hash_password("Correct-Horse-Battery-Staple"),
        role=UserRole.USER,
        email_notifications_enabled=False,
    )
    defaults.update(overrides)
    user = User(**defaults)
    session.add(user)
    session.flush()
    return user
