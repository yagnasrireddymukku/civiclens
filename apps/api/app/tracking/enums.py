"""Tracking domain vocabulary — see docs/DATABASE.md §17.

`TrackedEntityType` intentionally does NOT import `app.ai.enums.
AIEntityType` even though the values overlap exactly (job/service/
scheme/document) — `app.tracking` has no reason to depend on `app.ai`
as a module, and each domain that has needed this same small
job/service/scheme/document vocabulary (`app.ai`, this module) has
defined its own copy rather than manufacturing a shared-vocabulary
module for a 4-line enum (CLAUDE.md rule 12: avoid premature
abstraction). Scholarships are tracked via their parent `scheme_id`
(this phase's §4.1), not a fifth value.
"""

import enum


class TrackedEntityType(enum.StrEnum):
    JOB = "job"
    SERVICE = "service"
    SCHEME = "scheme"
    DOCUMENT = "document"
