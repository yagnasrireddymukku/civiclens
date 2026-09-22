"""Government Services domain enums — see docs/DATABASE.md §10.

`ServicePublicationStatus` deliberately does not reuse
`app.jobs.enums.JobPublicationStatus` even though the three values are
identical — that type is named/scoped to jobs specifically (like
`job_notification_status`), not established as a generic shared type
from the start the way `verification_status` (owned by `app.sources`)
was. Renaming it to a generic shared enum, and migrating the existing
`jobs` table to it, is a bigger change than this phase's scope
justifies — see docs/DATABASE.md §10 for the fuller note.

`RequirementType`/`ApplicationChannelType` moved to
`app.requirements.enums` in Phase 8, once Schemes needed the same
vocabulary — see that module's docstring.
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
