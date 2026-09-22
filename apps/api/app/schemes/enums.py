"""Government Schemes domain enums — see docs/DATABASE.md §12.

`SchemePublicationStatus` deliberately does not reuse
`ServicePublicationStatus`/`JobPublicationStatus` even though all three
share the same three values — same reasoning as
`app.services.enums`'s docstring: a workflow gate is legitimately
domain-scoped, and collapsing it into one shared enum now would migrate
two already-shipped tables for a theoretical future benefit
(CLAUDE.md rules 9, 12, 22).

`RequirementType`/`ApplicationChannelType` are NOT redefined here —
Schemes import the shared vocabulary directly from
`app.requirements.enums`, the same way Services does after Phase 8's
extraction.

`EducationLevel`/`StudyMode` (Phase 9, docs/DATABASE.md §13) belong here
rather than a new module: they have exactly one consumer
(`ScholarshipDetail`, itself a `Scheme` extension), unlike
`RequirementType`/`ApplicationChannelType`, which were extracted to
`app.requirements` only once a *second* consumer (Schemes) appeared.
Following that same "extract only when a second consumer appears"
precedent in reverse — there is no second consumer here, so there is
nothing to extract.
"""

import enum


class SchemeCategory(enum.StrEnum):
    """A controlled taxonomy (this phase's §5) — a bounded, citizen-facing
    set of benefit/support kinds, deliberately distinct from
    `app.services.enums.ServiceCategory`: a scheme is a benefit program a
    citizen may be eligible for, not a service a citizen requests/
    accesses (this phase's §3)."""

    SCHOLARSHIP = "SCHOLARSHIP"
    PENSION = "PENSION"
    SUBSIDY = "SUBSIDY"
    FINANCIAL_ASSISTANCE = "FINANCIAL_ASSISTANCE"
    INSURANCE = "INSURANCE"
    HOUSING = "HOUSING"
    HEALTHCARE = "HEALTHCARE"
    EDUCATION = "EDUCATION"
    AGRICULTURE = "AGRICULTURE"
    EMPLOYMENT = "EMPLOYMENT"
    SKILL_DEVELOPMENT = "SKILL_DEVELOPMENT"
    WOMEN_CHILD_WELFARE = "WOMEN_CHILD_WELFARE"
    SOCIAL_WELFARE = "SOCIAL_WELFARE"
    BUSINESS_ENTREPRENEURSHIP = "BUSINESS_ENTREPRENEURSHIP"
    DISABILITY_SUPPORT = "DISABILITY_SUPPORT"
    OTHER = "OTHER"


class BenefitType(enum.StrEnum):
    """A lightweight classification for `SchemeBenefit` rows — what form
    the support takes, never a fabricated amount (this phase's §6).
    Deliberately as coarse-grained as `RequirementType`/
    `ApplicationChannelType`: enough for a citizen to scan, not a
    financial-instrument taxonomy."""

    CASH_TRANSFER = "CASH_TRANSFER"
    SUBSIDY = "SUBSIDY"
    SCHOLARSHIP_AMOUNT = "SCHOLARSHIP_AMOUNT"
    PENSION = "PENSION"
    INSURANCE_COVERAGE = "INSURANCE_COVERAGE"
    LOAN_SUBSIDY = "LOAN_SUBSIDY"
    IN_KIND_SUPPORT = "IN_KIND_SUPPORT"
    OTHER = "OTHER"


class SchemePublicationStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class EducationLevel(enum.StrEnum):
    """A controlled, extensible taxonomy (Phase 9's §5) for
    `ScholarshipDetail.education_level` — bounded enough to be a useful
    filter, per this phase's explicit "keep taxonomy extensible, do not
    over-normalize" instruction."""

    SCHOOL = "SCHOOL"
    INTERMEDIATE = "INTERMEDIATE"
    DIPLOMA = "DIPLOMA"
    UNDERGRADUATE = "UNDERGRADUATE"
    POSTGRADUATE = "POSTGRADUATE"
    DOCTORAL = "DOCTORAL"
    PROFESSIONAL = "PROFESSIONAL"
    VOCATIONAL = "VOCATIONAL"
    OTHER = "OTHER"


class StudyMode(enum.StrEnum):
    """A small, closed set (Phase 9's §4/§10) — deliberately an enum, not
    prose, matching `DeliveryMode`'s precedent for a genuinely bounded
    dimension (unlike `course_discipline`/`institution_type`, which stay
    prose to avoid building an academic-institution reference database
    this phase's §10 explicitly warns against)."""

    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    DISTANCE = "DISTANCE"
    ONLINE = "ONLINE"
    OTHER = "OTHER"
