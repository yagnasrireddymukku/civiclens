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
| `/ai` | `ai_knowledge_chunks` (Phase 12); retrieves via `search_documents` + domain tables + `sources` ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)) |
| `/tracking` | `tracked_items` (§19) |
| `/notifications` | `notifications`, `notification_delivery_attempts` (§19) |
| `/sources` | `sources`, `source_versions`, `verification_records` |
| `/auth` | `users`, `refresh_tokens` (§19) |
| `/admin` | `change_records`, `verification_records`, `sources`/`source_versions` (read-only), plus each domain's own `verification_status` column (§21) — review/approval half of Phase 13 only, RBAC-gated |

A router never queries another domain's tables directly; cross-domain reads
go through that domain's own module interface, per the modular-monolith
boundary rule ([ARCHITECTURE.md](ARCHITECTURE.md) §1, [CLAUDE.md](../CLAUDE.md) rule 10).

## 4. Authentication & Authorization

**Realized (Tracking + Notifications, rescheduled from Phase 12) —
httpOnly cookies, not a Bearer `Authorization` header.** ADR-009's
"cookie vs. header" choice is now implemented, not aspirational:
- JWT access token (~15 min TTL) and refresh token (~30 day TTL,
  rotated on every use) are set as httpOnly, `Secure` (in
  staging/production), `SameSite=Lax` cookies by `POST /api/v1/auth/
  {register,login,refresh}` — never returned in a response body, never
  read from an `Authorization` header. See
  [ADR-009](ADR/ADR-009-authentication-strategy.md) and
  [SECURITY.md](SECURITY.md) §2-3 for the full rationale (CSRF exposure
  vs. XSS-exfiltration trade-off that motivated this over a header
  token).
- A third, deliberately non-httpOnly cookie (`civiclens_csrf`) pairs
  with the double-submit pattern: every mutating request must also
  send that same value in an `X-CSRF-Token` header, compared with
  `hmac.compare_digest`. Enforced by the `verify_csrf` dependency on
  every non-GET authenticated route.
- Refresh-token rotation is family-scoped: replaying an
  already-rotated (revoked) refresh token revokes every token sharing
  its `family_id`, not just the one presented — [SECURITY.md](SECURITY.md)
  §2's anti-theft design, verified by a dedicated replay test.
- Every route is explicitly one of: **public** (no token required —
  default for all read-only domain/content endpoints, required for SEO
  crawlability per [SEO.md](SEO.md)), **authenticated** (`user` role or
  above — tracking, notifications, profile, dashboard; enforced by the
  `get_current_user` dependency, which 401s on any missing/invalid/
  expired access-token cookie), or **privileged** (`editor`/`admin` —
  change-record review, entity verification, per
  [DATA_SOURCES.md](DATA_SOURCES.md) §4 and §21 below — **realized,
  Phase 13's review/approval half**; ingestion-pipeline-specific
  privileged actions, since no ingestion pipeline exists, remain
  unbuilt).
- **Realized:** role checks are declared as a FastAPI dependency at the
  route level — `require_role(*allowed_roles)`
  (`app.auth.dependencies`) returns a dependency 403ing unless
  `current_user.role` is one of the given roles, composed with
  `get_current_user` rather than duplicating its cookie/token logic.
  Every `/admin/*` route (§21) uses it; never an inline `if` inside
  handler logic — this keeps authorization auditable and consistent
  across routers.
- No endpoint infers a user's identity or role from anything other than
  the validated access-token cookie's claims — never from a
  client-supplied header, query parameter, or request body field.
- Ownership on every authenticated tracking/notification route is
  IDOR-safe by construction: "doesn't exist" and "belongs to another
  user" are raised as the identical internal error and mapped to the
  identical 404, so a response never discloses which case applies.

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

- Any domain-content business route beyond Jobs, Services, Schemes,
  Documents, Eligibility, Civic AI, Auth, Tracking, Notifications, and
  Admin (exams, representatives, elections) or its request/response
  models — `health`/`health/ready` (§11), `/search` (Phase 5,
  [SEARCH.md](SEARCH.md) §12), `/jobs` (Phase 6, §13), `/services`
  (Phase 7, §14), `/schemes` (Phase 8, §15), `/documents` (Phase 10,
  §17), `/eligibility` (Phase 11, §18), `/auth`/`/tracking`/
  `/notifications` (Tracking + Notifications, rescheduled from Phase
  12, §19), `/ai` (Phase 12, §20), and `/admin` (Phase 13, review/
  approval half only, §21) exist so far. Scholarships (Phase 9, §16)
  are not a separate route — `category=SCHOLARSHIP` schemes returned
  by the same `/schemes` endpoints.
