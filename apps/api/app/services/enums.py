"""Government Services domain enums — see docs/DATABASE.md §11.

`ServicePublicationStatus` deliberately does not reuse
`app.jobs.enums.JobPublicationStatus` even though the three values are
identical — that type is named/scoped to jobs specifically (like
`job_notification_status`), not established as a generic shared type
from the start the way `verification_status` (owned by `app.sources`)
was. Renaming it to a generic shared enum, and migrating the existing
`jobs` table to it, is a bigger change than this phase's scope
justifies — see docs/DATABASE.md §11 for the fuller note.
"""

import enum


class ServiceCategory(enum.StrEnum):
    """A controlled, extensible taxonomy (this phase's §5) — deliberately
    not free text, unlike `Job.category`: services form a bounded,
    citizen-facing set of kinds worth filtering by, where jobs' category
    is an open-ended recruitment classification."""

    CERTIFICATES = "CERTIFICATES"
    DOCUMENTS = "DOCUMENTS"
    WELFARE = "WELFARE"
    EDUCATION = "EDUCATION"
    HEALTHCARE = "HEALTHCARE"
    AGRICULTURE = "AGRICULTURE"
    EMPLOYMENT = "EMPLOYMENT"
    BUSINESS = "BUSINESS"
    TRANSPORT = "TRANSPORT"
    MUNICIPAL = "MUNICIPAL"
    REVENUE = "REVENUE"
    SOCIAL_SECURITY = "SOCIAL_SECURITY"
    IDENTITY = "IDENTITY"
    UTILITIES = "UTILITIES"
    OTHER = "OTHER"


class DeliveryMode(enum.StrEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    BOTH = "BOTH"


class ServicePublicationStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class RequirementType(enum.StrEnum):
    """A lightweight classification for `ServiceRequirement` rows — not
    the eligibility-engine's `attribute`/`operator`/`value` model
    (docs/ELIGIBILITY_ENGINE.md), which Phase 10 owns. This just lets a
    future rule-authoring step ask "does this service have an age
    requirement" without parsing prose."""

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
