"""Eligibility Engine domain — see docs/DATABASE.md §15, docs/ROADMAP.md
Phase 11 (rescheduled from the original Phase 10 slot — see
[ROADMAP.md](../../../../docs/ROADMAP.md)'s rescheduling note).

**Deviates from the `eligibility_rules(entity_type, entity_id, ...)`
polymorphic sketch** in docs/DATABASE.md §2.4 and docs/ELIGIBILITY_ENGINE.md
§2. That sketch predates this phase's actual implementation and was never
an ADR — ADR-007 only commits to "deterministic rule engine, DB-defined
rules, no LLM in the decision path," not to a specific FK shape. Phase 10
already established the precedent for deviating from an old placeholder
sketch when a small, fixed entity-type set makes a real foreign key
possible: it rejected `entity_documents` (a polymorphic join table) for
two additive `civic_document_id` columns on the two known parent tables.
The same reasoning applies here, at a larger scale: `EligibilityRule`
carries three nullable FKs (`job_id`/`scheme_id`/`service_id`, each
`ON DELETE CASCADE`) instead of an unenforceable `entity_type`+`entity_id`
pair, with a `CHECK` constraint requiring exactly one to be set. This
gives real referential integrity (a rule can never point at a deleted or
nonexistent row) and automatic cleanup if the parent entity is removed,
at the cost of a migration if a fourth entity type is ever added — judged
the better trade since CLAUDE.md rule 12 counsels against building for
hypothetical future scale, and this phase's kickoff names exactly three
entity kinds (jobs, schemes/scholarships, services). Documents are
deliberately excluded — a `CivicDocument` isn't itself something a
citizen is eligible/not-eligible for (see `app.eligibility.enums`).

**`EligibilityCondition` is deliberately separate from
`SchemeRequirement`/`ServiceRequirement`/`DocumentRequirement`.** Those
tables stay exactly as they are — informational, prose-first, a bounded
`requirement_type` plus an optional integer range, never evaluated. This
phase's kickoff explicitly asks that informational requirements and
machine-evaluable criteria stay distinguished; folding `attribute`/
`operator`/typed-value columns into the existing `*_requirements` tables
would blur that line and would force every existing (already-shipped,
prose-heavy) row to somehow become machine-evaluable. `EligibilityRule`/
`EligibilityCondition` are new, additive tables that reference an entity
directly — they do not touch `scheme_requirements` et al. at all.

**Evaluability is stricter than the standard display-visibility rule.**
Every other domain treats `VERIFIED` and `NEEDS_REVIEW` as visible for
*display*. This phase's kickoff explicitly asks that "unverified, expired,
or review-required rules must not silently produce authoritative
outcomes" — stricter than display visibility, since an eligibility verdict
is a claim of fact, not just informational content. `is_rule_evaluable()`
in `app.eligibility.service` therefore requires `verification_status ==
VERIFIED` specifically (excluding `NEEDS_REVIEW`, `UNVERIFIED`, and
`EXPIRED` alike), on top of the usual `publication_status == PUBLISHED`
and `deleted_at IS NULL` gates.

**`rule_version`** is a plain, manually-incremented integer, not a full
temporal rule-history system: every published `EligibilityRule` row is
treated as immutable once evaluated, so a `rule_id` + `rule_version` pair
in an evaluation's trace is enough to reproduce that exact evaluation
later (this phase's §B "stable rule versioning") without building the
rule-authoring/superseding workflow admin tooling would need — no such
admin UI exists yet, matching every other domain's fixture-only-authoring
convention at this stage.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.eligibility.enums import EligibilityAttribute, EligibilityOperator
from app.eligibility.enums import EligibilityRulePublicationStatus as RulePublicationStatus
from app.sources.enums import VerificationStatus

if TYPE_CHECKING:
    from app.jobs.models import Job
    from app.schemes.models import Scheme
    from app.services.models import Service


class EligibilityRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One versioned, sourced rule set for exactly one job/scheme/service —
    see module docstring for the entity-reference design."""

    __tablename__ = "eligibility_rules"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(job_id, scheme_id, service_id) = 1",
            name="ck_eligibility_rules_exactly_one_entity",
        ),
    )

    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    scheme_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True
    )

    rule_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Why this version exists / what changed — prose, not a diff engine.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    publication_status: Mapped[RulePublicationStatus] = mapped_column(
        Enum(RulePublicationStatus, name="eligibility_rule_publication_status", native_enum=True),
        nullable=False,
        default=RulePublicationStatus.DRAFT,
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

    # Soft delete, matching every other domain's convention.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped[Job | None] = relationship()
    scheme: Mapped[Scheme | None] = relationship()
    service: Mapped[Service | None] = relationship()
    conditions: Mapped[list[EligibilityCondition]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="EligibilityCondition.created_at",
    )


class EligibilityCondition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One machine-evaluable predicate — `attribute`/`operator`/typed
    value — belonging to exactly one `EligibilityRule`. See module
    docstring for why this is not `SchemeRequirement`/`ServiceRequirement`.

    Value storage is deliberately typed rather than one generic JSON blob:
    `numeric_value`/`numeric_value_max` (`Numeric`, never `Float` — this
    phase's §B) for numeric attributes, `text_value`/`text_values` for
    text/enum attributes. Which columns are populated is dictated by
    `attribute`+`operator`, validated by
    `app.eligibility.evaluator.validate_condition_shape` at read time —
    enforced in application code, not a database CHECK, since the valid
    combination space is attribute-and-operator-dependent in a way a
    single SQL CHECK expression could not express safely.
    """

    __tablename__ = "eligibility_conditions"
    __table_args__ = (
        CheckConstraint(
            "numeric_value IS NOT NULL OR text_value IS NOT NULL OR text_values IS NOT NULL",
            name="ck_eligibility_conditions_has_a_value",
        ),
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("eligibility_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attribute: Mapped[EligibilityAttribute] = mapped_column(
        Enum(EligibilityAttribute, name="eligibility_attribute", native_enum=True), nullable=False
    )
    operator: Mapped[EligibilityOperator] = mapped_column(
        Enum(EligibilityOperator, name="eligibility_operator", native_enum=True), nullable=False
    )
    # Plain-language explanation shown in the evaluation trace, e.g.
    # "Applicant must be between 18 and 35 years old." Never fabricated —
    # sourced from the same document the numeric/text value came from.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    numeric_value_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    text_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    text_values: Mapped[list[str] | None] = mapped_column(postgresql.JSONB, nullable=True)

    rule: Mapped[EligibilityRule] = relationship(back_populates="conditions")
