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
