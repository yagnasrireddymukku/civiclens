# CivicLens — Architecture Overview

This is the top-level architecture reference. It defines technology
decisions, structural boundaries, and cross-cutting principles that every
other document ([DATABASE.md](DATABASE.md), [API.md](API.md),
[FRONTEND.md](FRONTEND.md), [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md), etc.)
must remain consistent with. Detailed infrastructure/deployment topology
lives in [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md); rationale for
each decision is recorded in [ADR/](ADR/README.md).

## 1. Architectural Style

**Modular monolith**, not microservices. One backend service (FastAPI) with
strict internal module boundaries per domain (jobs, exams, schemes,
eligibility, search, ai, tracking, sources/ingestion). Modules communicate
in-process through defined interfaces, not network calls. A module is
extracted into its own service only when there is a documented, measured
reason (load isolation, independent deploy cadence, language mismatch) —
see [ADR-001](ADR/ADR-001-monorepo-architecture.md).

Rationale: at MVP scale, microservices add operational cost (deployment,
networking, observability, data consistency) without a corresponding
benefit. A modular monolith with clean boundaries can be split later without
a rewrite, because the module boundaries already exist in code.

Explicitly avoided unless a documented need arises: Kubernetes, message
buses/event streaming platforms, multiple databases, service meshes.

## 2. Technology Stack

| Layer | Choice | ADR |
|---|---|---|
| Monorepo tooling | pnpm workspaces (JS/TS) + Poetry/uv (Python), no Turborepo/Nx at MVP | [ADR-001](ADR/ADR-001-monorepo-architecture.md) |
| Frontend | Next.js (App Router) + TypeScript | [ADR-002](ADR/ADR-002-nextjs-frontend.md) |
| Backend | FastAPI (Python 3.12+) | [ADR-003](ADR/ADR-003-fastapi-backend.md) |
| Primary database | PostgreSQL | [ADR-004](ADR/ADR-004-postgresql.md) |
| Search (MVP) | PostgreSQL full-text search + `pg_trgm`; upgrade path to Meilisearch | [ADR-005](ADR/ADR-005-search-architecture.md) |
| AI/RAG | Provider-abstracted LLM layer + `pgvector` for embeddings | [ADR-006](ADR/ADR-006-ai-rag-architecture.md) |
| Eligibility | Deterministic rule engine, DB-defined rules, no LLM in the decision path | [ADR-007](ADR/ADR-007-eligibility-engine.md) |
| Source/verification | First-class `sources`/`source_versions`/`verification_records` model | [ADR-008](ADR/ADR-008-source-verification-architecture.md) |
| Auth | JWT (access + refresh), RBAC roles, OAuth as secondary login | [ADR-009](ADR/ADR-009-authentication-strategy.md) |
| Deployment | Containerized; managed platforms, no Kubernetes | [ADR-010](ADR/ADR-010-deployment-architecture.md) |

## 3. State-Agnostic Design Principle

Andhra Pradesh and Telangana are the **initial data scope**, not a
structural assumption. Concretely:

- `states`, `districts`, `constituencies` are database rows with a
  `status` (`active` / `planned`), not enum values or code branches.
