"""Admin Intelligence Center vocabulary.

`AdminEntityType` intentionally does NOT import `app.tracking.enums.
TrackedEntityType` or `app.ai.enums.AIEntityType`, even though the
values are identical — matching the precedent both of those modules
already set for exactly this reason (see `app.tracking.enums`'s own
docstring): `app.admin` has no module-boundary reason to depend on
`app.tracking` as a module, and each orchestration module that has
needed this same small job/service/scheme/document vocabulary has
defined its own copy rather than manufacturing a shared-vocabulary
module for a 4-line enum (CLAUDE.md rule 12).
"""

import enum


class AdminEntityType(enum.StrEnum):
    JOB = "job"
    SERVICE = "service"
    SCHEME = "scheme"
    DOCUMENT = "document"
