# CivicLens — API Architecture

This document defines the REST API **conventions** every FastAPI endpoint
must follow — not endpoint-by-endpoint specifications. Concrete request/
response shapes are finalized per domain as each phase implements it (see
[ROADMAP.md](ROADMAP.md) Phases 2, 6–9), against the entities in
[DATABASE.md](DATABASE.md). This document is the target for Phase 2
("API.md conventions section finalized against the real app structure")
and is refined incrementally as domains land. **No endpoints are
implemented yet.**

## 1. Scope & Relationship to Other Docs

- Structural boundaries (which module owns which routes) come from
  [ARCHITECTURE.md](ARCHITECTURE.md) §1, §6.
- Entities referenced by every domain endpoint are defined in
  [DATABASE.md](DATABASE.md).
- The Eligibility Engine's response contract (§9 below) is defined in full
  in [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) §4 — this document only
  restates it as an example of contract style.
- Auth mechanics follow [ADR-009](ADR/ADR-009-authentication-strategy.md).
- Security requirements (input validation, rate limiting, authz) are
  enforced per [SECURITY.md](SECURITY.md); this document defines the
  conventions those checks apply to.

## 2. Versioning

- All routes are prefixed `/api/v1/...`. The version prefix is the unit of
  breaking-change isolation — a breaking change to a resource's shape ships
  as `/api/v2/...` for that resource, not an in-place mutation of `v1`.
- A minor, additive change (a new optional field, a new endpoint) does not
  require a version bump.
- Deprecation policy: a deprecated endpoint is marked in the OpenAPI schema
  (`deprecated: true`) and documented with a removal-not-before date of at
  least one full release cycle. Deprecated endpoints continue to function
  until removed — no silent behavior changes during the deprecation window.
- No endpoint ships without an OpenAPI-visible version; there is no
  unversioned `/api/...` surface.

## 3. Route Domains

Each domain below is an isolated FastAPI router mounted under
`/api/v1/{domain}`, owned by the matching backend module
([ARCHITECTURE.md](ARCHITECTURE.md) §6):

| Route prefix | Backing entities ([DATABASE.md](DATABASE.md)) |
|---|---|
| `/search` | read-side projection of all domain tables ([SEARCH.md](SEARCH.md)) |
| `/jobs` | `jobs`, `job_notifications`, `deadlines` |
| `/exams` | `exams`, `deadlines` |
| `/schemes` | `schemes` |
| `/services` | `services`, `documents`, `entity_documents` |
| `/scholarships` | `scholarships` |
| `/representatives` | `representatives` |
| `/elections` | `elections`, `election_results` |
| `/eligibility` | `eligibility_rules`, `eligibility_conditions` |
| `/calculators` | none (pure functions — see §9) |
| `/ai` | none owned; retrieves via search + domain tables + `sources` ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)) |
| `/tracking` | `tracking_items` |
| `/notifications` | `notifications` |
| `/sources` | `sources`, `source_versions`, `verification_records` |
| `/users`, `/auth` | `users`, `profiles` |

A router never queries another domain's tables directly; cross-domain reads
go through that domain's own module interface, per the modular-monolith
boundary rule ([ARCHITECTURE.md](ARCHITECTURE.md) §1, [CLAUDE.md](../CLAUDE.md) rule 10).

## 4. Authentication & Authorization

- Bearer JWT access tokens on the `Authorization` header for authenticated
  routes; refresh via a dedicated `/api/v1/auth/refresh` endpoint. See
  [ADR-009](ADR/ADR-009-authentication-strategy.md) for token lifetime and
  storage guidance.
- Every route is explicitly one of: **public** (no token required —
  default for all read-only domain/content endpoints, required for SEO
  crawlability per [SEO.md](SEO.md)), **authenticated** (`user` role or
  above — tracking, saved items, profile, dashboard), or **privileged**
  (`editor`/`admin` — ingestion review, source management, per
  [DATA_SOURCES.md](DATA_SOURCES.md) §4).
- Role checks are declared as a FastAPI dependency at the route level
  (e.g., `require_role("editor")`), never as an inline `if` inside handler
  logic — this keeps authorization auditable and consistent across
  routers.
- No endpoint infers a user's identity or role from anything other than
  the validated token claims.

## 5. Request Validation

- Every request body, query parameter set, and path parameter is a
  Pydantic v2 model — no untyped `dict` or raw `Request` body parsing in
  handler code ([ADR-003](ADR/ADR-003-fastapi-backend.md)).
- Validation errors return HTTP 422 with the standard error shape (§8),
  including a `field` path per violation — FastAPI's default Pydantic
  error detail is normalized into this shape at the app's exception-handler
  layer, not left as the raw default format.
- Enum-like fields (status, verification status, domain names) are typed
  as Python enums mirrored from the DB's own constrained values
  ([DATABASE.md](DATABASE.md)), never free-form strings validated by
  convention only.

## 6. Pagination, Filtering, Sorting

Applied uniformly across every list endpoint (`/jobs`, `/schemes`,
`/search`, etc.):

- **Pagination**: cursor-based for feeds that can grow and are consumed
  sequentially (`/notifications`, `/search`); offset/limit
  (`?page=&page_size=`, default `page_size=20`, max `100`) for bounded,
  filterable domain listings. Every paginated response includes
  `total_count` (or `has_more` for cursor pagination) — a client must never
  have to guess whether more results exist.
- **Filtering**: query parameters map directly to indexed columns —
  `state`, `district`, `status`, `date_from`/`date_to`, `domain` — per
  FR-SR2 ([PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md)). Filters are
  additive (AND), never an ad hoc query-language string.