- No backend module, API route, or frontend component may hardcode a state
  name, code, or ID. Configuration (e.g., "which states are publicly
  launched") lives in data/config, not source code.
- Domain content (jobs, schemes, etc.) is always scoped by a foreign key to
  `states`/`districts`, so expansion to a new state is a data-loading
  exercise, not a schema or API change.

## 4. Source-of-Truth Doctrine (Summary)

Full detail in [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md). The non-negotiable
hierarchy:

```
OFFICIAL / AUTHORITATIVE SOURCE
        ↓
VERIFIED STRUCTURED DATA  (CivicLens database, with provenance)
        ↓
CIVICLENS APPLICATION      (API, search, UI)
        ↓
AI EXPLANATION             (synthesizes, never originates, facts)
```

Never: `internet → LLM → claimed fact`. This constrains every engine below:
the AI layer and the Eligibility Engine both consume structured data; they
do not produce it.

## 5. Product Engines → Architecture Mapping

| Engine | Primary module(s) | Data owned | Depends on |
|---|---|---|---|
| A. Civic Search | `search` (API), search index | Read-only projection of domain tables | Domain modules |
| B. Civic AI | `ai` (API) | None (retrieval-only) | Search, domain tables, `sources` |
| C. Eligibility Engine | `eligibility` (API) | `eligibility_rules`, `eligibility_conditions` | Domain tables |
| D. Civic Timeline | `deadlines` (part of domain modules) | `deadlines` | Jobs/exams/schemes |
| E. Tracking & Alerts | `tracking`, `notifications` | `tracking_items`, `notifications` | All domain modules |
| F. Document Intelligence | `documents` | `documents`, links from eligibility | Eligibility, domain modules |
| G. Life Event Navigator | Frontend composition layer | None (query composition) | Search, domain modules |
| H. Personal Civic Dashboard | `users`/`profiles` + read aggregation | `profiles`, `saved_items` | Tracking, domain modules |

Engines G and H are primarily **composition** layers (frontend + read-side
API aggregation) rather than new data owners — this keeps the data model
lean (see [DATABASE.md](DATABASE.md) §1 "why not a table per engine").

## 6. Repository Layout (Monorepo)

```
civiclens/
├── apps/
│   ├── web/              # Next.js + TypeScript frontend
│   └── api/               # FastAPI backend (modular monolith)
│       └── app/
│           ├── jobs/ exams/ schemes/ services/ scholarships/
│           ├── representatives/ elections/
│           ├── eligibility/ documents/
│           ├── search/ ai/ tracking/ notifications/
│           ├── sources/            # source & verification records
│           ├── users/ auth/
│           └── core/               # settings, db session, shared deps
├── packages/
│   ├── types/              # hand-written until OpenAPI-generated types
│   │                        # land (API.md §10); shared TS types
│   ├── validation/          # shared Zod validation schemas
│   ├── ui/                  # reserved — empty until a real cross-app
│   │                        # component-reuse need exists (FRONTEND.md §10)
│   └── config/              # shared tsconfig base
├── scripts/                  # repo-level dev scripts
├── services/
│   └── ingestion/            # data ingestion & change-detection (Phase 13+)
├── infra/                    # Docker, IaC, deployment config
├── docs/                      # this documentation
└── CLAUDE.md, README.md
```

Realized in Phase 1 with one adjustment from the original plan: the shared
types package is named `packages/types` (not `packages/shared-types`), and
`packages/validation` and a reserved, empty `packages/ui` were added — a
naming/scope refinement made directly by product ownership when Phase 1 was
kicked off, not a unilateral architecture change. No business logic,
domain schema, or real data exists yet.

## 7. Ingestion & Change Detection (Architecture Summary)

Detailed in [DATA_SOURCES.md](DATA_SOURCES.md). Pipeline shape:

```
SOURCE → FETCH → EXTRACT → NORMALIZE → VALIDATE → CHANGE DETECT
       → REVIEW (human) → PUBLISH → INDEX
```

Ingestion is a separate module/service from the public API — it writes to
staging tables and change records, never directly to published data,
without passing through review. See [ADR-008](ADR/ADR-008-source-verification-architecture.md).

## 8. AI/RAG Architecture (Architecture Summary)

Detailed in [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md). Shape:

```
USER QUERY → INTENT ANALYSIS → RETRIEVAL (DB + search + approved docs)
           → CONTEXT ASSEMBLY → LLM (provider-abstracted) → CITED RESPONSE
```

## 9. Eligibility Engine (Architecture Summary)

Detailed in [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md). Strict
separation of user attributes, rules, evaluation, and explanation — no LLM
in the decision path.

## 10. Internationalization Architecture

- Frontend: locale-aware routing (`/en/...`, `/te/...` or negotiated
  default), translation catalogs per locale, content fields modeled as
  translatable (see [DATABASE.md](DATABASE.md) §i18n fields).
- Launch locales: English, Telugu. Architecture supports adding locales via
  configuration/content, not code changes.
- Search must be locale-aware (see [SEARCH.md](SEARCH.md)).

## 11. Cross-Cutting Principles

1. **Provenance is mandatory.** Any table holding a public fact has a path
   to a `source` record.
2. **Determinism where it matters.** Eligibility and calculators are pure,
   testable functions over structured input — never LLM calls.
2. **Everything indexed is reviewed.** Ingested data passes human review
   before publish at v1 (see [DATA_SOURCES.md](DATA_SOURCES.md) §4).
3. **No engine hardcodes geography.** See §3.
4. **The AI layer is stateless with respect to facts.** It holds no
   authoritative data of its own.
5. **Extract, don't rewrite.** Modules are structured so any one of them
   can become an independent service later without a rewrite.

## 12. Related Documents

- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) — infra, environments, deployment topology
- [DATABASE.md](DATABASE.md), [API.md](API.md), [FRONTEND.md](FRONTEND.md)
- [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md), [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md), [DATA_SOURCES.md](DATA_SOURCES.md)
- [SECURITY.md](SECURITY.md), [PRIVACY.md](PRIVACY.md)
- [ADR/](ADR/README.md) for full decision rationale
