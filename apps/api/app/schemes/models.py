"""Government Schemes domain — see docs/DATABASE.md §12, docs/ROADMAP.md
Phase 8. The third real domain module, following Jobs' (Phase 6) and
Services' (Phase 7) exact provenance/visibility pattern: `Scheme`
carries its own `source_id` (`NOT NULL`, `RESTRICT`) and a denormalized
`verification_status`/`last_verified_at` pair, mirroring
`search_documents`/`jobs`/`services` — see `app/jobs/models.py`'s module
docstring for the fuller rationale, not repeated here.

Scheme vs. Service (this phase's §3): a `Service` is something a citizen
requests/accesses (issuance, a certificate, a transaction); a `Scheme` is
a benefit/support program a citizen may be eligible for (financial
assistance, a subsidy, a scholarship, a pension, insurance, or
livelihood/agricultural/housing/education/healthcare/employment
support). Both are citizen-facing government offerings, but a scheme
additionally carries *benefit* information (`SchemeBenefit`) that a
service has no equivalent of.

§26/§27 decision (documented once here, not repeated per table):
`SchemeRequirement` reuses the shared `RequirementType` vocabulary
(`app.requirements.enums`, extracted from `app.services.enums` earlier
in this phase) but is its own table, not a shared one — same reasoning
`ServiceRequirement` already established, now confirmed by a second
consumer. `SchemeRequiredDocument`/`SchemeApplicationMethod` are
likewise Scheme-owned tables mirroring `RequiredDocument`/
`ApplicationMethod`'s exact shape rather than a shared polymorphic
table: introducing one now would require migrating Phase 7's
already-shipped `service_required_documents`/`service_application_methods`
tables for a theoretical future benefit, which this phase's "preserve
backward compatibility" instruction and CLAUDE.md rules 9/12/22 counsel
against. Unlike `RequirementType`/`ApplicationChannelType`,
`RequiredDocument` has no shared *vocabulary* to extract either (no
`DocumentType` enum exists) — there is nothing here to move, only
tables to (deliberately) not share.

`SchemeRelatedService` models the Scheme<->Service relationship (this
phase's §11) as the smallest structure that supports it: a plain join
table would work for the relationship alone, but this phase's fixture
guidance (§25) wants a documented reason a scheme and service are
related (e.g. "apply for this certificate first"), which a bare
`secondary=` association table can't carry — so it's one small mapped
class with a `note` column instead, not a full many-to-many with its
own additional infrastructure.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.institutions.models import Department, Organization
from app.requirements.enums import ApplicationChannelType, RequirementType
from app.schemes.enums import BenefitType, SchemeCategory, SchemePublicationStatus
from app.sources.enums import VerificationStatus

if TYPE_CHECKING:
    from app.services.models import Service


class Scheme(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A citizen-facing government scheme (e.g. "Old Age Pension
    Scheme") — docs/DATABASE.md §12."""

    __tablename__ = "schemes"

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
    category: Mapped[SchemeCategory] = mapped_column(
        Enum(SchemeCategory, name="scheme_category", native_enum=True), nullable=False, index=True
    )
    # Prose, not a structured beneficiary model — same reasoning as
    # `Service.target_audience`: real beneficiary wording ("women-headed
    # households below the poverty line") rarely reduces to one value.
    # The *structured* half of the eligibility foundation this phase's
    # §7/§8 asks for is `SchemeRequirement` below, not this field.
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nullable, like Service.state_id: a scheme may be available
    # statewide or nationally, not scoped to one state.
    state_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("states.id", ondelete="SET NULL"), nullable=True, index=True
    )
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    official_scheme_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    application_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Browse-friendly current-state label, mirroring Job.status /
    # Service.status's free-text convention.
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    publication_status: Mapped[SchemePublicationStatus] = mapped_column(
        Enum(SchemePublicationStatus, name="scheme_publication_status", native_enum=True),
        nullable=False,
        default=SchemePublicationStatus.DRAFT,
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

    # Soft delete, matching Job/Service's convention (docs/DATABASE.md
    # §0 rule 3).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="schemes")
    department: Mapped[Department | None] = relationship(back_populates="schemes")
    benefits: Mapped[list[SchemeBenefit]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )
    requirements: Mapped[list[SchemeRequirement]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )
    required_documents: Mapped[list[SchemeRequiredDocument]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )
    application_methods: Mapped[list[SchemeApplicationMethod]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )
    related_services: Mapped[list[SchemeRelatedService]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )


class SchemeBenefit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One structured piece of benefit information (this phase's §6) —
    a type plus prose, never a fabricated amount: `amount_summary` is
    populated only when a source states a figure, same convention as
    `Service.fee_summary`."""

    __tablename__ = "scheme_benefits"

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    benefit_type: Mapped[BenefitType] = mapped_column(
        Enum(BenefitType, name="benefit_type", native_enum=True), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    frequency_summary: Mapped[str | None] = mapped_column(String(150), nullable=True)

    scheme: Mapped[Scheme] = relationship(back_populates="benefits")


class SchemeRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One eligibility-relevant prerequisite — the structured half of
    this phase's §7/§8 beneficiary-profile/eligibility-foundation
    requirement, reusing `ServiceRequirement`'s exact shape and the
    shared `RequirementType` vocabulary (see module docstring). Never
    evaluates ELIGIBLE/NOT_ELIGIBLE/INCOMPLETE — that decision belongs
    to the future Eligibility Engine (docs/ELIGIBILITY_ENGINE.md, Phase
    10), not this table."""

    __tablename__ = "scheme_requirements"

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_type: Mapped[RequirementType] = mapped_column(
        postgresql.ENUM(RequirementType, name="requirement_type", create_type=False),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    min_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_value: Mapped[int | None] = mapped_column(Integer, nullable=True)

    scheme: Mapped[Scheme] = relationship(back_populates="requirements")


class SchemeRequiredDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One document a citizen typically needs to provide — mirrors
    `app.services.models.RequiredDocument`'s exact shape (see module
    docstring's §26 note on why this stays its own table)."""

    __tablename__ = "scheme_required_documents"

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    scheme: Mapped[Scheme] = relationship(back_populates="required_documents")


class SchemeApplicationMethod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One channel through which a citizen can apply for/access a
    scheme, reusing the shared `ApplicationChannelType` vocabulary (see
    module docstring)."""

    __tablename__ = "scheme_application_methods"

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_type: Mapped[ApplicationChannelType] = mapped_column(
        postgresql.ENUM(ApplicationChannelType, name="application_channel_type", create_type=False),
        nullable=False,
    )
    # Never a guessed/plausible-looking URL (this phase's §10) — null
    # when a source doesn't state one for this channel.
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    scheme: Mapped[Scheme] = relationship(back_populates="application_methods")


class SchemeRelatedService(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Links a `Scheme` to a related `Service` (this phase's §11) — e.g.
    a service a citizen typically completes before or while applying for
    the scheme. `note` records *why* they're related when a source
    states it; deliberately a small mapped class rather than a bare
    `secondary=` table, since it needs that extra column (see module
    docstring)."""

    __tablename__ = "scheme_related_services"
    __table_args__ = (
        UniqueConstraint(
            "scheme_id", "service_id", name="uq_scheme_related_services_scheme_service"
        ),
    )

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    scheme: Mapped[Scheme] = relationship(back_populates="related_services")
    service: Mapped[Service] = relationship()
