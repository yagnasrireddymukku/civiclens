"""User identity and Profile — see docs/DATABASE.md §2.8.

Phase 3 scope is identity storage only: no authentication flows, login,
OAuth, password reset, or session logic live here (those are ADR-009 /
docs/ROADMAP.md Phase 15 concerns) — `password_hash` is a column for a
future auth module to populate, not something this phase computes.

Profile fields are explicitly user-provided only — nothing inferred, per
docs/PRIVACY.md §1. Every field is optional; a user with an empty profile
can still use core search/browse features.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String
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
