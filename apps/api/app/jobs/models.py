"""Government Jobs domain — see docs/DATABASE.md §2.3, docs/ROADMAP.md
Phase 6. The first real CivicLens domain module; its shape is the pattern
Services (Phase 7) and future domains (Schemes, Scholarships) follow.

`Organization`/`Department` (docs/DATABASE.md §2.2) moved to
`app.institutions.models` in Phase 7, once Services needed them too —
see that module's docstring. Job/JobNotification are the evolving facts:
each carries its own `source_id` (`NOT NULL`, `RESTRICT` — a source
can't be deleted out from under a fact that cites it) and a denormalized
`verification_status`/`last_verified_at` pair, mirroring
`search_documents`'s Phase 5 pattern, so "Last verified: DATE" (a hard
product requirement, docs/DATA_GOVERNANCE.md §4) never needs a join. The
`verification_records` audit trail (`app/sources/models.py`) remains the
authoritative history of verification *events*; these columns are a
display-convenience cache of the current state, not a second source of
truth.

`JobVacancy` deliberately carries no provenance of its own — it's an
itemized breakdown of its parent `JobNotification`, inheriting that
notification's source.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.institutions.models import Department, Organization
from app.jobs.enums import EmploymentType, JobNotificationStatus, JobPublicationStatus
from app.sources.enums import VerificationStatus


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The stable conceptual opportunity (e.g. "Sub Inspector of Police,
    Telangana") — distinct from a specific `JobNotification` recruitment
    cycle, since the same job concept recurs across cycles over time
    (docs/DATABASE.md §2.3)."""

    __tablename__ = "jobs"

    slug: Mapped[str] = mapped_column(String(220), nullable=False, unique=True, index=True)
    # The language the content columns below are actually written in —
    # not a translation pairing. This phase does not build a bilingual
    # content model: docs/DATA_GOVERNANCE.md prohibits machine-translating
    # official text, and human-translated summaries are out of this
    # phase's scope (this phase's §17). A job exists in whichever
    # language its source document does; `/te/jobs` honestly shows only
    # `locale="te"` rows rather than a fabricated translation of English
    # ones (mirrors docs/SEARCH.md §7's Telugu-limitation disclosure).
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en", index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType, name="employment_type", native_enum=True), nullable=False
    )
    # Free-text, entity-defined domain classification (e.g. "Group II
    # Services") — deliberately not an enum, matching
    # `search_documents.category`'s existing convention (docs/SEARCH.md
    # §6): no fixed taxonomy exists yet for a single, still-forming
    # domain.
    category: Mapped[str | None] = mapped_column(String(150), nullable=True)
    state_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("states.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Eligibility-relevant fields kept as plain structured columns per
    # docs/ELIGIBILITY_ENGINE.md's data model — this phase does NOT
    # attach `eligibility_rules`/`eligibility_conditions` rows, it only
    # ensures a future one can reference `entity_type="job",
    # entity_id=jobs.id` and read simple structured attributes (age,
    # category, domicile via `state_id` above) without a migration.
    # Qualification/experience stay prose (`_summary` columns): real
    # notification wording ("Bachelor's degree OR equivalent") is rarely
    # a single structured value, and this phase does not build the
    # parsing/normalization that would be needed to make it one.
    min_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qualification_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Text, not a number: a verified figure is rarely a single value
    # (pay bands, grade pay, allowances) — see
    # docs/DATA_GOVERNANCE.md §6 on never fabricating a salary figure.
    # Left null rather than guessed when a source doesn't state one.
    salary_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Browse-friendly current-state label — see module docstring for how
    # this differs from `publication_status` and `JobNotification.status`.
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    publication_status: Mapped[JobPublicationStatus] = mapped_column(
        Enum(JobPublicationStatus, name="job_publication_status", native_enum=True),
        nullable=False,
        default=JobPublicationStatus.DRAFT,
        index=True,
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # postgresql.ENUM (dialect-specific), not the generic sa.Enum: this
    # reuses the `verification_status` type 874e41ffb818 already created
    # — the generic sa.Enum's `create_type=False` isn't reliably honored
    # by Alembic's `create_table` (verified by hand in Phase 5, see
    # app/search/models.py).
    verification_status: Mapped[VerificationStatus] = mapped_column(
        postgresql.ENUM(VerificationStatus, name="verification_status", create_type=False),
        nullable=False,
        default=VerificationStatus.UNVERIFIED,
        index=True,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete: docs/DATABASE.md §0 rule 3 names jobs explicitly as an
    # entity whose retirement must preserve history.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="jobs")
    department: Mapped[Department | None] = relationship(back_populates="jobs")
    notifications: Mapped[list[JobNotification]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="JobNotification.created_at"
    )


class JobNotification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One specific recruitment cycle for a `Job` — a job may have several
    over time (amendments, corrigenda, or an entirely new cycle years
    later), each independently sourced and verified."""

    __tablename__ = "job_notifications"

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_number: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[JobNotificationStatus] = mapped_column(
        Enum(JobNotificationStatus, name="job_notification_status", native_enum=True),
        nullable=False,
        default=JobNotificationStatus.DRAFT,
        index=True,
    )
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    application_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    application_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    correction_window_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    exam_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_vacancies: Mapped[int | None] = mapped_column(Integer, nullable=True)
    official_notification_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    official_application_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

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

    job: Mapped[Job] = relationship(back_populates="notifications")
    vacancies: Mapped[list[JobVacancy]] = relationship(
        back_populates="job_notification", cascade="all, delete-orphan"
    )


class JobVacancy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One itemized post/position within a notification's total vacancy
    count — see module docstring on why this has no provenance of its
    own."""

    __tablename__ = "job_vacancies"

    job_notification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_notifications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    post_name: Mapped[str] = mapped_column(String(200), nullable=False)
    vacancy_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Free text, deliberately not a fixed enum of reservation categories:
    # those vary by state/organization and are a policy taxonomy this
    # module should not hardcode or risk getting stale (kickoff's
    # "reservation/category details where legally appropriate").
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)

    job_notification: Mapped[JobNotification] = relationship(back_populates="vacancies")
