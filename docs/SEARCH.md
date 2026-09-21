# CivicLens — Civic Search Engine Architecture

This document defines the target architecture for Engine A, Civic Search,
per [ADR-005](ADR/ADR-005-search-architecture.md). It is the reference for
Phase 5 ("Search Infrastructure" — [ROADMAP.md](ROADMAP.md)). **No search
index, query endpoint, or ranking logic exists yet.**

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

A generated `search_vector` (`tsvector`) column per searchable entity,
combining weighted fields, plus companion `pg_trgm` indexes on the
highest-value autocomplete fields:

| Entity | Indexed fields (weighted) |
|---|---|
| `jobs` | title (A), organization name (B), department name (C), description (D) |
| `job_notifications` | notification_number (B) |
| `exams` | name (A), conducting_body name (B) |
| `schemes` | name (A), description (B), target beneficiary summary (C) |
| `scholarships` | name (A), education_level (B), description (C) |
| `services` | name (A), description (B), channel (C) |
| `representatives` | name (A), constituency name (B), role (C) |
| `elections` | constituency name (A), election_date-derived label (B) |
| `documents` | name (A), typical_use (B) |

Weighting (`A`–`D`, Postgres FTS's standard rank weights) biases ranking
toward title/name matches over incidental description matches. Only
`VERIFIED` and `NEEDS_REVIEW` records are indexed (§7) — `UNVERIFIED` and
soft-deleted rows are excluded by the indexing query itself, not filtered
at query time, so they can never leak into results by omission of a
filter.

Locale-specific text (English/Telugu translatable fields,
[DATABASE.md](DATABASE.md) §0.4) is indexed per-locale: a Telugu query
matches Telugu-locale field content, not a machine transliteration of the
English field.

## 4. Autocomplete Design

- Prefix/substring matching via `pg_trgm` similarity (`%` operator) against
  the same weighted title/name fields, ordered by similarity score, capped
  to a small result count (e.g., top 8) for low-latency as-you-type
  suggestions.
- Autocomplete is a distinct, cheaper query path from full search — it
  does not run the full `tsquery` ranking pipeline, since it optimizes for
  latency on every keystroke rather than exhaustive relevance.

## 5. Typo Tolerance

`pg_trgm` similarity scoring (not edit-distance/Levenshtein directly)
handles minor misspellings by falling back from an exact/`tsquery` match
to a trigram-similarity match when the exact match returns few or no
results — e.g., "TSPC" still surfaces "TSPSC" results. This is the
mechanism validated by Phase 5's acceptance criterion (a deliberately
misspelled query must return correct ranked results,
[ROADMAP.md](ROADMAP.md) Phase 5).

## 6. Filters

Per FR-SR2, applied as SQL `WHERE` clauses alongside the text-search
predicate, on indexed columns — never as post-filtering of an
already-paged result set:

- **Domain** (jobs/exams/schemes/services/scholarships/representatives/
  elections/documents)
- **State** / **district** (via the geography foreign keys,
  [DATABASE.md](DATABASE.md) §2.1)
- **Status** (upcoming/open/closed, or entity-specific status)
- **Date range** (against relevant `deadlines`/`published_date` fields)

Filters combine with the text query as AND conditions, matching the
convention in [API.md](API.md) §6.

## 7. Multilingual Query Handling & Known Limitations

- Query language is detected (or explicitly supplied by the client based
  on active locale, [FRONTEND.md](FRONTEND.md) §7) and routed to the
  matching locale's indexed content.
- **Known, accepted MVP limitation** (per
  [ADR-005](ADR/ADR-005-search-architecture.md)): PostgreSQL has no native
  Telugu text-search configuration (no Telugu stemming/lemmatization
  dictionary equivalent to `english`'s). Telugu search at MVP relies on:
  - `simple` (unstemmed) `tsvector` configuration for Telugu text, plus
  - `pg_trgm` similarity as the primary practical matching mechanism for
    Telugu queries, since stemming-based ranking isn't available.
  This means Telugu search quality is expected to lag English search
  quality — a documented gap, not a silent one. It is surfaced honestly
  (no claim of equivalent linguistic sophistication) and is the leading
  trigger for the upgrade path in §9.

## 8. Relevance & Ranking

- Primary signal: `ts_rank`/`ts_rank_cd` weighted by field (§3).
- Secondary tie-breaker: recency (e.g., `published_date`/`updated_at`) for
  time-sensitive domains (jobs, exams) where a newer notification should
  generally outrank an older one of similar textual relevance.
- Verification status is not a ranking signal that hides content, but
  `NEEDS_REVIEW` results are visually flagged in the UI per
  [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §4 — ranking and trust
  signaling are kept as separate concerns.
- No personalization or click-through-based ranking at MVP — results are
  deterministic for a given query + filter set, which also keeps search
  behavior testable ([ROADMAP.md](ROADMAP.md) Phase 5 test requirement).

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

- Any actual `tsvector` column, index, or query implementation.
- Any Meilisearch (or other dedicated search engine) infrastructure — not
  provisioned until a §10 trigger is met and documented.
- Semantic/vector-based search ranking — that capability lives in Civic
  AI's retrieval layer ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §3), not
  in Civic Search itself, at this phase.

This document defines the target search architecture for Phase 5; it is
updated with real query patterns and index definitions once implementation
begins, per [ROADMAP.md](ROADMAP.md) Phase 5's documentation requirement.
