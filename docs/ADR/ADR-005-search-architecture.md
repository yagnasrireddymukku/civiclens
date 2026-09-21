# ADR-005: Search Architecture

## Status
Accepted

## Context
Civic Search must support keyword search, natural-language queries,
filters, autocomplete, typo tolerance, and multilingual (English/Telugu)
search ([PRODUCT_REQUIREMENTS.md](../PRODUCT_REQUIREMENTS.md) FR-SR1–4).
At MVP scale (two states, a curated domain set), data volume is modest.

## Decision
Launch with **PostgreSQL full-text search (`tsvector`/`tsquery`) combined
with `pg_trgm`** for typo tolerance and prefix/autocomplete matching, built
directly against the primary database (no separate search infrastructure).
Document a clear upgrade path to a dedicated search engine (**Meilisearch**
as the leading candidate — lightweight, strong typo tolerance and
multilingual support, far less operational overhead than an
Elasticsearch/OpenSearch cluster) for when volume, ranking sophistication,
or multilingual complexity outgrow Postgres. See full design in
[SEARCH.md](../SEARCH.md).

## Alternatives Considered
- **Elasticsearch/OpenSearch from day one**: rejected — a dedicated search
  cluster is significant operational overhead unjustified at launch scale
  ([CLAUDE.md](../../CLAUDE.md): avoid unnecessary distributed systems).
- **Meilisearch/Typesense from day one**: reasonable alternative, deferred
  rather than rejected — adding a second datastore to keep in sync with
  Postgres is complexity to defer until Postgres FTS demonstrably can't
  keep up (e.g., ranking quality, multilingual tokenization, or latency at
  scale).
- **External SaaS search (e.g., Algolia)**: rejected — recurring cost and a
  third-party dependency on public-interest infrastructure, deferred until
  a clear need and budget case exists.

## Consequences
- Search is powered by the same database as the source of truth — no
  sync/consistency problem at MVP.
- `pg_trgm` handles typo tolerance and fuzzy matching adequately for the
  initial two-state, curated-domain corpus size.
- Multilingual (Telugu) search quality via Postgres FTS is limited (no
  native Telugu text-search configuration); initial approach relies on
  trigram similarity plus locale-aware content fields
  ([ARCHITECTURE.md](../ARCHITECTURE.md) §10) rather than linguistic
  stemming. This is an accepted MVP limitation, revisited when a dedicated
  search engine is introduced.
- Migration path is designed for: search is a read-side projection
  ([ARCHITECTURE.md](../ARCHITECTURE.md) §5), so replacing the query engine
  later does not touch the schema or the source-of-truth data.
