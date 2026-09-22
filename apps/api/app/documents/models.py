"""Documents & Certificates domain — see docs/DATABASE.md §14,
docs/ROADMAP.md Phase 10. The fourth real domain module, following
Jobs'/Services'/Schemes' exact provenance/visibility pattern:
`CivicDocument` carries its own `source_id` (`NOT NULL`, `RESTRICT`)
and a denormalized `verification_status`/`last_verified_at` pair,
mirroring `search_documents`/`jobs`/`services`/`schemes`.

**The central architectural distinction (this phase's §3/§32)**: a
document that a citizen NEEDS (an itemized requirement attached to some
other record — `RequiredDocument`, `SchemeRequiredDocument`) is a
different concept from the official document/certificate ITSELF
(`CivicDocument` — what an Income Certificate *is*: who issues it, what
it's for, how to get one). Both already existed; only the second one is
new. `CivicDocument` is deliberately named that, not `Document` —
avoiding a generic, collision-prone name for what is a genuinely
first-class citizen-facing record, the same category of thing as `Job`/
`Service`/`Scheme`. The class name is internal; the public API/search
vocabulary still calls it a "document" (`entity_type="document"`,
`/api/v1/documents`), matching what this phase and its routes call the
domain.

**`RequiredDocument`/`SchemeRequiredDocument` gained one nullable
column each, `civic_document_id`** (see `app/services/models.py`,
`app/schemes/models.py`) — a purely additive `ON DELETE SET NULL` FK to
`civic_documents.id`, added to already-shipped tables. This is the
smallest relational design (this phase's §14/§22) that lets a document's
detail page answer "where is this required" without inferring anything
from matching names (explicitly prohibited by §22) or building a
generic polymorphic reference graph (explicitly prohibited by §32): a
required-document row simply points at the real `CivicDocument` record
when a source-backed link exists, and stays `NULL` (free text only,
today's behavior, unchanged) when it doesn't. `DocumentSupportingDocument`
below reuses the identical nullable self-referential pattern — a
document's own supporting-document list can point at *other*
`CivicDocument` rows the same way.

`DocumentRequirement`/`DocumentSupportingDocument`/
`DocumentApplicationMethod` are this domain's own child tables, not
shared ones — same reasoning `ServiceRequirement`/`RequiredDocument`/
`ApplicationMethod` already established, now confirmed by a fourth
consumer. `DocumentRequirement` reuses the shared `RequirementType`
vocabulary; `DocumentApplicationMethod` reuses the shared
`ApplicationChannelType` vocabulary — both from `app.requirements.enums`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.documents.enums import DocumentCategory, DocumentPublicationStatus, DocumentType
from app.institutions.models import Department, Organization
from app.requirements.enums import ApplicationChannelType, DeliveryMode, RequirementType
from app.sources.enums import VerificationStatus

if TYPE_CHECKING:
    from app.services.models import Service


class CivicDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An official citizen-facing document or certificate (e.g. "Income
    Certificate") — docs/DATABASE.md §14. Distinct from a `Service`
    (something a citizen requests/accesses, e.g. "Income Certificate
    Issuance") and from a `Scheme` (a benefit program) — a `CivicDocument`
    describes the record itself, which a `Service` may exist to issue
    (`service_id`, below) and which other domains' `*RequiredDocument`
    rows may reference as something a citizen needs to provide."""

    __tablename__ = "civic_documents"

    slug: Mapped[str] = mapped_column(String(220), nullable=False, unique=True, index=True)
    # See app/jobs/models.py's `locale` field for the "no bilingual
    # content model" rationale — identical here.
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en", index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type", native_enum=True), nullable=False, index=True
    )
    category: Mapped[DocumentCategory] = mapped_column(
        Enum(DocumentCategory, name="document_category", native_enum=True),
        nullable=False,
        index=True,
    )
    # Prose, source-backed only (this phase's §9) — never an invented
    # claim about a document's legal significance.
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Nullable, like Service/Scheme: a document may be issued statewide
    # or nationally, not scoped to one state.
    state_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("states.id", ondelete="SET NULL"), nullable=True, index=True
    )
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    delivery_mode: Mapped[DeliveryMode] = mapped_column(
        postgresql.ENUM(DeliveryMode, name="delivery_mode", create_type=False), nullable=False
    )
    official_document_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    application_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Text, never a fabricated figure — same convention as
    # `Service.fee_summary`/`Job.salary_summary`.
    fee_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    processing_time_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    validity_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    renewal_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # The "obtained through" relationship (this phase's §13) — nullable:
    # not every document is obtained via a modeled `Service` today, and
    # this phase never requires one just to satisfy the field.
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Browse-friendly current-state label, mirroring every other
    # domain's free-text `status` convention.
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    publication_status: Mapped[DocumentPublicationStatus] = mapped_column(
        Enum(DocumentPublicationStatus, name="document_publication_status", native_enum=True),
        nullable=False,
        default=DocumentPublicationStatus.DRAFT,
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

    # Soft delete, matching every other domain's convention
    # (docs/DATABASE.md §0 rule 3).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="civic_documents")
    department: Mapped[Department | None] = relationship(back_populates="civic_documents")
    service: Mapped[Service | None] = relationship()
    requirements: Mapped[list[DocumentRequirement]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    supporting_documents: Mapped[list[DocumentSupportingDocument]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="DocumentSupportingDocument.document_id",
    )
    application_methods: Mapped[list[DocumentApplicationMethod]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One eligibility-relevant prerequisite to *obtain* this document —
    reuses `ServiceRequirement`'s exact shape and the shared
    `RequirementType` vocabulary. Never evaluates ELIGIBLE/NOT_ELIGIBLE/
    INCOMPLETE — that decision belongs to the future Eligibility Engine
    (docs/ELIGIBILITY_ENGINE.md), not this table."""

    __tablename__ = "document_requirements"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("civic_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_type: Mapped[RequirementType] = mapped_column(
        postgresql.ENUM(RequirementType, name="requirement_type", create_type=False),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    min_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_value: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document: Mapped[CivicDocument] = relationship(back_populates="requirements")


class DocumentSupportingDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One document a citizen typically needs to provide *to obtain
    this document* — mirrors `RequiredDocument`'s exact shape, plus one
    addition: `civic_document_id`, a nullable self-referential FK to
    `civic_documents.id` for when that supporting document is itself a
    modeled `CivicDocument` (e.g. a Residence Certificate application
    that lists "Income Certificate" as supporting proof, where an Income
    Certificate `CivicDocument` row exists). `NULL` when no such record
    exists yet — free text only, same as every `*RequiredDocument` table
    today."""

    __tablename__ = "document_supporting_documents"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("civic_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    civic_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("civic_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    document: Mapped[CivicDocument] = relationship(
        back_populates="supporting_documents", foreign_keys=[document_id]
    )
    civic_document: Mapped[CivicDocument | None] = relationship(foreign_keys=[civic_document_id])


class DocumentApplicationMethod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One channel through which a citizen can apply for/obtain this
    document, reusing the shared `ApplicationChannelType` vocabulary."""

    __tablename__ = "document_application_methods"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("civic_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_type: Mapped[ApplicationChannelType] = mapped_column(
        postgresql.ENUM(ApplicationChannelType, name="application_channel_type", create_type=False),
        nullable=False,
    )
    # Never a guessed/plausible-looking URL (this phase's §12) — null
    # when a source doesn't state one for this channel.
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped[CivicDocument] = relationship(back_populates="application_methods")
