# CivicLens — Civic Search Engine Architecture

This document defines the architecture for Engine A, Civic Search, per
[ADR-005](ADR/ADR-005-search-architecture.md). **Phase 5 ("Search
Infrastructure" — [ROADMAP.md](ROADMAP.md)) implemented the search
infrastructure itself** — the `search_documents` projection, the
`GET /api/v1/search` endpoint, and the frontend search page. **Phase 6
made Jobs the first real domain module to call `upsert_search_document`
(§14), and Phase 7 made Services the second (§15)** — proving the
abstraction generalizes across domains, not something built once and
never exercised again. Every result is still a synthetic fixture (no
real government data exists yet). Phase 8 made Schemes the third
(§16), with an explicit test that Jobs, Services, and Schemes all
appear together in one cross-domain result set. **Phase 9 deliberately
added no fourth `entity_type`** — Scholarships are a `Scheme`
specialization, already indexed as `entity_type="scheme"` since §16
(see §17). **Phase 10 made Documents the actual fourth**
(`entity_type="document"`, §18), with an explicit test that Jobs,
Services, Schemes, and Documents all appear together in one
cross-domain result set. Exams, representatives, and elections remain
unindexed; §3 and §12–18 describe what's actually built and are
updated again as each of those lands.

## 1. Core Principle: Search Is a Projection, Not a System of Record

Per [ADR-004](ADR/ADR-004-postgresql.md) and
[ARCHITECTURE.md](ARCHITECTURE.md) §5, Civic Search owns no data of its
own — it is a **read-side projection** of the domain tables in
[DATABASE.md](DATABASE.md) (jobs, exams, schemes, services, scholarships,
representatives, elections, documents). Consequences:

- The search index can be dropped and rebuilt from source tables at any
  time with no data loss.
- Search never becomes a secondary source of truth that can drift from
  the domain tables — indexing is one-directional (domain tables →
  index), never the reverse.
- Disabling search entirely does not affect any other engine
  ([ROADMAP.md](ROADMAP.md) Phase 5 rollback note).

## 2. MVP Approach: PostgreSQL FTS + pg_trgm

Per [ADR-005](ADR/ADR-005-search-architecture.md), launch search runs
directly against the primary Postgres database — no separate search
infrastructure:

- **`tsvector`/`tsquery`** (PostgreSQL full-text search) for token-based
  matching and ranking (`ts_rank`) over indexed text fields.
- **`pg_trgm`** (trigram similarity) for typo tolerance and prefix
  matching/autocomplete, via GIN trigram indexes
  ([DATABASE.md](DATABASE.md) §4).
- Both are extensions of the existing Postgres instance — no new
  datastore to provision, replicate, or keep in sync
  ([CLAUDE.md](../CLAUDE.md): avoid unnecessary dependencies).

This is deliberately the simplest approach that satisfies FR-SR1–4
([PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §1.6) at launch-scale
corpus size (two states, a curated domain set) — not a permanent ceiling.

## 3. What Gets Indexed

Rather than a generated `search_vector` column on each domain table,
Phase 5 built one generic, polymorphic projection table,
`search_documents` (`apps/api/app/search/models.py`), keyed on
`(entity_type, entity_id, locale)` with no foreign key to any domain
table — matching the `sources`/`change_records` polymorphic pattern
already used elsewhere ([ARCHITECTURE.md](ARCHITECTURE.md) §6). This was
chosen over per-domain generated columns because **no domain table exists
yet** (§1's "clean search abstraction" requirement, this phase's scope):
a future domain module (jobs, schemes, ...) calls
`upsert_search_document`/`remove_search_document`
(`apps/api/app/search/service.py`) when it publishes or retires an
entity; nothing outside that module ever constructs a `tsquery` or
touches `search_vector` directly, so replacing the underlying engine
later (§10) means rewriting `app/search/service.py`, not every future
caller.

Each row carries: `title`, `summary`, `searchable_text` (weighted A/B/C
respectively — title outranks summary outranks incidental body text),
`route`, `state_id`/`district_id` (nullable FKs), `category`, `status`,
`source_id` (FK, `NOT NULL`) and `verification_status` — provenance is
carried on every row, never optional (§13's `source` field on every
result). A trigram (`gin_trgm_ops`) index on `title` backs §5's fallback;
a GIN index on `search_vector` backs exact matching.

Only `VERIFIED` and `NEEDS_REVIEW` documents are indexable —
`upsert_search_document` raises `ValueError` if called with any other
`VerificationStatus`, so `UNVERIFIED`/`EXPIRED` content can never reach
the index by omission of a filter; a caller must explicitly call
`remove_search_document` when an entity's status changes.

Locale-specific text is indexed per-locale (`locale` is part of the
uniqueness key): a Telugu query matches Telugu-locale rows, not a machine
transliteration of the English field.

## 4. Autocomplete Design

**Not built in Phase 5** — this phase's scope was full search only
(`GET /api/v1/search`), not a separate as-you-type suggestion endpoint.
The design below remains the plan for when autocomplete is prioritized:

- Prefix/substring matching via `pg_trgm` similarity (`%` operator) against
  the same weighted title/name fields, ordered by similarity score, capped
  to a small result count (e.g., top 8) for low-latency as-you-type
  suggestions.
- Autocomplete would be a distinct, cheaper query path from full search —
  not running the full `tsquery` ranking pipeline, since it optimizes for
  latency on every keystroke rather than exhaustive relevance.

## 5. Typo Tolerance

Implemented in `search_documents()` (`app/search/service.py`) as a
two-step fallback, never a blended/merged score (kept deterministic and
testable, §8): first, an exact `websearch_to_tsquery` match; only if that
returns **zero** rows does the query re-run using
`word_similarity(query, title) > 0.4` (a `pg_trgm` function, not plain
`similarity()` — see the code comment for why: `similarity()` scores a
short query against a long title's *entire* text and under-scores an
obvious typo, while `word_similarity()` scores it against the title's
best-matching substring). This threshold and mechanism were verified
directly against fixtures: a real typo ("pasport") scores 0.70; unrelated
text scores 0.0. The response's `query.fuzzy_fallback_used` flag tells
the caller (and the frontend, §13) which path served the result, so a UI
can honestly label a fuzzy-matched result set.

## 6. Filters

Implemented in `_apply_filters()` (`app/search/service.py`) as SQL
`WHERE` clauses AND-ed with the text-search predicate, applied
identically to the count query and the results query and to both the
exact and fuzzy branches — never post-filtering an already-paged result
set (per FR-SR2 and [API.md](API.md) §6):

- **`entity_type`** (the future domain discriminator — no fixed enum yet
  at Phase 5 since no domain module exists; see §11)
- **`state_id`** / **`district_id`** (the geography foreign keys,
  [DATABASE.md](DATABASE.md) §2.1)
- **`category`** / **`status`** (free-text, entity-defined at this phase)
- **`date_from`** / **`date_to`** (against `last_verified_at`)

Every query param is bound via SQLAlchemy, never string-interpolated —
directly verified with a hostile query string
(`tests/test_search/test_service.py::test_query_string_is_not_vulnerable_to_sql_injection`).

## 7. Multilingual Query Handling & Known Limitations

- The caller supplies `locale` explicitly (from the active
  frontend locale, [FRONTEND.md](FRONTEND.md) §7) — Civic Search does not
  attempt language *detection*; it routes to the matching locale's
  indexed rows (`SearchDocument.locale`, part of the uniqueness key).
- **Known, accepted MVP limitation**, implemented exactly as
  [ADR-005](ADR/ADR-005-search-architecture.md) anticipated: PostgreSQL
  has no native Telugu text-search configuration (no stemming
  dictionary equivalent to `english`'s). `_ts_config()`
  (`app/search/service.py`) selects the `english` FTS configuration for
  `locale="en"` and falls back to `simple` (unstemmed) for every other
  locale, `pg_trgm` similarity being the primary practical matching
  mechanism once stemming-based ranking isn't available. This means
  Telugu search quality is expected to lag English search quality — a
  documented gap, not a silent one, and the leading trigger for the
  upgrade path in §10.

## 8. Relevance & Ranking

- Primary signal on an exact match: `ts_rank_cd` over the weighted
  `search_vector` (§3). Primary signal on a fuzzy-fallback match (§5):
  the `word_similarity` score itself.
- Secondary tie-breaker in both cases: recency (`last_verified_at`,
  nulls last) — `_order_by_relevance_or_recency()`.
- `sort=last_verified` (`SearchSortOption`, an explicit two-value
  allow-list, never an arbitrary client-supplied column name) overrides
  relevance ordering entirely when the caller wants newest-first.
- Verification status is not a ranking signal that hides content — a
  `NEEDS_REVIEW` document ranks exactly where its text relevance places
  it; the frontend surfaces its status via a distinct badge
  (§13) per [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §4 — ranking and
  trust signaling are kept as separate concerns.
- No personalization, popularity, or political ranking (this phase's
  explicit prohibition) — results are deterministic for a given query +
  filter set, which also keeps search behavior testable (14 deterministic
  tests in `tests/test_search/test_service.py`).

## 9. Intent Detection — Relationship to Civic AI

Civic Search performs lightweight intent signals only: recognizing an
obvious domain keyword, a state/district name, or a qualification term
within the query, to bias filters (e.g., "TSPSC group 2 andhra" implying
domain=jobs, state=Telangana). This is **not** the same component as
[AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §2's structured intent/query
analysis — Civic AI's retrieval layer consumes Civic Search (and direct
DB queries) as one of its two retrieval paths, but owns its own, richer
intent classification for natural-language questions. Civic Search's
intent detection exists to improve keyword-search relevance; it is not
redefined here beyond that boundary.

## 10. Upgrade Path: Meilisearch

[ADR-005](ADR/ADR-005-search-architecture.md) names Meilisearch as the
leading upgrade candidate (strong typo tolerance and multilingual support,
low operational overhead relative to Elasticsearch/OpenSearch). Concrete
triggers for migration — any one of these is sufficient to open the
migration work, not a required combination:

1. **Corpus size**: indexed row count grows large enough that Postgres FTS
   query latency on filtered searches regresses past the NFR-P1 target
   ([PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) §2.2) under
   realistic load — expected as domain/geography coverage expands past
   AP + Telangana (Phase 18).
2. **Ranking quality complaints**: user/editorial feedback or measured
   search-abandonment indicates `ts_rank` ordering is materially worse
   than users expect for common queries, and weight-tuning has been tried
   and is insufficient.
3. **Multilingual quality**: Telugu search quality (§7) remains a
   recurring, named complaint after the `simple`+`pg_trgm` approach has
   been tuned — Meilisearch's language-agnostic tokenizer and stronger
   typo-tolerance ranking are expected to materially improve this.

Because search is a projection (§1), migration is an additive
infrastructure change: stand up Meilisearch, build an indexing pipeline
from the same source tables, cut the `/search` route's backing
implementation over, and decommission the Postgres FTS query path — no
schema change to the source-of-truth tables, no data migration risk to
anything but the disposable index itself.

## 11. Explicitly Not Built Yet

- Any *real* domain data — every row in the database today is a
  clearly-fictional fixture, gated to `local`/`test` environments only
  ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §7): `app/search/fixtures.py`
  (`TEST_JOB`/`TEST_SERVICE`/`TEST_SCHEME`), `app/jobs/fixtures.py`'s one
  synthetic job (§14), and `app/services/fixtures.py`'s one synthetic
  service (§15).
- Exams, representatives, and elections indexing anything — Jobs
  (Phase 6), Services (Phase 7), Schemes (Phase 8), and Documents
  (Phase 10) are the only real domain modules calling
  `upsert_search_document` so far. Scholarships (Phase 9) are already
  covered — they're `Scheme` rows, not a fourth module (§17).
- Autocomplete (§4) and any dedicated as-you-type endpoint.
- Any Meilisearch (or other dedicated search engine) infrastructure — not
  provisioned until a §10 trigger is met and documented.
- Semantic/vector-based search ranking — that capability lives in Civic
  AI's retrieval layer ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §3), not
  in Civic Search itself, at this phase.
- Search analytics / zero-result-query logging
  ([OBSERVABILITY.md](OBSERVABILITY.md)).

## 12. Implementation: `search_documents` & API Contract

- **Table**: `search_documents` (`app/search/models.py`), migrated in
  `alembic/versions/5d30d9b37791_add_search_documents.py`. The migration
  runs `CREATE EXTENSION IF NOT EXISTS pg_trgm` itself — every environment
  that migrates to `head`, including test infrastructure
  (`apps/api/tests/_full_pg_utils.py`), needs a Postgres build shipping
  that contrib module (see [TESTING.md](TESTING.md) §3).
- **Write path**: `upsert_search_document()` / `remove_search_document()`
  (`app/search/service.py`) — the only functions that ever write to this
  table. A domain module calls these from wherever it manages its own
  entities' lifecycle — see §14 for Jobs, the first real caller.
- **Read path**: `search_documents()` (`app/search/service.py`) — see §5,
  §6, §8 for its query flow, filters, and ranking.
- **Endpoint**: `GET /api/v1/search` (`app/api/v1/search.py`), query
  params bound via `SearchQueryParams`
  (`app/search/schemas.py`): `q` (≤200 chars), `entity_type`, `state_id`,
  `district_id`, `category`, `status`, `date_from`, `date_to`, `locale`
  (default `en`), `page`/`page_size` (default 20, max 50, per
  [API.md](API.md) §6's pagination convention), `sort`. Response is
  `SearchResponse`: `results` (each carrying a public composite
  `id` — `"{entity_type}:{entity_id}"`, never the raw internal
  `search_documents.id`, per [API.md](API.md) §12 — plus `source`
  provenance and `verification_status` on every item), `pagination`, and
  `query` (echoes `q`/`locale` and `fuzzy_fallback_used`, §5).

## 13. Frontend Integration

- `apps/web/app/[locale]/search/page.tsx` — a Server Component reading
  `q`/`page` from `searchParams`, so results are shareable/bookmarkable
  URLs (`/en/search?q=...`, `/te/search?q=...`) that reproduce on reload
  with no client-side result state.
- Composes Phase 4's `SearchBar` and `SearchResultCard`
  (`apps/web/components/civic`) — `SearchControls.tsx` is the one
  Client Component island, handling the query input and pagination
  control, navigating to a new `?q=&page=` URL on submit/page-change
  rather than fetching client-side.
- **Every result on this page is synthetic fixture data** (§11) — the
  page renders a persistent, translated "Development data" notice
  (`Search.devDataTitle`/`devDataBody` in `messages/*.json`) above the
  results for exactly this reason; it must not be removed before real
  domain data exists, and should be revisited once it does (per this
  phase's explicit "do not present synthetic results as production
  CivicLens information" requirement).
- `verification_status` maps to a `SourceBadge` (`VERIFIED` → "verified",
  anything else indexable → "available") rather than the fuller
  `VerificationStatus` badge component, matching `SearchResultCard`'s
  existing (Phase 4) prop contract.
- Shared response types/schemas live in `@civiclens/types` and
  `@civiclens/validation` (`SearchResponse`, `searchResponseSchema`) —
  the first hand-written domain types in those packages, added ahead of
  the OpenAPI-generation tooling named in [API.md](API.md) §10.
- A failed/unreachable API call renders an honest inline error state
  (never a crash), matching `apps/web/lib/api.ts`'s existing
  `getApiHealth` contract — see `apps/web/lib/search.ts`.

## 14. Jobs Domain Integration (Phase 6)

Jobs is the first real domain module to index into `search_documents` —
the pattern Services (§15), Schemes (§16), and every future domain
module (exams, scholarships) follows:

- `entity_type="job"`, `entity_id=<jobs.id>` (not the raw slug — the
  search abstraction stays domain-agnostic and never assumes a domain
  table has a `slug` column).
- `sync_job_search_index()` (`app/jobs/service.py`) is the one place
  that decides indexability: it calls `upsert_search_document` when a
  job is `publication_status="PUBLISHED"` and
  `verification_status` is `VERIFIED`/`NEEDS_REVIEW` (the same rule
  `app/jobs/service.py`'s own read path enforces, so a job is never
  visible in search but 404 on its own detail page or vice versa), and
  `remove_search_document` otherwise — never both, never left stale.
- `route="/jobs/{slug}"`, `locale=job.locale` (§9's "no bilingual content
  model" — a Telugu-tagged job would index into and surface from a
  Telugu search, never a machine-translated English one),
  `searchable_text` combines `qualification_summary`/
  `experience_summary`/`category` (fields not otherwise weighted into
  `title`/`summary`).
- This phase calls `sync_job_search_index()` only from
  `app/jobs/fixtures.py` (no admin/editing UI exists yet to change a
  job's publication state after creation) — a future ingestion/admin
  phase calls it again whenever a job's publication or verification
  state changes.
- Verified directly: a job indexed this way is findable via
  `GET /api/v1/search?q=...` with `entity_type: "job"` and the job's own
  `route` in the result (`tests/test_jobs/test_api.py::
  test_indexed_job_is_findable_via_the_generic_search_endpoint`).

## 15. Services Domain Integration (Phase 7)

Services is the second real domain module to index into
`search_documents`, and the first proof that §14's pattern actually
generalizes rather than being Jobs-specific:

- `entity_type="service"`, `entity_id=<services.id>` — same
  domain-agnostic shape as Jobs, no special-casing.
- `sync_service_search_index()` (`app/services/service.py`) mirrors
  `sync_job_search_index()` exactly: indexes when
  `publication_status="PUBLISHED"` and `verification_status` is
  `VERIFIED`/`NEEDS_REVIEW` (the identical rule
  `app/services/service.py`'s own read path enforces), removes
  otherwise.
- `route="/services/{slug}"`, `locale=service.locale`,
  `searchable_text` combines `target_audience`/`service_type` (fields
  not otherwise weighted into `title`/`summary`), `category` is the
  enum's string value (`service.category.value`) since
  `search_documents.category` is a plain text column.
- Verified directly: a service indexed this way is findable via
  `GET /api/v1/search?q=...` with `entity_type: "service"` and the
  service's own `route` in the result
  (`tests/test_services/test_api.py::
  test_indexed_service_is_findable_via_the_generic_search_endpoint`),
  and a single query can return both a job and a service result
  together (`test_cross_domain_search_returns_both_jobs_and_services`)
  — verified live end-to-end as well as via automated tests.

## 16. Schemes Domain Integration (Phase 8)

Schemes is the third real domain module to index into
`search_documents`, and the explicit architectural test that the
abstraction generalizes to a *third* independent caller, not just two:

- `entity_type="scheme"`, `entity_id=<schemes.id>` — same
  domain-agnostic shape as Jobs/Services, no special-casing.
- `sync_scheme_search_index()` (`app/schemes/service.py`) mirrors
  `sync_service_search_index()` exactly: indexes when
  `publication_status="PUBLISHED"` and `verification_status` is
  `VERIFIED`/`NEEDS_REVIEW` (the identical rule
  `app/schemes/service.py`'s own read path enforces), removes
  otherwise.
- `route="/schemes/{slug}"`, `locale=scheme.locale`,
  `searchable_text` is `scheme.target_audience` (the one prose field not
  otherwise weighted into `title`/`summary` — unlike Services, a scheme
  has no second free-text field like `service_type` to also combine in),
  `category` is the enum's string value (`scheme.category.value`).
- Verified directly: a scheme indexed this way is findable via
  `GET /api/v1/search?q=...` with `entity_type: "scheme"` and the
  scheme's own `route` in the result
  (`tests/test_schemes/test_service.py::
  test_sync_scheme_search_index_indexes_a_publicly_visible_scheme`), and
  a single query can return a job, a service, and a scheme result
  together — the literal Phase 8 acceptance criterion
  (`tests/test_schemes/test_api.py::
  test_cross_domain_search_returns_jobs_services_and_schemes`) — verified
  live end-to-end as well as via automated tests.

## 17. Scholarships (Phase 9) — No New `entity_type`

Scholarships are represented as a `Scheme` specialization (`category ==
"SCHOLARSHIP"` plus a 1:1 `ScholarshipDetail` extension row — see
[DATABASE.md](DATABASE.md) §13), not an independent domain. This phase's
§15 explicitly asked the architecture to justify `entity_type="scholarship"`
before creating one; the decision here is **not to**:

- A scholarship scheme is a row in `schemes`, already indexed via
  `sync_scheme_search_index()` (§16) with `entity_type="scheme"` the
  moment it's published and verified — nothing scholarship-specific
  needed to change in `app/search/` or `app/schemes/service.py`'s
  indexing call for this to work.
- `searchable_text` is unchanged (`scheme.target_audience`) — the new
  `scholarship_details` fields (education level, academic requirements,
  application window) are not folded into the indexed text. They're
  structured data surfaced via `GET /api/v1/schemes/{slug}` (§16's
  API.md entry) and the `education_level` list filter, not free-text
  search inputs; nothing in this phase's §18 asked for
  "find me an undergraduate scholarship" as a *keyword* search
  experience distinct from the `education_level` filter already built.
- Verified directly: the existing Phase 8 cross-domain search test
  (`test_cross_domain_search_returns_jobs_services_and_schemes`) and the
  live smoke test both re-confirmed cross-domain search is unaffected —
  a scholarship-category scheme is findable via `/search` exactly like
  any other scheme, with `entity_type: "scheme"` in the result, not a
  fourth type.

## 18. Documents Domain Integration (Phase 10)

Documents is the fourth real domain module to index into
`search_documents` — and, unlike Scholarships (§17), a genuine fourth
`entity_type`, since `CivicDocument` is a first-class domain entity
(see [DATABASE.md](DATABASE.md) §14 for the full architectural
distinction from `RequiredDocument`/`SchemeRequiredDocument`):

- `entity_type="document"`, `entity_id=<civic_documents.id>` — same
  domain-agnostic shape as Jobs/Services/Schemes, no special-casing.
- `sync_document_search_index()` (`app/documents/service.py`) mirrors
  `sync_scheme_search_index()` exactly: indexes when
  `publication_status="PUBLISHED"` and `verification_status` is
  `VERIFIED`/`NEEDS_REVIEW` (the identical rule
  `app/documents/service.py`'s own read path enforces), removes
  otherwise.
- `route="/documents/{slug}"`, `locale=document.locale`,
  `searchable_text` is `document.purpose` (the one prose field not
  otherwise weighted into `title`/`summary`), `category` is the enum's
  string value (`document.category.value`) — `document_type` is
  deliberately not also folded into `searchable_text` or `category`;
  it's a separate filter dimension (§6 of this document, [API.md](API.md)
  §17), not additional search text.
- Verified directly: a document indexed this way is findable via
  `GET /api/v1/search?q=...` with `entity_type: "document"` and the
  document's own `route` in the result
  (`tests/test_documents/test_service.py::
  test_sync_document_search_index_indexes_a_publicly_visible_document`),
  and a single query can return a job, a service, a scheme, and a
  document result together — the literal Phase 10 acceptance criterion
  (`tests/test_documents/test_api.py::
  test_cross_domain_search_returns_jobs_services_schemes_and_documents`)
  — verified live end-to-end as well as via automated tests.

This document is updated again with real query patterns as each further
domain module starts calling `upsert_search_document`, per
[ROADMAP.md](ROADMAP.md)'s documentation requirement.
