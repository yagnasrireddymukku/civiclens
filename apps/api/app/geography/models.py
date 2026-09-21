"""Geography: State, District, Constituency — see docs/DATABASE.md §2.1.

State-agnostic by construction (docs/ARCHITECTURE.md §3): no state is
hardcoded anywhere in this module. Andhra Pradesh and Telangana, when
loaded, are ordinary rows with `status="active"`; every other Indian
state can exist as a `status="planned"` row from day one, or be added
later, without a schema or code change.

Slug fields are this phase's addition beyond docs/DATABASE.md §2.1's
terse field list, per this phase's explicit "public identifiers" scope:
public-facing URLs (docs/SEO.md's `/representatives/{state}/{constituency}`
pattern) need a stable, unique-in-scope identifier. Scoping:
state slug is globally unique; district and constituency slugs are
unique within their parent state (a constituency slug is additionally
scoped by type, since an assembly and a parliamentary constituency in the
same state may share a name).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.geography.enums import ConstituencyType, StateStatus


class State(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "states"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, unique=True, index=True)
    status: Mapped[StateStatus] = mapped_column(
        Enum(StateStatus, name="state_status", native_enum=True),
        nullable=False,
        default=StateStatus.PLANNED,
    )

    districts: Mapped[list[District]] = relationship(
        back_populates="state", cascade="all, delete-orphan"
    )
    constituencies: Mapped[list[Constituency]] = relationship(
        back_populates="state", cascade="all, delete-orphan"
    )


class District(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "districts"
    __table_args__ = (
        UniqueConstraint("state_id", "code", name="uq_districts_state_code"),
        UniqueConstraint("state_id", "slug", name="uq_districts_state_slug"),
    )

    state_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("states.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False)

    state: Mapped[State] = relationship(back_populates="districts")
    constituencies: Mapped[list[Constituency]] = relationship(back_populates="district")


class Constituency(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "constituencies"
    __table_args__ = (
        UniqueConstraint("state_id", "type", "slug", name="uq_constituencies_state_type_slug"),
    )

    state_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("states.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nullable: some constituencies span multiple districts or aren't
    # meaningfully scoped to one — see docs/DATABASE.md §2.1.
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    type: Mapped[ConstituencyType] = mapped_column(
        Enum(ConstituencyType, name="constituency_type", native_enum=True), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(170), nullable=False)

    state: Mapped[State] = relationship(back_populates="constituencies")
    district: Mapped[District | None] = relationship(back_populates="constituencies")
