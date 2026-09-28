"""Civic AI / RAG vocabulary — see docs/AI_ARCHITECTURE.md.

`AIEntityType` intentionally mirrors the plain string values
`app.search.models.SearchDocument.entity_type` already uses ("job",
"service", "scheme", "document") — not a new taxonomy. It's a Python
enum here (not a DB enum, matching `SearchDocument.entity_type`'s own
"plain string column" convention, since it's a polymorphic reference
key, not a column an "add one more valid domain" migration should ever
be needed for).
"""

import enum


class AIEntityType(enum.StrEnum):
    JOB = "job"
    SERVICE = "service"
    SCHEME = "scheme"
    DOCUMENT = "document"


class RetrievalMatchType(enum.StrEnum):
    LEXICAL = "LEXICAL"
    SEMANTIC = "SEMANTIC"


class GroundingStatus(enum.StrEnum):
    """docs/AI_ARCHITECTURE.md §6's `grounding_status` — the UI renders
    each of these differently (never just "confidence: 0.42"):

    - GROUNDED: at least one server-validated citation backs the answer.
    - UNGROUNDED: the model produced an answer but zero of its citations
      survived server-side validation against the retrieved evidence —
      the answer text is discarded, never shown, per
      docs/AI_ARCHITECTURE.md §6.
    - INSUFFICIENT_EVIDENCE: retrieval itself returned nothing — the LLM
      is never even called (this phase's cost-control requirement).
    - PROVIDER_UNAVAILABLE: no LLM provider is configured, or the
      provider call failed/timed out — distinct from "no evidence,"
      since evidence may well exist and search/browse remains available.
    """

    GROUNDED = "GROUNDED"
    UNGROUNDED = "UNGROUNDED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"


class EligibilityExplanationStatus(enum.StrEnum):
    """Mirrors `GroundingStatus` for the narrower explain-eligibility
    path (app/ai/eligibility_explainer.py) — kept as its own enum since
    "not supported" (no evaluable rule) is a distinct, expected case
    there that has no equivalent in general Q&A."""

    EXPLAINED = "EXPLAINED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
