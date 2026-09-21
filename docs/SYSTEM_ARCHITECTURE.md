# CivicLens — System Architecture

This is the operational companion to [ARCHITECTURE.md](ARCHITECTURE.md).
That document defines architectural *style*, technology choices, and module
boundaries at a conceptual level. This document describes how those pieces
actually run: the runtime topology, request flows, environments, and the
isolation and caching mechanics that make the system operable in production.
Deployment mechanics (CI/CD, IaC, secrets, backups, rollback) live in
[DEPLOYMENT.md](DEPLOYMENT.md); this document stops at "what talks to what
and how," not "how it gets shipped."

**Nothing described here is built yet.** This is the target runtime shape
for the phases in [ROADMAP.md](ROADMAP.md); Phase 0 is documentation only.

## 1. Component Diagram (Target)

```
                         ┌─────────────────────────┐
                         │        Browser           │
                         │  (user, en/te locale)     │
                         └────────────┬─────────────┘
                                      │ HTTPS
                                      ▼
                  ┌───────────────────────────────────────┐
                  │     Next.js frontend (apps/web)         │
                  │  - SSR/ISR public pages (jobs, schemes, │
                  │    representatives, calculators)        │
                  │  - CSR authenticated dashboard           │
                  │  - Deployed on a frontend-native platform│
                  │    (e.g. Vercel) — ADR-002, ADR-010      │
                  └────────────────┬────────────────────────┘
                                   │ HTTPS (REST, OpenAPI contract)
                                   ▼
                  ┌───────────────────────────────────────────────┐
                  │      FastAPI backend (apps/api) — ONE service   │
                  │      modular monolith, ADR-003, ARCHITECTURE §1 │
                  │ ┌─────────────────────────────────────────────┐ │
                  │ │ jobs · exams · schemes · services            │ │
                  │ │ scholarships · representatives · elections   │ │
                  │ │ eligibility · documents · search · ai        │ │
                  │ │ tracking · notifications · users · auth       │ │
                  │ │ sources (ingestion-facing read/write boundary)│ │
                  │ └─────────────────────────────────────────────┘ │
                  │  In-process module calls only — no internal      │
                  │  network hops between modules (ARCHITECTURE §1)  │
                  └───────┬───────────────────────────────┬──────────┘
                          │ SQL (app role: read/write        │ HTTPS
                          │ published tables only)            │ (provider-abstracted,
                          ▼                                    │  AI_ARCHITECTURE §5)
       ┌───────────────────────────────────┐                  ▼
       │         PostgreSQL (single DB)      │        ┌──────────────────┐
       │  - domain tables (jobs, schemes...)  │        │ External LLM      │
       │  - sources / source_versions /       │        │ provider           │
       │    verification_records /            │        │ (Anthropic/OpenAI/ │
       │    change_records (ADR-008)           │        │  other; behind     │
       │  - eligibility_rules/conditions        │        │  LLMProvider       │
       │  - embeddings (pgvector, ADR-006)       │        │  interface)        │
       │  - tsvector + pg_trgm indexes            │        └──────────────────┘
       │    (ADR-005)                              │
       └───────┬───────────────────────────┬────────┘
               │ SQL (ingestion role:       │
               │ write staging/change       │
               │ tables only — §4)          │
               ▼                            │
   ┌─────────────────────────────┐          │
   │  Ingestion service            │◄────────┘ (reads published data
   │  (services/ingestion)          │            for change-detection diff)
   │  Admin Intelligence Center,     │
   │  DATA_SOURCES.md, Phase 13       │
   │  - fetch/extract/normalize/     │
   │    validate/change-detect        │
   │  - never writes published tables │
   │    directly (§4)                  │
   └──────────────────────────────────┘
               ▲
               │ HTTPS (admin-authenticated,
               │ editor/admin role only)
   ┌──────────────────────────────┐
   │  Admin review UI (apps/web      │
   │  /admin route, or a separate     │
   │  authenticated surface)           │
   └──────────────────────────────────┘
```

Two runtime deployables communicate over HTTPS (frontend ↔ backend); the
ingestion service is a third deployable unit *within the same monorepo*
(`services/ingestion`, [ARCHITECTURE.md](ARCHITECTURE.md) §6), sharing the
one PostgreSQL database but never the API process. This is still a modular
monolith, not microservices: there is one public-facing API, one database,
and no service mesh or broker between them (ADR-001, ADR-010, [CLAUDE.md](../CLAUDE.md)
rule 11).

## 2. Request Flow — Typical Page Load

Example: a user opens a job-listing detail page.

