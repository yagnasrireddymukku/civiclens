"""Auth domain logic — registration, login, and refresh-token rotation
(ADR-009, docs/SECURITY.md §2). The only module that queries/writes
`users.password_hash` or `refresh_tokens`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.models import RefreshToken
from app.auth.security import (
    create_access_token,
    generate_refresh_token_secret,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.core.config import Settings
from app.users.enums import UserRole
from app.users.models import User


class EmailAlreadyRegisteredError(Exception):
    pass


class RefreshTokenError(Exception):
    """Raised for any invalid/expired/replayed refresh token — the
    route layer maps every case to an identical 401, never revealing
    which (this phase's "fail closed" principle, SECURITY.md §1)."""


def register_user(session: Session, *, email: str, password: str) -> User:
    existing = session.query(User).filter(func.lower(User.email) == email.lower()).one_or_none()
    if existing is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(email=email, password_hash=hash_password(password), role=UserRole.USER)
    session.add(user)
    session.flush()
    return user


def authenticate_user(session: Session, *, email: str, password: str) -> User | None:
    """`None` for "no such user" *or* "wrong password" *or* "OAuth-only
    account with no local password" — never distinguishing which to the
    caller (timing/enumeration hygiene)."""

    user = session.query(User).filter(func.lower(User.email) == email.lower()).one_or_none()
    if user is None or user.password_hash is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str  # raw value — the only time it's ever visible; only its hash is persisted
    refresh_expires_at: datetime


def issue_token_pair(
    session: Session, *, settings: Settings, user: User, family_id: uuid.UUID | None = None
) -> TokenPair:
    """Starts a new rotation family when `family_id` is omitted (login);
    continues an existing one when called from `rotate_refresh_token`."""

    resolved_family_id = family_id or uuid.uuid4()
    raw_refresh_token = generate_refresh_token_secret()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)

    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            family_id=resolved_family_id,
            expires_at=expires_at,
        )
    )
    access_token = create_access_token(settings=settings, user_id=user.id, role=user.role)
    return TokenPair(
        access_token=access_token, refresh_token=raw_refresh_token, refresh_expires_at=expires_at
    )


def rotate_refresh_token(
    session: Session, *, settings: Settings, raw_refresh_token: str
) -> tuple[User, TokenPair]:
    """Rotation with replay detection (SECURITY.md §2): presenting a
    refresh token that has already been rotated away (`revoked_at` set)
    revokes its *entire* family before raising — a stolen, already-used
    token can never be used again, and neither can the legitimate
    session it was stolen from, forcing a fresh login."""

    token_hash = hash_refresh_token(raw_refresh_token)
    stored = session.query(RefreshToken).filter_by(token_hash=token_hash).one_or_none()
    if stored is None:
        raise RefreshTokenError("Refresh token not recognized.")

    now = datetime.now(UTC)
    if stored.revoked_at is not None:
        session.query(RefreshToken).filter(
            RefreshToken.family_id == stored.family_id, RefreshToken.revoked_at.is_(None)
        ).update({"revoked_at": now})
        raise RefreshTokenError("Refresh token reuse detected; session family revoked.")
    if stored.expires_at < now:
        raise RefreshTokenError("Refresh token expired.")

    user = session.get(User, stored.user_id)
    if user is None:
        raise RefreshTokenError("User no longer exists.")

    stored.revoked_at = now
    new_pair = issue_token_pair(session, settings=settings, user=user, family_id=stored.family_id)
    return user, new_pair


def revoke_refresh_token(session: Session, *, raw_refresh_token: str) -> None:
    """Logout — revokes only this one token (the current, still-valid
    end of its rotation chain), not the whole history."""

    token_hash = hash_refresh_token(raw_refresh_token)
    stored = session.query(RefreshToken).filter_by(token_hash=token_hash).one_or_none()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