- Concrete rate-limit thresholds/infrastructure for anything beyond
  `/ai/*`'s own in-process MVP limiter (§20) and `/admin/*`'s own
  separate per-user in-process MVP limiter (§21) — no cross-route,
  cross-process, or general rate-limiting infrastructure exists; cache
  headers or CDN interaction rules (deferred to
  [SECURITY.md](SECURITY.md) / [ARCHITECTURE.md](ARCHITECTURE.md)
  performance work in later phases).
- **Realized (Phase 13, review/approval half):** `require_role`
  (`app.auth.dependencies`) and the `/admin/*` routes it gates (§21) —
  an approve/reject route for a `ChangeRecord` and the verification-
  submission route [DATABASE.md](DATABASE.md) §19 describes. **Still
  not built:** a re-indexing/admin route for `/ai` (no route anywhere
  calls `require_role` for it yet, even though the dependency now
  exists), and the full ingestion-pipeline/review-queue architecture
  [DATA_SOURCES.md](DATA_SOURCES.md) §3-4 describes (fetch/extract/
  normalize/validate stages, source onboarding) — this phase's `/admin`
  routes review already-detected changes and submit verification
  decisions; they do not fetch, onboard, or publish anything.
- GraphQL or any query language beyond the filter/sort conventions in §6 —
  not needed at MVP scope and not planned without a documented reason.

## 13. Jobs Domain (Phase 6)

The first real domain module, following every convention above:

