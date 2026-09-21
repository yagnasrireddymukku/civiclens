# ADR-004: PostgreSQL as Primary Database

## Status
Accepted

## Context
CivicLens's core data is deeply relational (states → districts →
constituencies; jobs → notifications → exams → deadlines; eligibility rules
and conditions; provenance/verification records with foreign keys
everywhere). It also needs full-text search (MVP, [ADR-005](ADR-005-search-architecture.md))
and vector similarity search for AI retrieval ([ADR-006](ADR-006-ai-rag-architecture.md)).

## Decision
Use **PostgreSQL** as the single primary datastore, with the `pg_trgm`
extension for fuzzy/typo-tolerant text search and the `pgvector` extension
for embedding storage/similarity search.

## Alternatives Considered
- **NoSQL document store (e.g., MongoDB)** as primary store: rejected — the
  domain is inherently relational with strict referential integrity needs
  (eligibility rules referencing entities, provenance chains); modeling
  this in a document store would fight the data shape.
- **Separate dedicated vector database (e.g., Pinecone/Weaviate)**:
  rejected at MVP — `pgvector` avoids operating a second database for a
  workload that, at launch scale (two states, a curated set of domains), is
  well within Postgres's capability. Revisit only if embedding volume/query
  latency demonstrably outgrows it (documented in a future ADR, not
  assumed now).
- **Separate dedicated search engine at launch (Elasticsearch/OpenSearch)**:
  see [ADR-005](ADR-005-search-architecture.md) — deferred, not rejected
  outright.

## Consequences
- One database to operate, back up, and secure at MVP — lower operational
  complexity ([CLAUDE.md](../../CLAUDE.md): avoid unnecessary databases).
- `pgvector` and `pg_trgm` must be enabled as extensions; this is a minor,
  well-supported operational step on any managed Postgres provider.
- A future migration to a dedicated search/vector engine is possible
  without touching the source-of-truth schema, since those systems would
  be projections of Postgres data, not the system of record.
