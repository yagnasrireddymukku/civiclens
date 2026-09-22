"""Government Services domain — see docs/DATABASE.md §10, docs/ROADMAP.md
Phase 7. The second real domain module, following Jobs' (Phase 6) exact
provenance/visibility pattern: `Service` carries its own `source_id`
(`NOT NULL`, `RESTRICT`) and a denormalized `verification_status`/
`last_verified_at` pair, mirroring `search_documents` and `jobs` — see
`app/jobs/models.py`'s module docstring for the fuller rationale, not
repeated here.

`ServiceRequirement`, `RequiredDocument`, and `ApplicationMethod`
deliberately carry no provenance of their own — like `JobVacancy`, each
is an itemized breakdown of its parent `Service`, inheriting that
service's source. `ServiceRequirement` is intentionally light — a type
plus an optional numeric range plus prose — not the eligibility
engine's `attribute`/`operator`/`value` model
(docs/ELIGIBILITY_ENGINE.md, Phase 10's domain): this phase prepares
structured ground for that engine without building it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.institutions.models import Department, Organization
from app.requirements.enums import ApplicationChannelType, DeliveryMode, RequirementType
from app.services.enums import ServiceCategory, ServicePublicationStatus
from app.sources.enums import VerificationStatus

if TYPE_CHECKING:
    # Only for static type-checking — a real top-level import here would
    # be circular (app.documents imports Service for its own `service_id`
    # relationship). SQLAlchemy resolves `Mapped["CivicDocument"]` below
    # at runtime by name against the shared declarative registry instead,
    # once `app.core.db.model_registry` has imported every model module.
    from app.documents.models import CivicDocument


class Service(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A citizen-facing government service (e.g. "Income Certificate
    Issuance") — docs/DATABASE.md §10."""

    __tablename__ = "services"

    slug: Mapped[str] = mapped_column(String(220), nullable=False, unique=True, index=True)
    # See app/jobs/models.py's `locale` field for the "no bilingual
    # content model" rationale — identical here.
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en", index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[ServiceCategory] = mapped_column(
        Enum(ServiceCategory, name="service_category", native_enum=True), nullable=False, index=True
    )
    # Free text, deliberately not an enum — unlike `category` above,
    # "service type" (e.g. "certificate issuance", "benefit
    # disbursement") has no bounded, citizen-facing set worth a fixed
    # taxonomy yet, matching `Job.category`'s existing convention.
    service_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Prose, not a structured audience model: real notification wording
    # ("farmers with landholding under 2 hectares") rarely reduces to a
    # single value — same reasoning as Job.qualification_summary.
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_mode: Mapped[DeliveryMode] = mapped_column(
        Enum(DeliveryMode, name="delivery_mode", native_enum=True), nullable=False
    )
    # Nullable, unlike Job.state_id: a service may be available
    # statewide or nationally, not scoped to one state (this phase's §4.1
    # "state_id where applicable").
    state_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("states.id", ondelete="SET NULL"), nullable=True, index=True
    )
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    official_service_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    application_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Text, not a number — see Job.salary_summary's identical rationale:
    # real fees are often tiered/conditional, and this phase never
    # fabricates a figure a source doesn't state.
    fee_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    processing_time_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    location_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Browse-friendly current-state label, mirroring Job.status /
    # search_documents.status's free-text convention.
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    publication_status: Mapped[ServicePublicationStatus] = mapped_column(
        Enum(ServicePublicationStatus, name="service_publication_status", native_enum=True),
        nullable=False,
        default=ServicePublicationStatus.DRAFT,
        index=True,
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        postgresql.ENUM(VerificationStatus, name="verification_status", create_type=False),
        nullable=False,
        default=VerificationStatus.UNVERIFIED,
        index=True,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete, matching Job's convention (docs/DATABASE.md §0 rule 3).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="services")
    department: Mapped[Department | None] = relationship(back_populates="services")
    requirements: Mapped[list[ServiceRequirement]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )
    required_documents: Mapped[list[RequiredDocument]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )
    application_methods: Mapped[list[ApplicationMethod]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )


class ServiceRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One eligibility-relevant prerequisite — structured just enough
    (type + optional numeric range) for a future Eligibility Engine
    (docs/ELIGIBILITY_ENGINE.md, Phase 10) to read without a migration;
    see module docstring."""

    __tablename__ = "service_requirements"

    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_type: Mapped[RequirementType] = mapped_column(
        Enum(RequirementType, name="requirement_type", native_enum=True), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    min_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_value: Mapped[int | None] = mapped_column(Integer, nullable=True)

    service: Mapped[Service] = relationship(back_populates="requirements")


class RequiredDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One document a citizen typically needs to provide — deliberately
    minimal (name + optional note), extensible toward a future Document
    Intelligence capability (this phase's §24) without committing to its
    shape now.

    `civic_document_id` (Phase 10) is a purely additive, nullable
    `ON DELETE SET NULL` FK to `civic_documents.id` — `NULL` when no
    modeled `CivicDocument` record exists for this requirement yet (free
    text only, today's original behavior, unchanged), set when one does,
    enabling a document's detail page to answer "where is this
    required" without inferring anything from matching names. See
    `app/documents/models.py`'s module docstring for the full
    reasoning."""

    __tablename__ = "service_required_documents"

    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    civic_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("civic_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    service: Mapped[Service] = relationship(back_populates="required_documents")
    civic_document: Mapped[CivicDocument | None] = relationship()


class ApplicationMethod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One channel through which a citizen can apply for/access a
    service."""

    __tablename__ = "service_application_methods"

    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_type: Mapped[ApplicationChannelType] = mapped_column(
        Enum(ApplicationChannelType, name="application_channel_type", native_enum=True),
        nullable=False,
    )
    # Never a guessed/plausible-looking URL (this phase's §11) — null
    # when a source doesn't state one for this channel.
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    service: Mapped[Service] = relationship(back_populates="application_methods")
