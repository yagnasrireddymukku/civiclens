"""Shared eligibility-support vocabulary — see docs/DATABASE.md §11.

`RequirementType`/`ApplicationChannelType` moved here in Phase 8, once
Schemes needed the same vocabulary Services (Phase 7) already used.
Unlike `ServicePublicationStatus`/`JobPublicationStatus` (deliberately
NOT shared — see `app.services.enums`'s docstring — since a workflow
gate is legitimately domain-scoped and could diverge per domain later),
a *document/application-channel/requirement-type* concept isn't
domain-specific in any real way: "Aadhaar Card" or "apply online" mean
the same thing whether the citizen-facing record is a job, a service, or
a scheme. This is a pure Python/enum-level move — each domain still owns
its own child tables (`service_requirements` vs `scheme_requirements`,
etc.); only the *vocabulary* is shared, matching the same
"extract when a second consumer appears" precedent
`app.institutions` followed in Phase 7 (verified via `alembic check`
showing zero schema diff after the move).

`DeliveryMode` moved here in Phase 10, for the identical reason: the
Documents & Certificates domain (`app.documents`) needs the same
online/offline/both vocabulary `app.services.enums` already defined —
"available online," "available offline," or "both" means the same
thing whether the citizen-facing record is a service or a civic
document. Also a pure Python/enum-level move (verified via
`alembic check` showing zero schema diff after the move); `services`
still owns `delivery_mode` as its own column, reusing this enum by
`create_type=False`.
"""

import enum


class RequirementType(enum.StrEnum):
    """A lightweight classification for a domain's own `*_requirements`
    child rows — not the eligibility-engine's `attribute`/`operator`/
    `value` model (docs/ELIGIBILITY_ENGINE.md), which Phase 10 owns. This
    just lets a future rule-authoring step ask "does this entity have an
    age requirement" without parsing prose. Deliberately kept to five
    values rather than enumerating every beneficiary dimension Phase 8's
    kickoff names (student/employment status, social category, gender,
    disability, landholding) — those are represented as `OTHER` +
    descriptive prose instead of dedicated enum values, avoiding an
    enum-expansion migration for dimensions nothing in this phase filters
    or queries by (see docs/DATABASE.md §11)."""

    AGE = "AGE"
    RESIDENCY = "RESIDENCY"
    INCOME = "INCOME"
    OCCUPATION = "OCCUPATION"
    OTHER = "OTHER"


class ApplicationChannelType(enum.StrEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MOBILE_APP = "MOBILE_APP"
    MEESEVA = "MEESEVA"
    DEPARTMENT_PORTAL = "DEPARTMENT_PORTAL"
    SERVICE_CENTER = "SERVICE_CENTER"
    IN_PERSON = "IN_PERSON"
    OTHER = "OTHER"


class DeliveryMode(enum.StrEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    BOTH = "BOTH"