- **Sorting**: `?sort=field&order=asc|desc`, restricted to an explicit
  allow-list of sortable columns per resource (never an arbitrary
  client-supplied column name, to avoid unindexed-sort performance
  surprises and injection surface).

## 7. Standard Error Response Shape

Every non-2xx response — validation failure, not-found, auth failure,
rate-limit, server error — uses one consistent envelope:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Job notification not found.",
    "details": [
      {"field": "job_id", "issue": "no record with this id"}
    ]
  }
}
```

- `code` is a stable, machine-readable string (`VALIDATION_ERROR`,
  `NOT_FOUND`, `UNAUTHORIZED`, `FORBIDDEN`, `RATE_LIMITED`,
  `INTERNAL_ERROR`), independent of the human-readable `message`, so
  frontend code branches on `code`, never on message text.
- `details` is optional and only present for multi-field validation
  failures.
- Internal errors never leak stack traces, SQL, or file paths in
  `message` — that detail goes to server-side logs only
  ([SECURITY.md](SECURITY.md)).

## 8. Rate Limiting

- Applied per-user (authenticated) or per-IP (anonymous), enforced at the
  API layer (not left to infrastructure alone), with limits set per route
  class: generous for public read endpoints, stricter for `/auth` (brute-
  force protection) and `/ai` (cost control, per
  [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §7).
- A rate-limited request returns HTTP 429 using the standard error shape
  (`code: "RATE_LIMITED"`) with a `Retry-After` header.
- Exact thresholds are a [SECURITY.md](SECURITY.md) concern, tuned per
  route at implementation time — this document only fixes the mechanism
  and response contract, not the numbers.

## 9. Response Contract Style — Worked Example

Domain endpoints return the resource as structured data with explicit
provenance fields, never bare content. The Eligibility Engine's evaluation
endpoint is the reference example for how a non-trivial response is
shaped (full semantics in [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) §4):

```json
{
  "result": "INCOMPLETE",
  "conditions": [
    {"attribute": "age", "operator": "between", "value": [21, 42], "userValue": 23, "status": "PASS"}
  ],
  "source": {"title": "...", "url": "...", "lastVerified": "2026-08-01"}
}
```

Every domain resource follows the same discipline: the fact, plus its
`source` (URL, title, last-verified date, verification status) inline or
by reference — never a fact without a way to trace it back to
[DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §3's required provenance fields.
`/calculators` endpoints are the one exception with no `source` field,
since they are pure functions over user-supplied input (e.g., age-as-on-
date) rather than published facts.

## 10. OpenAPI Schema & Typed Client Generation

- FastAPI generates the OpenAPI 3 schema natively from route signatures and
  Pydantic models — the schema is never hand-maintained
  ([ADR-003](ADR/ADR-003-fastapi-backend.md)).
- The schema is the single source of truth for `packages/types`: a
  build step generates a typed TypeScript client (types + fetch wrappers)
  consumed by `apps/web`, so the frontend never hand-writes request/response
  types that could drift from the backend ([ARCHITECTURE.md](ARCHITECTURE.md)
  §6, [ADR-002](ADR/ADR-002-nextjs-frontend.md)).
- Any backend route change that alters a response shape therefore surfaces
  as a type error in the frontend build the next time
  `packages/types` is regenerated — this is the intended contract-
  drift guard, not a manual review step.
- Route handlers document responses with explicit `response_model`s (not
  `response_model=None` with manual serialization) so the generated schema
  is accurate, including error responses via FastAPI's documented
  exception-to-schema mapping.

## 11. Database Dependency Injection & Health/Readiness (Phase 3)

Every route that needs the database declares it via a FastAPI dependency
— `Depends(get_db)` (`app/core/db/session.py`) — never by importing an
engine/session directly or opening its own connection:

```
request → get_db dependency (opens a Session) → route/service function
        → repository/query code → SQLAlchemy → PostgreSQL
```

- The request is the transaction boundary: `get_db` commits after the
  route returns normally and rolls back if it raises — route/service code
  never calls `session.commit()`/`session.rollback()` itself
  ([DATABASE.md](DATABASE.md), transaction-management convention).
- `GET /api/v1/health` (liveness) has no database dependency by design —
  it answers "is the process up." `GET /api/v1/health/ready` (readiness,
  Phase 3) checks the database using its own short-lived connection
  (`get_engine()` directly, not `get_db`) rather than a request-scoped
  session, since it's testing raw connectivity, not doing request work; it
  returns the standard error envelope (§7) with `code: "NOT_READY"` and
  HTTP 503 when the database is unreachable, never a hang — the engine
  enforces a connect/statement timeout specifically so this fails fast.

## 12. Explicitly Not Built Yet

- Any domain-content business route (jobs, exams, schemes, services,
  scholarships, representatives, elections, eligibility, tracking, AI) or
  its request/response models — only `health`/`health/ready` (§11) and
  `/search` (Phase 5, [SEARCH.md](SEARCH.md) §12) exist so far, and
  `/search` has nothing real to index yet (no domain route has published
  anything into it).
- Concrete rate-limit thresholds, cache headers, or CDN interaction rules
  (deferred to [SECURITY.md](SECURITY.md) / [ARCHITECTURE.md](ARCHITECTURE.md)
  performance work in later phases).
- GraphQL or any query language beyond the filter/sort conventions in §6 —
  not needed at MVP scope and not planned without a documented reason.

This document defines the target API conventions for Phase 2 onward; each
domain phase (6–9, 10–12) implements against it and updates this document
only where real implementation reveals a convention gap.
