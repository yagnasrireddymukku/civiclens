"""Eligibility Engine vocabulary — see docs/ELIGIBILITY_ENGINE.md and
docs/DATABASE.md §15.

`EligibilityRulePublicationStatus` deliberately does NOT reuse
`SchemePublicationStatus`/`ServicePublicationStatus`/`JobPublicationStatus`
even though all four share the same three values — same reasoning as
`app.services.enums`'s docstring: a workflow gate is legitimately
domain-scoped (CLAUDE.md rules 9, 12, 22).

`EligibilityAttribute` is deliberately a small, closed set — only the
dimensions this phase's kickoff names as "well-defined criteria that can
be evaluated reliably" (age ranges, income ceilings, education level,
percentage/CGPA thresholds, residence/state, category) and that map to
something a citizen can be asked directly. Notably absent: date windows
(an application-window open/close date is a fact about the *opportunity*,
already shown on its own detail page, not something an *applicant*
answers — see docs/ELIGIBILITY_ENGINE.md's implementation note) and any
attribute `app.users.models.Profile` cannot represent honestly.
"""

import enum


class EligibilityAttribute(enum.StrEnum):
    AGE = "AGE"
    INCOME_ANNUAL = "INCOME_ANNUAL"
    EDUCATION_LEVEL = "EDUCATION_LEVEL"
    ACADEMIC_PERCENTAGE = "ACADEMIC_PERCENTAGE"
    ACADEMIC_CGPA = "ACADEMIC_CGPA"
    RESIDENCE_STATE = "RESIDENCE_STATE"
    CATEGORY = "CATEGORY"


class EligibilityOperator(enum.StrEnum):
    """The fixed, tested operator set from docs/ELIGIBILITY_ENGINE.md §3 —
    no free-form expression evaluation, no `eval`, ever."""

    EQ = "EQ"
    NEQ = "NEQ"
    GTE = "GTE"
    LTE = "LTE"
    BETWEEN = "BETWEEN"
    IN = "IN"
    NOT_IN = "NOT_IN"


class EligibilityOutcome(enum.StrEnum):
    """The only three verdicts the engine ever returns — never a
    probability/confidence score (docs/ELIGIBILITY_ENGINE.md §7)."""

    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    INCOMPLETE = "INCOMPLETE"


class ConditionStatus(enum.StrEnum):
    """Per-condition status feeding the overall `EligibilityOutcome` —
    `UNKNOWN` is never coerced to `PASS` or `FAIL` (docs/ELIGIBILITY_ENGINE.md
    §3: a missing attribute is never treated as false/zero/a pass)."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class EligibilityRulePublicationStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class EligibilityEntityType(enum.StrEnum):
    """The three entity kinds this phase's kickoff names — Documents are
    deliberately excluded: a `CivicDocument` is not itself something a
    citizen is "eligible" or "not eligible" for."""

    JOB = "JOB"
    SCHEME = "SCHEME"
    SERVICE = "SERVICE"