1. Browser requests `/en/jobs/<slug>` from the Next.js frontend.
2. Next.js renders the page server-side (SSR) or serves a previously
   generated static page (ISR — §6), calling the FastAPI backend's
   `/jobs/{id}` read endpoint if the cache is cold or expired.
3. FastAPI's `jobs` module handles the request: validates the path param
   (Pydantic), queries PostgreSQL for the job row plus its joined
   `source`/`verification_record` (ADR-008), and returns a typed JSON
   response ([API.md](API.md) §9 response contract).
4. PostgreSQL executes the query against the `jobs` table and its
   provenance joins; no AI or ingestion involvement in this path.
5. Next.js renders HTML with the job details, source attribution, and
   "last verified" date, and returns it to the browser. The rendered
   page (for public, non-personalized routes) is cached at the edge per
   the ISR policy for that route (§6).

No step in this flow touches the LLM or the ingestion service — a page
load is a pure structured-data read, consistent with the source-of-truth
doctrine ([ARCHITECTURE.md](ARCHITECTURE.md) §4): the AI layer is not in
the critical path for factual display.

## 3. Request Flow — Civic AI Query

Example: a user asks the Civic AI "Am I eligible for TSPSC Group 2 with a
B.Tech degree at age 24?"

1. Frontend (`ai` chat surface) sends the query, plus the user's
   authenticated context (profile attributes, if the user opted to include
   them), to `POST /ai/query` on the backend.
2. `ai` module: **intent/query analysis** parses the query into a structured
   intent object (domain = exams, entity = TSPSC Group 2, attributes =
   degree/age) — never sent to the LLM as free text at this stage
   ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §2).
3. **Retrieval**: structured queries against domain tables (exam, its
   `eligibility_rules`) combined with `pgvector` semantic search over the
   `embeddings` table for supporting context, restricted to `VERIFIED`
   (and flagged `NEEDS_REVIEW`) records only ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)
   §3).
4. If the query is an eligibility question, the `eligibility` module runs
   the deterministic rule evaluation ([ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md))
   — the verdict itself is never computed by the LLM.
5. **Context assembly**: retrieved facts, their citations, and (if
   applicable) the eligibility evaluation trace are assembled into a
   structured prompt that separates grounded context from instructions.
6. **LLM call**: the `ai` module calls the external LLM provider through the
   `LLMProvider` abstraction ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §5) —
   this is the only point in the entire system that makes an outbound call
   to a third-party AI vendor. The provider is swappable configuration, not
   a hardcoded dependency.
