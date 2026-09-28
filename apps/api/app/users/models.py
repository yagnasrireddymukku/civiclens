"""User identity and Profile — see docs/DATABASE.md §2.8.

Phase 3 scope was identity storage only: no authentication flows, login,
OAuth, or password reset lived here — `password_hash` was a column
waiting for a future auth module to populate. `app.auth` (Tracking +
Notifications, rescheduled from Phase 12) is that module: it reads/writes
`password_hash` via
`app.auth.security.hash_password`/`verify_password`, but the column and
its nullability (a future OAuth-only user has no local password) were
already decided in Phase 3, unchanged here.

Profile fields are explicitly user-provided only — nothing inferred, per
docs/PRIVACY.md §1. Every field is optional; a user with an empty profile
can still use core search/browse features.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.users.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    # Nullable: a user who only ever authenticates via a future OAuth
    # flow (ADR-009) has no local password.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True), nullable=False, default=UserRole.USER
    )
    # Tracking + Notifications, rescheduled from Phase 12
    # (docs/PRIVACY.md §3: "optional data and communications
    # require explicit, opt-in consent... declinable") — defaults to
    # `False`, never opted in on the user's behalf. A single boolean
    # lives directly on `User` (matching `role`'s precedent) rather than
    # a new one-column preferences table, since there is exactly one
    # channel preference to store today.
    email_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    profile: Mapped[Profile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Profile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    qualification: Mapped[str | None] = mapped_column(String(150), nullable=True)
    state_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("states.id", ondelete="SET NULL"), nullable=True
    )
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL"), nullable=True
    )
    # Sensitive per docs/PRIVACY.md §2 (e.g. reservation category):
    # collected only because a future, real, sourced eligibility rule
    # (docs/ELIGIBILITY_ENGINE.md, docs/ROADMAP.md Phase 10) needs it —
    # never used for analytics or any other purpose.
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped[User] = relationship(back_populates="profile")
