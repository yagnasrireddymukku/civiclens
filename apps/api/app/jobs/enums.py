"""Government Jobs domain enums — see docs/DATABASE.md §2.2-§2.3.

Three distinct "status"-shaped concepts exist across this module,
deliberately kept separate rather than collapsed into one:

- `Job.publication_status` (this file): the editorial visibility gate —
  DRAFT/ARCHIVED are never returned by the public API or indexed into
  search, regardless of anything else. This is the one place a job can
  be hidden outright.
- `Job.status` (a plain string, `app/jobs/models.py`): a browse-friendly,
  free-text current-state label (e.g. "open", "closed"), mirroring
  `search_documents.status`'s existing convention
  (docs/SEARCH.md §6: "free-text, entity-defined at this phase").
- `JobNotificationStatus` (this file): the detailed recruitment-cycle
  lifecycle for one specific notification, since a Job may recur across
  many notifications over time with different cycle stages.
"""

import enum


class OrganizationType(enum.StrEnum):
    CENTRAL = "CENTRAL"
    STATE = "STATE"
    AUTONOMOUS_BODY = "AUTONOMOUS_BODY"


class EmploymentType(enum.StrEnum):
    PERMANENT = "PERMANENT"
    CONTRACT = "CONTRACT"
    TEMPORARY = "TEMPORARY"


class JobPublicationStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class JobNotificationStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    PUBLISHED = "PUBLISHED"
    APPLICATION_OPEN = "APPLICATION_OPEN"
    APPLICATION_CLOSED = "APPLICATION_CLOSED"
    EXAMINATION = "EXAMINATION"
    RESULT = "RESULT"
    ARCHIVED = "ARCHIVED"
