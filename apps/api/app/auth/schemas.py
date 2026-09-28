"""Request/response contract for /api/v1/auth — see docs/API.md."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.users.enums import UserRole

# A floor, not a full strength policy (entropy meters, breach-list
# checks, etc. are Phase 15 hardening concerns) — long enough to rule
# out trivially weak passwords without inventing a complex, hard-to-
# maintain-correctly policy this phase doesn't need.
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 200

# A deliberately simple, pragmatic format check (one "@", a non-empty
# local/domain part, a "." in the domain) rather than a full RFC 5322
# validator — avoids adding `pydantic[email]` (`email-validator` +
# `dnspython`, CLAUDE.md rule 13) for a check this phase only needs to
# catch obvious typos with, not exhaustively validate deliverability.
_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(pattern=_EMAIL_PATTERN, max_length=320)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(pattern=_EMAIL_PATTERN, max_length=320)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class UserSummary(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    email_notifications_enabled: bool


class UpdateNotificationPreferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_notifications_enabled: bool


class AuthResponse(BaseModel):
    """Returned by register/login/refresh. `csrf_token` mirrors the
    non-httpOnly cookie of the same value — handed back in the body too
    so a freshly-loaded frontend can read it without a separate
    document.cookie parse (app/auth/cookies.py sets both)."""

    user: UserSummary
    csrf_token: str
