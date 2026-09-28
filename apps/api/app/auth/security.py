"""Password hashing and JWT encode/decode — the two cryptographic
primitives ADR-009/docs/SECURITY.md §2 specify. Deliberately the only
module that imports `bcrypt`/`jwt` directly; every other auth module
goes through the functions here.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import Settings
from app.users.enums import UserRole

_TOKEN_TYPE_ACCESS = "access"


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # A malformed/foreign hash (e.g. empty string) — never raise out
        # of an auth check; treat as "does not match."
        return False


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    role: UserRole


def create_access_token(*, settings: Settings, user_id: uuid.UUID, role: UserRole) -> str:
    """Carries only `sub`/`role`/`iat`/`exp`/`type` — never profile
    attributes (docs/DATABASE.md §2.8, SECURITY.md §2's explicit list)."""

    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "type": _TOKEN_TYPE_ACCESS,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(*, settings: Settings, token: str) -> AccessTokenClaims | None:
    """`None` for any invalid/expired/wrong-type token — callers treat
    this identically to "not authenticated," never distinguishing the
    reason to a client (this phase's "fail closed" principle,
    SECURITY.md §1)."""

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != _TOKEN_TYPE_ACCESS:
        return None
    try:
        return AccessTokenClaims(user_id=uuid.UUID(payload["sub"]), role=UserRole(payload["role"]))
    except (KeyError, ValueError):
        return None


def generate_refresh_token_secret() -> str:
    """The raw, one-time-visible refresh token value — only its hash is
    ever persisted (SECURITY.md §2: "stored hashed server-side, never
    plaintext")."""

    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    # A refresh token is already a 48-byte, cryptographically random
    # secret (not a human password) — a fast, unsalted SHA-256 digest is
    # the correct tool here, not bcrypt (which is deliberately slow, for
    # low-entropy human passwords specifically). Storing it non-reversibly
    # still satisfies "never plaintext."
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
