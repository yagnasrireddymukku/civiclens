"""Institutions — Organization, Department — see docs/DATABASE.md §2.2.

Extracted from `app.jobs` in Phase 7: these were always conceptually
separate from Jobs (§2.2 "Institutions" vs §2.3 "Opportunities" have been
distinct sections since Phase 0), just implemented inside `app/jobs/` in
Phase 6 because Jobs was the only consumer yet. Phase 7's Services domain
needs the same organizations/departments, and importing them from
`app.jobs.models` would be exactly the cross-module reach-around
CLAUDE.md rule 10 prohibits — so they move to their own module instead,
the same way `app/geography/` already serves every domain module
without any one of them owning it.

This is a model-layer move only: the `organizations`/`departments`
tables and their columns are unchanged from Phase 6 (verified via
`alembic check` showing no diff after the move) — no new migration.

Treated as administrative reference data, the same way geography
(`app/geography/models.py`) is — no `source_id`: an organization's or
department's own existence/name isn't a fact requiring per-row
provenance the way a specific job or service listing is.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.institutions.enums import OrganizationType

if TYPE_CHECKING:
    # Only for static type-checking — a real top-level import here would
    # be circular (app.jobs/app.services import Organization/Department
    # from this module). SQLAlchemy resolves the `Mapped[list["Job"]]`/
    # `Mapped[list["Service"]]` relationship targets below at runtime by
    # name against the shared declarative registry instead, once
    # `app.core.db.model_registry` has imported every model module.
    from app.jobs.models import Job
    from app.services.models import Service


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A recruiting board, university, corporation, or other institution
    (e.g. APPSC, TSPSC) that issues jobs, services, or (in future
    phases) schemes/scholarships."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    org_type: Mapped[OrganizationType] = mapped_column(
        Enum(OrganizationType, name="organization_type", native_enum=True), nullable=False
    )
    # Nullable: a central/national body isn't scoped to one state.
    state_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("states.id", ondelete="SET NULL"), nullable=True, index=True
    )
    website_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    jobs: Mapped[list[Job]] = relationship(back_populates="organization")
    services: Mapped[list[Service]] = relationship(back_populates="organization")


class Department(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A government department issuing recruitment, services, or (in
    future phases) schemes — may or may not sit under a parent
    `Organization` (e.g. a state's "Home Department" often issues its
    own notices directly)."""

    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_departments_organization_name"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    state_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("states.id", ondelete="SET NULL"), nullable=True, index=True
    )

    jobs: Mapped[list[Job]] = relationship(back_populates="department")
    services: Mapped[list[Service]] = relationship(back_populates="department")