7. The LLM returns a synthesis, which the `ai` module wraps into the
   response contract (`answer`, `citations[]`, `grounding_status` —
   [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §6) and returns to the frontend.
8. Frontend renders the answer with visible citations and, if
   `grounding_status` is not fully grounded, an explicit "we couldn't
   verify this" UI state rather than the raw answer.

The LLM provider sits outside CivicLens's trust boundary: it receives only
the assembled, already-verified context for that single request, never a
standing connection or bulk data export, and never a source of facts in
its own right ([ARCHITECTURE.md](ARCHITECTURE.md) §4, §11.4).

## 4. Environments

| Environment | Purpose | Data | Sources | Feature flags |
|---|---|---|---|---|
| **Local / dev** | Individual development, via Docker Compose (API + Postgres; frontend runs natively for fast refresh) | Small fixture/seed dataset, clearly marked fictional per [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §7 | All external sources sandboxed/mocked — no live fetches against real government sites | All flags on by default, including unreleased/experimental ones |
| **Staging** | Pre-production verification, mirrors production topology | A realistic-volume but non-production dataset (may include a sanitized copy or an expanded fixture set) | Ingestion sources run in a sandboxed/dry-run mode by default (fetch + validate, but publish gated the same as production, or entirely disabled) — a source is only "live" here if explicitly enabled for a rehearsal | Flags mirror production plus any features pending a final go/no-go |
| **Production** | Real users, real published civic data | Full production dataset, subject to the same provenance/review rules everywhere else | Only sources that have passed the full onboarding checklist ([DATA_SOURCES.md](DATA_SOURCES.md) §2) are live | Flags reflect actual launch state; experimental features stay off until explicitly enabled |

All three environments run the **same container image** and the same
codebase — differences are environment variables, secrets, and data, never
a forked build ([ADR-010](ADR/ADR-010-deployment-architecture.md),
detailed promotion flow in [DEPLOYMENT.md](DEPLOYMENT.md) §1). This is what
makes staging a meaningful rehearsal of production rather than a
best-effort approximation.

## 5. Ingestion Isolation From the Public API

The ingestion service (`services/ingestion`) and the public API
(`apps/api`) are separate processes/deployables that share one PostgreSQL
instance under **different database roles**:

- **`app_api` role** (used by `apps/api`): read/write on published domain
  tables (jobs, schemes, etc.) and read/write on user-owned tables (users,
  tracking, notifications). No write access to raw ingestion staging
  tables.
- **`app_ingestion` role** (used by `services/ingestion`): write access to
  `source_versions`, staging/extraction tables, and `change_records` only.
  It has **no write access to published domain tables** — publishing a
  reviewed change is performed by an explicit reviewer-approved transaction
  ([DATA_SOURCES.md](DATA_SOURCES.md) §3–4), not by the ingestion process
  itself writing live data.
- Both roles can read published data (ingestion needs it for change-
  detection diffing against the current live value).

This split is enforced at the database-permission level, not only by
application convention, so a bug or compromise in the ingestion pipeline
cannot silently corrupt public-facing data. The admin review UI
(editor/admin roles only, [ADR-009](ADR/ADR-009-authentication-strategy.md))
is the only path from staging data to a live publish.

## 6. Caching Strategy (Overview)

- **Public, SEO-critical pages** (job/scheme/service/representative detail
  and listing pages, calculators): served via Next.js **Incremental Static
  Regeneration**. A page is statically generated, served from the edge, and
  revalidated on a time interval or on-demand trigger (e.g., when a
  `change_record` for that entity is approved and published). This is the
  primary lever for both performance and backend load reduction, per
  ADR-002's stated rationale.
- **Authenticated/dashboard pages**: not cached at the edge (personalized,
  session-dependent); rendered client-side or SSR per-request.
- **API responses**: no caching layer is specified at this phase beyond
  what PostgreSQL and connection pooling provide naturally. Backend-level
  response caching (e.g., short-TTL caching of expensive aggregate/search
  queries) is explicitly deferred.
- **Search and AI retrieval**: not cached at this phase; each query re-runs
  against PostgreSQL/pgvector. Caching hot queries is a candidate
  optimization, not a v1 requirement.

A full caching, CDN, and query-optimization pass — including cache-key
design, invalidation triggers wired to the ingestion publish step, and load
testing — is explicitly scoped to **[ROADMAP.md](ROADMAP.md) Phase 16
(Performance + Production Readiness)**, not this document. Nothing above
should be read as a performance guarantee; it is the shape the caching
strategy will be built into, not the strategy itself.

## 7. How This Topology Stays State-Agnostic

Per the state-agnostic design principle ([ARCHITECTURE.md](ARCHITECTURE.md)
§3), nothing in the runtime topology described above is specific to Andhra
Pradesh or Telangana:

- There is one frontend deployment, one backend deployment, and one
  database for **all** states the product serves — not a deployment per
  state.
- ISR cache keys and static-generation routes are parameterized by
  state/district/entity IDs from the database, not by a hardcoded list of
  AP/TS routes.
- The ingestion service's source allowlist is data (rows describing a
  source, its state scope, and its onboarding status), not a code branch
  per state — adding a third state's sources is a data-onboarding
  exercise ([DATA_SOURCES.md](DATA_SOURCES.md) §1–2), not an infrastructure
  change.
- Environment configuration (§4) varies by deploy environment
  (local/staging/production), never by geography — there is no "AP
  environment" or "Telangana environment."

Expanding to a new state changes what rows exist in PostgreSQL and which
sources are onboarded; it does not change how many services run, how they
talk to each other, or how they're deployed.

## 8. Explicitly Not Built Yet

- No container images, Compose files, or deployment manifests exist.
- No database is provisioned; the schema above is the target, detailed in
  [DATABASE.md](DATABASE.md).
- No LLM provider is integrated or configured.
- No ingestion pipeline, admin review UI, or database roles are created.
- No caching, CDN, or load-testing infrastructure exists (Phase 16).

## 9. Related Documents

- [ARCHITECTURE.md](ARCHITECTURE.md) — architectural style, stack, module
  boundaries (conceptual level this document expands on)
- [DEPLOYMENT.md](DEPLOYMENT.md) — CI/CD, IaC, secrets, backups, rollback
- [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md), [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md)
- [DATA_SOURCES.md](DATA_SOURCES.md), [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [DATABASE.md](DATABASE.md), [API.md](API.md)
- [ADR/](ADR/README.md) for decision rationale, especially ADR-001, ADR-005,
  ADR-006, ADR-008, ADR-010
