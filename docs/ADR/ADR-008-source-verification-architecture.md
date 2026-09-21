# ADR-008: Source / Verification Architecture

## Status
Accepted

## Context
CivicLens's entire trust proposition depends on every fact being traceable
to an authoritative source with a known verification state
([DATA_GOVERNANCE.md](../DATA_GOVERNANCE.md)). This must be a first-class,
enforced part of the data model, not a convention that can be skipped.

## Decision
Model provenance explicitly as first-class entities —
`sources`, `source_versions`, `verification_records`, `change_records`
(see [DATABASE.md](../DATABASE.md) §2.7) — referenced by every fact-bearing
domain table. Ingestion writes only to staging/change tables; publishing to
live tables requires human review at v1 (see
[DATA_SOURCES.md](../DATA_SOURCES.md) §4). Every time-sensitive public page
surfaces "Last verified: DATE" and a source link, sourced directly from
this model, not derived ad hoc.

## Alternatives Considered
- **Provenance as unstructured metadata (e.g., a JSON "notes" field)**:
  rejected — unqueryable, unenforceable, easy to omit; provenance must be
  a structural requirement, not an optional annotation.
- **No explicit versioning of source content**: rejected — without
  `source_versions`, change detection ([DATA_SOURCES.md](../DATA_SOURCES.md)
  §5) has nothing to diff against, and audit trails would be incomplete.
- **Autonomous publish with post-hoc audit** (publish first, review later):
  rejected for v1 — the cost of a published wrong fact (a user missing a
  deadline, or acting on a fabricated scheme) is higher than the delay cost
  of human review at current data volumes.

## Consequences
- Every new domain feature that stores a public fact must be designed with
  a `source_id`/verification path from the start — this is a standing
  constraint on all future schema work (see [CLAUDE.md](../../CLAUDE.md)).
- The admin/review tooling (Phase 13) is not optional scope — it is a
  prerequisite for publishing any real data at all.
- Slightly slower time-to-publish for new data than an autonomous pipeline,
  accepted as the cost of the trust guarantee that differentiates the
  product.