- `GET /api/v1/jobs` — filters: `state_id`, `district_id`,
  `organization_id`, `department_id`, `status` (free text, exact match),
  `employment_type` (enum), `date_from`/`date_to` (against
  `last_verified_at`); `page`/`page_size` (§6); `sort` (a `Literal` with
  one value, `"recent"`, today — an explicit allow-list, never a
  popularity/salary-based sort, per this phase's scope). Deliberately has
  **no free-text `q` parameter** — that already exists at `/search` with
  `entity_type=job`, and duplicating relevance ranking inside a second
  endpoint was judged unnecessary complexity, not an oversight.
- `GET /api/v1/jobs/{slug}` — `slug`, not a database id, is the public
  identifier (§12's "don't expose internal database IDs" convention).
  Returns the job with its notifications nested inline (each with its
  vacancies nested inline) rather than a separate
  `/jobs/{id}/notifications` endpoint — the kickoff named that endpoint
  as a *potential* shape, and one response with everything a detail page
  needs was simpler than two round trips for data that's always rendered
  together.
- Both endpoints apply the same visibility rule: a job is returned only
  when `publication_status="PUBLISHED"` and `verification_status` is
  `VERIFIED`/`NEEDS_REVIEW` — an unpublished or not-yet-verified job 404s
  identically to a nonexistent slug, never distinguishing the two to an
  unauthenticated caller.
- See [DATABASE.md](DATABASE.md) §9 for the schema and
  [SEARCH.md](SEARCH.md) for how a published job also becomes a search
  result (`entity_type="job"`).

## 14. Services Domain (Phase 7)

The second real domain module, mirroring §13's Jobs conventions exactly:

- `GET /api/v1/services` — filters: `state_id`, `district_id`,
  `organization_id`, `department_id`, `category` (enum, unlike Jobs'
  free-text `category` — Services uses a controlled taxonomy),
  `delivery_mode` (enum), `status` (free text, exact match),
  `date_from`/`date_to` (against `last_verified_at`); `page`/`page_size`
  (§6); `sort` (a `Literal` with one value, `"recent"`, matching §13's
  identical no-popularity-ranking rationale). Deliberately has **no
  free-text `q` parameter**, for the same reason as `/jobs` — full-text
  search already exists at `/search` with `entity_type=service`.
- `GET /api/v1/services/{slug}` — `slug` is the public identifier.
  Returns `requirements`/`required_documents`/`application_methods`
  nested inline (each a small, provenance-free child list — see
  [DATABASE.md](DATABASE.md) §10) rather than separate sub-resource
  endpoints, for the same "one response, no extra round trips" reasoning
  as `/jobs/{slug}`'s nested notifications.
- Same visibility rule as Jobs (§13): `publication_status="PUBLISHED"`
  and `verification_status` `VERIFIED`/`NEEDS_REVIEW`, or an identical
  404 — never distinguishing "doesn't exist" from "not yet published."
- See [DATABASE.md](DATABASE.md) §10 for the schema and
  [SEARCH.md](SEARCH.md) for how a published service also becomes a
  search result (`entity_type="service"`), the second real domain to do
  so (proving the Phase 5 search abstraction generalizes across domains,
  not just for Jobs).

## 15. Schemes Domain (Phase 8)

The third real domain module, mirroring §13/§14's conventions exactly:

- `GET /api/v1/schemes` — filters: `state_id`, `district_id`,
  `organization_id`, `department_id`, `category` (enum — `SchemeCategory`,
  a 16-value taxonomy distinct from `ServiceCategory`), `status` (free
  text, exact match), `date_from`/`date_to` (against `last_verified_at`);
  `page`/`page_size` (§6); `sort` (a `Literal` with one value, `"recent"`,
  matching §13/§14's identical no-popularity-ranking rationale). No
  `delivery_mode` filter — a scheme has no equivalent field. Deliberately
  has **no free-text `q` parameter**, for the same reason as `/jobs`/
  `/services` — full-text search already exists at `/search` with
  `entity_type=scheme`.
- `GET /api/v1/schemes/{slug}` — `slug` is the public identifier.
  Returns `benefits`/`requirements`/`required_documents`/
  `application_methods`/`related_services` nested inline (each a small
  child list — see [DATABASE.md](DATABASE.md) §12) rather than separate
  sub-resource endpoints, for the same "one response, no extra round
  trips" reasoning as `/jobs/{slug}`'s nested notifications.
  `related_services` additionally filters out any linked `Service` that
  isn't itself publicly visible — a scheme's trust boundary doesn't
  extend to the services it links to.
- Same visibility rule as Jobs/Services (§13/§14):
  `publication_status="PUBLISHED"` and `verification_status`
  `VERIFIED`/`NEEDS_REVIEW`, or an identical 404 — never distinguishing
  "doesn't exist" from "not yet published."
- See [DATABASE.md](DATABASE.md) §12 for the schema and
  [SEARCH.md](SEARCH.md) §16 for how a published scheme also becomes a
  search result (`entity_type="scheme"`), the third real domain to do
  so — with an explicit test that Jobs, Services, and Schemes all appear
  together in one cross-domain search result set.

## 16. Scholarships (Phase 9)

Not a separate route — Scholarships are a `Scheme` specialization
(`category == "SCHOLARSHIP"`), per the architectural decision in
[DATABASE.md](DATABASE.md) §13 and [ROADMAP.md](ROADMAP.md)'s Phase 9
entry. `GET /api/v1/schemes` and `GET /api/v1/schemes/{slug}` (§15) serve
scholarships exactly as they serve any other scheme, with two additions:

- `GET /api/v1/schemes` gained one filter, `education_level` (enum —
  `EducationLevel`, 9 values). It matches only schemes that have a
  `ScholarshipDetail` row at all — combining it with a non-scholarship
  `category` deterministically yields zero results, the same way any
  other AND-combined filter pair would, rather than one filter silently
  overriding the other. No `course_discipline`/`institution_type`
  filter exists — those fields are prose (§10 of the kickoff explicitly
  warns against building an academic-institution reference database),
  not a bounded value a query parameter could match exactly.
- `GET /api/v1/schemes/{slug}` gained one nested field, `scholarship` —
  `null` for every non-scholarship scheme (not an object of all-`null`
  fields), populated with `education_level`/`course_discipline`/
  `institution_type`/`study_mode`/`year_of_study`/`minimum_percentage`/
  `minimum_cgpa`/`academic_requirement_notes`/`application_opens`/
  `application_closes`/`correction_window_end`/`academic_year`/
  `renewable`/`renewal_notes` when the scheme has one.
  `minimum_percentage`/`minimum_cgpa` serialize as JSON **strings**
  ("60.00"), not numbers — Pydantic v2's default serialization for a
  `Decimal` response-model field, verified directly against a real
  response rather than assumed (a wrong `number` assumption was caught
  by the live smoke test before commit, documented in
  [DATABASE.md](DATABASE.md) §13).
- Same visibility rule as every other domain (§13/§14/§15): a
  scholarship scheme is only ever returned when its parent `Scheme` row
  is `publication_status="PUBLISHED"` and `verification_status`
  `VERIFIED`/`NEEDS_REVIEW` — there is no separate scholarship
  visibility rule to keep in sync, since it is the same row.
- No eligibility endpoint, no `ELIGIBLE`/`NOT_ELIGIBLE`/`INCOMPLETE`
  field anywhere in either response — the Eligibility Engine's own
  domain, entirely (`/eligibility`, §18, Phase 11).

## 17. Documents & Certificates Domain (Phase 10)

The fourth real domain module, and a genuinely first-class one this
time (unlike Scholarships, §16) — see [DATABASE.md](DATABASE.md) §14
for the full architectural decision distinguishing a `CivicDocument`
(the official document/certificate itself) from a `RequiredDocument`/
`SchemeRequiredDocument` row (a requirement that a document be
provided):

- `GET /api/v1/documents` — filters: `state_id`, `district_id`,
  `organization_id`, `department_id`, `document_type` (enum —
  `DocumentType`, 7 values), `category` (enum — `DocumentCategory`, 13
  values, a distinct axis from `document_type`), `delivery_mode` (enum,
  reusing the shared `DeliveryMode` — a second consumer, joining
  Services), `status` (free text, exact match), `date_from`/`date_to`
  (against `last_verified_at`); `page`/`page_size` (§6); `sort` (a
  `Literal` with one value, `"recent"`, matching §13–§15's identical
  no-popularity-ranking rationale). Deliberately has **no free-text `q`
  parameter**, for the same reason as every other domain — full-text
  search already exists at `/search` with `entity_type=document`.
- `GET /api/v1/documents/{slug}` — `slug` is the public identifier.
  Returns `requirements`/`supporting_documents`/`application_methods`
  nested inline (each a small child list — see
  [DATABASE.md](DATABASE.md) §14) rather than separate sub-resource
  endpoints, for the same "one response, no extra round trips"
  reasoning as `/jobs/{slug}`'s nested notifications. Two additional
  fields beyond every other domain's shape:
  - `service` — the "obtained through" relationship (§13 of the
    kickoff): `null` when no modeled `Service` exists, or when it
    exists but isn't itself publicly visible (the same trust-boundary
    rule §15's `related_services` already established).
  - `required_by` — "where this document may be required" (§14/§22 of
    the kickoff): a list of `{entity_type: "service" | "scheme", slug,
    name}` entries, built only from an explicit `civic_document_id`
    link on `RequiredDocument`/`SchemeRequiredDocument`, never inferred
    from matching names, and filtered to only publicly-visible parent
    records. Jobs never appear here — `app.jobs` has no document-
    requirement table at all, an accurate absence rather than a gap.
  Each `supporting_documents` entry also carries a nullable
  `civic_document` reference (`{slug, name}`) — present when that
  supporting document is itself a modeled `CivicDocument`, letting the
  frontend link to it directly.
- Same visibility rule as every other domain (§13–§15):
  `publication_status="PUBLISHED"` and `verification_status`
  `VERIFIED`/`NEEDS_REVIEW`, or an identical 404 — never distinguishing
  "doesn't exist" from "not yet published."
- See [DATABASE.md](DATABASE.md) §14 for the schema and
  [SEARCH.md](SEARCH.md) §18 for how a published document also becomes
  a search result (`entity_type="document"`), the fourth real domain to
  do so — with an explicit test that Jobs, Services, Schemes, and
  Documents all appear together in one cross-domain search result set.

## 18. Eligibility Engine (Phase 11)

Two endpoints, deliberately not shaped like every other domain's
list/detail pair — an evaluation is an action, not a browsable resource:

- `GET /api/v1/eligibility/criteria?entity_type=&entity_slug=` — the
  questions needed for an evaluation, no answers submitted. `entity_type`
  is `JOB`/`SCHEME`/`SERVICE` (`EligibilityEntityType` — Documents are
  excluded, see [DATABASE.md](DATABASE.md) §15); `entity_slug` resolves
  through that domain's own `get_*_by_slug` (its own visibility rule
  applies — an unpublished entity 404s here exactly as it would on its
  own detail page). Response: `supported` (`false` when no verified,
  published `EligibilityRule` exists for this entity — never fabricated
  as an evaluable case), and when `true`: `criteria` (one entry per
  condition — `attribute`, `operator`, a human-readable `expected`
  string, and a sourced `description`), `rule_id`/`rule_version`,
  `source`, `verification_status`, `last_verified`.
- `POST /api/v1/eligibility/evaluate` — body `{entity_type, entity_slug,
  answers}`. `answers` is every supported attribute, individually
  optional and range-validated (`age: 0-130`, `academic_percentage:
  0-100`, `academic_cgpa: 0-10`, etc.) — Pydantic's `extra="forbid"`
  rejects an unrecognized field outright, not silently. Response mirrors
  `criteria`'s shape plus: `outcome` (`ELIGIBLE`/`NOT_ELIGIBLE`/
  `INCOMPLETE`, `null` only when `supported` is `false`), `conditions`
  (the full per-criterion trace — `status`
  `PASS`/`FAIL`/`UNKNOWN`, the submitted value, and a `reason` string),
  `missing_attributes`/`failed_attributes` (convenience lists derived
  from `conditions`, so a client doesn't have to filter the trace
  itself), and `evaluated_at`.
- Submitted answers are read, evaluated, and discarded within the
  request — never persisted to any table, never logged (this phase's
  §G; [PRIVACY.md](PRIVACY.md) §1's minimization principle). No `auth`
  module exists yet ([DATABASE.md](DATABASE.md) §15's note), so there is
  no session to attach a stored `Profile` to in the first place —
  evaluation is stateless by necessity as well as by design.
- Evaluability is stricter than the standard visibility rule used by
  every list/detail endpoint above: only `verification_status ==
  VERIFIED` rules are ever evaluated (not `NEEDS_REVIEW`), since a
  verdict is a claim of fact rather than displayed content — see
  [DATABASE.md](DATABASE.md) §15.
- No pagination, filtering, or sorting conventions from §6 apply — this
  is a two-endpoint evaluation action, not a listing.
- See [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) for the underlying
  evaluation semantics and [DATABASE.md](DATABASE.md) §15 for the schema
  and its deviation from this document's original polymorphic sketch.

## 19. Auth, Tracking & Notifications (rescheduled from Phase 12)

**Auth** (`/api/v1/auth`) — see §4 for the cookie/CSRF mechanics:
- `POST /register` — body `{email, password}` (`password` min 10 chars,
  a floor not a full strength policy — entropy meters/breach-list
  checks are Phase 15 hardening). 201, sets the three session cookies,
  body `{user, csrf_token}`. 409 if the email (case-insensitively)
  already exists.
- `POST /login` — body `{email, password}`. 200, same cookie/body
  shape as register. 401 for any failure (unknown email, wrong
  password, or an OAuth-only account with no password set) — never
  distinguishing which, the same non-disclosure convention as every
  ownership check.
- `POST /refresh` — no body; reads the refresh cookie, rotates it. 200
  with fresh cookies on success; 401 (and clears all three cookies) on
  an expired/revoked/replayed refresh token.
- `POST /logout` — requires `X-CSRF-Token`. 204, clears all three
  cookies and revokes the presented refresh token.
- `GET /me` — the caller's own `{id, email, role,
  email_notifications_enabled}`. 401 if not authenticated.
- `PATCH /me` — requires `X-CSRF-Token`. Body
  `{email_notifications_enabled}` — the only field a user can currently
  self-update.

**Tracking** (`/api/v1/tracking`) — every route requires
authentication; ownership is enforced on every operation (§4):
- `GET /tracking` — the caller's own tracked items, each with
  display data joined from `search_documents`/`Source` (title, route,
  `verification_status`, `last_verified`, `source_organization`), a
  `still_available` flag (`false` when the entity has dropped out of
  `search_documents` — expired, withdrawn, or unpublished, without
  guessing why), and `deadline`/`deadline_expired` (computed from real
  structured data only — [DATABASE.md](DATABASE.md) §18 — `null` when
  the entity type or record has no deadline field).
- `POST /tracking` — requires `X-CSRF-Token`. Body `{entity_type,
  entity_slug, label?}` (`entity_type` is `job`/`service`/`scheme`/
  `document`; scholarships are tracked via their parent scheme's
  slug). 201. Idempotent: tracking an already-tracked (even paused)
  entity reactivates the existing row rather than erroring or
  duplicating. 404 if the entity doesn't exist or isn't publicly
  visible — the same non-disclosing 404 every domain's detail route
  uses.
- `PATCH /tracking/{id}` — requires `X-CSRF-Token`. Body
  `{label}` only.
- `POST /tracking/{id}/pause`, `POST /tracking/{id}/resume` — require
  `X-CSRF-Token`. A soft toggle (`is_active`), deliberately distinct
  from removal — pausing stops generating notifications for that item
  without losing the tracking record.
- `DELETE /tracking/{id}` — requires `X-CSRF-Token`. 204, hard delete.
- Every `{id}`-scoped route 404s identically for "doesn't exist" and
  "belongs to another user" (§4's IDOR-safe convention) — verified by
  a two-independent-authenticated-identities test.

**Notifications** (`/api/v1/notifications`) — every route requires
authentication; ownership enforced identically to Tracking:
- `GET /notifications?page=&page_size=` — the caller's own inbox,
  newest first, paginated (§6's conventions), plus `unread_count`.
  Notifications are produced only by the trusted sweep described in
  [DATABASE.md](DATABASE.md) §17-18 — no route here or anywhere else
  lets a client create one directly.
- `POST /notifications/{id}/read` — requires `X-CSRF-Token`. 200,
  idempotent (marking an already-read notification read again is a
  no-op, not an error).
- `POST /notifications/read-all` — requires `X-CSRF-Token`. 204, marks
  every one of the caller's unread notifications read in one bulk
  update.
- No route triggers the notification sweep or email delivery — those
  are an internal service function plus a manual ops script
  (`apps/api/scripts/run_notification_sweep.py`), never an HTTP
  endpoint, since no admin/internal-auth boundary exists yet to gate
  such a route safely ([DATABASE.md](DATABASE.md) §17's "no scheduler
  exists" note).

## 20. Civic AI Domain (Phase 12)

Three endpoints, none shaped like a list/detail pair — every one is an
action, not a browsable resource:

- `POST /api/v1/ai/ask` — body `{question, locale, entity_context?}`.
  `question` is length-validated (3–500 chars); `locale` is `en`/`te`;
  `entity_context` (optional `{entity_type, entity_slug}`) guarantees
  that entity's own knowledge chunk is considered even if the free-text
  question doesn't literally match it. Response: `grounding_status`
  (`GROUNDED`/`UNGROUNDED`/`INSUFFICIENT_EVIDENCE`/
  `PROVIDER_UNAVAILABLE` — see [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)
  §10), `answer` (`null` for every status except `GROUNDED` — an
  ungrounded or unavailable answer is never shown as if it were real),
  `citations[]` (each with `title`, `route`, `source`,
  `verification_status`, `last_verified`, `needs_review_caveat`),
  `message`, `disclaimer`, `locale`.
- `POST /api/v1/ai/explain-eligibility` — body `{entity_type,
  entity_slug, answers, locale}`, the same `answers` shape
  `/eligibility/evaluate` accepts (§18). Calls the real deterministic
  Eligibility Engine unmodified and only ever phrases its result — see
  [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §10's eligibility-integration
  note and `tests/test_ai/test_eligibility_explainer.py` for the proof
  that a provider actively trying to state the wrong outcome cannot
  succeed. Response: `status`
  (`EXPLAINED`/`NOT_SUPPORTED`/`PROVIDER_UNAVAILABLE`/
  `ENTITY_NOT_FOUND`), `outcome`, `explanation`, `rule_id`/
  `rule_version`, `source`, `verification_status`, `last_verified`,
  `message`.
- `GET /api/v1/ai/health` — diagnostic only: `{llm_configured,
  llm_provider, embedding_configured, embedding_provider}`. Never
  returns whether a call would actually succeed (no live provider ping)
  — only whether credentials are configured at all.
- Both POST endpoints are rate-limited (`app.ai.rate_limit`, an
  in-process per-IP sliding window — [SECURITY.md](SECURITY.md) §6's
  "strictest per-user limits" class) — a `429` includes `Retry-After`,
  using the standard error envelope (§7), which required fixing
  `handle_http_exception` to forward `exc.headers` (a real, previously
  latent gap: no endpoint had ever raised an `HTTPException` with custom
  headers before this phase).
- Submitted questions and eligibility answers are read, evaluated, and
  discarded within the request — never persisted to any table, never
  logged (no request-body logging exists anywhere in
  `app/core/logging.py`, and this router adds none) — this phase's
  explicit privacy requirement.
- No re-indexing endpoint exists — see
  [DATABASE.md](DATABASE.md) §16's "no auth mechanism exists yet" note.
- See [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §10 for the underlying
  retrieval/prompting/citation-validation pipeline and
  [DATABASE.md](DATABASE.md) §16 for the schema and its deviations from
  the original `pgvector`/foreign-key sketches.

## 21. Admin Intelligence Center (Phase 13, review/approval half only)

**Every route below requires `editor` or `admin` role** — a plain
`user` gets `403 Forbidden`, not `404` (this is a role check, not an
IDOR-safety concern; there is no per-object ownership to hide here,
unlike `/tracking`/`/notifications`). Role is read fresh from the
database on every request (the `User` row `get_current_user` already
loaded), never from the JWT's own claims — a role change takes effect
on the very next request. See
[SECURITY.md](SECURITY.md) §4 for the RBAC design and
`app.admin.service`'s module docstring
([DATABASE.md](DATABASE.md) §19) for this phase's narrower-than-
originally-sketched scope (review/approval of already-detected
changes and entity verification — no ingestion pipeline).

- `GET /api/v1/admin/dashboard` — real, data-backed metrics only (this
  phase's explicit "do not introduce fabricated dashboard statistics
  or popularity-based rankings"): `pending_change_records` (count),
  `verification_status_counts` (a count per `VerificationStatus`
  across all four domains), `recent_change_decisions`/
  `recent_verifications` (most recent, real rows — never a rolling
  "trending" computation).
- `GET /api/v1/admin/change-records?review_status=&page=&page_size=` —
  the `ChangeRecord` review queue (§6's pagination conventions),
  each with joined display data (`entity.title`/`route`/
  `verification_status`/`source_organization`) resolved directly from
  the entity's own domain table (not `search_documents`, since an
  `UNVERIFIED`/`EXPIRED` entity is never indexed there — see
  [DATABASE.md](DATABASE.md) §9's visibility rule); `entity.title`/
  `route` are `null` when the entity no longer exists, never a broken
  response.
- `POST /api/v1/admin/change-records/{id}/approve` and `.../reject` —
  require `X-CSRF-Token`, rate-limited
  (`app.admin.rate_limit.enforce_admin_rate_limit`, a per-user
  in-process sliding window — see [SECURITY.md](SECURITY.md) §14).
  `404` if the record doesn't exist; `409 Conflict` if the record was
  already decided the *other* way (approving an already-`REJECTED`
  record or vice versa); re-issuing the *same* decision is a `200`
  idempotent no-op, not an error. Approving also runs the existing
  notification generator (Tracking + Notifications) — dedup-safe, so
  retrying an approval never double-notifies a tracker.
- `GET /api/v1/admin/verification/queue?entity_type=&page=&page_size=`
  — entities with `verification_status` `NEEDS_REVIEW` or `UNVERIFIED`
  (the default; not overridable via query param this phase) across
  job/scheme/service/document, combined and paginated (§19 of
  [DATABASE.md](DATABASE.md) explains why this is done in Python, not
  one SQL query).
- `POST /api/v1/admin/verification/{entity_type}/{entity_id}` — body
  `{status, source_id, review_due_at?}`. Requires `X-CSRF-Token`,
  rate-limited. `source_id` is **required, not optional** — Pydantic
  rejects a missing one with `422` before the handler even runs (this
  phase's explicit "no approval without evidence"); a `source_id` that
  doesn't resolve to a real `Source` row is also `422` (evidence that
  doesn't exist is treated the same as no evidence); a nonexistent
  entity is `404`. On success (`201`): creates the `VerificationRecord`
  and updates the entity's own `verification_status` in the same
  transaction, then re-syncs its search-index membership.
- `GET /api/v1/admin/sources?page=&page_size=` and
  `GET /api/v1/admin/sources/{id}` — read-only browsing of existing
  `Source`/`SourceVersion` rows (version history on the detail route).
  No route creates a `Source` or `SourceVersion` this phase — see
  [DATABASE.md](DATABASE.md) §19 and
  [DATA_SOURCES.md](DATA_SOURCES.md) for why.
- No route triggers a live fetch, publishes autonomously, or exposes
  any ingestion-pipeline capability — none exists (§ROADMAP.md's Phase
  13 scope-difference note).

This document defines the target API conventions for Phase 2 onward; each
domain phase (6–9, 10–12) implements against it and updates this document
only where real implementation reveals a convention gap.
