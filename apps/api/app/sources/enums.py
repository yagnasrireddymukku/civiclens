import enum


class VerificationStatus(enum.StrEnum):
    """See docs/DATA_GOVERNANCE.md §4 — the only four states a fact may be
    in; never presented to users as equivalent."""

    VERIFIED = "VERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    EXPIRED = "EXPIRED"
    UNVERIFIED = "UNVERIFIED"


class ChangeReviewStatus(enum.StrEnum):
    """Review state of a detected change, per the ingestion review
    workflow — see docs/DATA_SOURCES.md §3-4. Not enumerated by name in
    docs/DATABASE.md §2.7; these three values are the minimum needed to
    represent: detected, awaiting a human decision, decided."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
