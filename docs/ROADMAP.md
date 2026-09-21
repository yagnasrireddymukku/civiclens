# CivicLens — Development Roadmap

Each phase lists objective, scope, dependencies, expected files/modules,
technical work, tests, documentation, acceptance criteria, risks, and
rollback considerations. Phases are sequential; a phase does not start
until the prior phase's acceptance criteria are met and, per
[CLAUDE.md](../CLAUDE.md), explicitly approved.

## Phase 0 — Product + Architecture + Governance
- **Objective**: Establish product vision, architecture, and engineering
  governance before any code.
- **Scope**: All documents in `docs/`, ADRs, `CLAUDE.md`, `README.md`.
- **Dependencies**: None.
- **Files/modules**: `docs/**`, `CLAUDE.md`, `README.md`.
- **Technical work**: None (documentation only).
- **Tests**: N/A.
- **Documentation**: This roadmap and all sibling documents.
- **Acceptance criteria**: All docs listed in this repository's governing
  prompt exist and are internally consistent; no application code exists.
- **Risks**: Documentation drifting from reality once implementation
  starts — mitigated by the "update documentation after architecture
  changes" rule in [CLAUDE.md](../CLAUDE.md).
- **Rollback**: Trivial (revert documentation commits); no runtime impact.

## Phase 1 — Monorepo Foundation
- **Objective**: Stand up the repository skeleton with no business logic.
- **Scope**: Directory structure, tooling configs, CI skeleton, linting.
- **Dependencies**: Phase 0 approval.
- **Files/modules**: `apps/web` (Next.js scaffold), `apps/api` (FastAPI
  scaffold), `packages/types`, `packages/validation`, `packages/ui`
  (reserved/empty), `packages/config`, `scripts/`, root
  `pnpm-workspace.yaml`, `apps/api/pyproject.toml`.
- **Technical work**: Scaffold apps, configure linting/formatting
  (ESLint/Prettier, ruff), configure CI to run lint + build + typecheck +
  test on PR. A minimal `GET /api/v1/health` endpoint and a frontend
  placeholder page that calls it prove the wiring end to end.
- **Tests**: Backend pytest suite (health, config, error-envelope) and a
  frontend Vitest test proving graceful degradation when the API is
  unreachable — not a "hello world" placeholder test.
- **Documentation**: [ARCHITECTURE.md](ARCHITECTURE.md) §6 updated to match
  the realized layout (`packages/types` instead of `packages/shared-types`,
  plus `packages/validation`/`packages/ui`).
- **Acceptance criteria**: `pnpm install`, frontend dev server, and backend
  dev server all run locally; CI green.
- **Risks**: Tooling version mismatches across OSes — mitigated by pinning
  versions and documenting setup in `README.md`.
- **Rollback**: Revert scaffold commits; no data/runtime dependents yet.

## Phase 2 — Backend Foundation
- **Objective**: FastAPI app skeleton with core cross-cutting concerns.
- **Scope**: Settings/config, DB session management, health checks,
  logging, error handling, module boundary structure (no domain logic).
- **Dependencies**: Phase 1.
- **Files/modules**: `apps/api/app/core/*`, `apps/api/app/main.py`.
- **Technical work**: App factory, environment-based settings, structured
  logging setup, `/health` endpoint, module router registration pattern.
- **Tests**: Unit tests for settings loading; integration test hitting
  `/health`.
- **Documentation**: [API.md](API.md) conventions section finalized against
  the real app structure.
- **Acceptance criteria**: API boots against a local Postgres instance with
  no domain tables yet; health check passes in CI.
- **Risks**: Over-scaffolding module boundaries before real domains exist —
  mitigated by keeping module folders empty/minimal until Phase 6+.
- **Rollback**: Revert; no persisted data yet.

## Phase 3 — Database + Data Model
- **Objective**: Implement the core schema from [DATABASE.md](DATABASE.md).
- **Scope**: Alembic migrations for geography, institutions, provenance,
  users/profiles tables. Domain-specific tables (jobs, schemes, etc.) are
  added incrementally in their own phases (6–9), not all at once here.
- **Dependencies**: Phase 2.
- **Files/modules**: `apps/api/app/core/models`, `apps/api/alembic/`.
- **Technical work**: SQLAlchemy models + Alembic migrations for
  `states`, `districts`, `constituencies`, `organizations`, `departments`,
  `sources`, `source_versions`, `verification_records`, `change_records`,
  `users`, `profiles`.
- **Tests**: Migration up/down tests; model constraint tests (uniqueness,
  FK integrity).
- **Documentation**: [DATABASE.md](DATABASE.md) updated with any deviations
  discovered during implementation.
- **Acceptance criteria**: Migrations apply cleanly on a fresh DB and
  reverse cleanly; no seed data beyond clearly-fictional test fixtures.
- **Risks**: Schema churn once domain tables arrive — mitigated by
  reviewing [DATABASE.md](DATABASE.md) relationships before writing
  migrations, not after.
- **Rollback**: Alembic downgrade path required for every migration
  ([CLAUDE.md](../CLAUDE.md): keep migrations reversible where practical).

## Phase 4 — Frontend + Design System
- **Objective**: Implement the design system primitives and app shell.
- **Scope**: Design tokens, component library base, layout, i18n scaffold
  (English/Telugu), no real content pages yet.
- **Dependencies**: Phase 1 (can run in parallel with Phases 2–3).
- **Files/modules**: `apps/web/app/`, `apps/web/components/ui/`,
  `apps/web/styles/`, `apps/web/i18n/`.
- **Technical work**: Implement tokens/components per
  [FRONTEND.md](FRONTEND.md) design-system spec; locale routing scaffold.
- **Tests**: Component unit tests (rendering, accessibility roles);
  Storybook or equivalent visual reference (only if justified — avoid
  unnecessary tooling per [CLAUDE.md](../CLAUDE.md)).
- **Documentation**: [FRONTEND.md](FRONTEND.md) finalized with real
  component inventory.
- **Acceptance criteria**: App shell renders in English and Telugu locale
  routes with placeholder content; base accessibility checks pass.
- **Risks**: Design system built ahead of real content needs, causing
  rework — mitigated by validating tokens/components against Phase 6's
  actual job-listing page before finalizing.
- **Rollback**: Revert; no backend dependency.

## Phase 5 — Search Infrastructure
- **Objective**: Stand up Postgres-based search per
  [SEARCH.md](SEARCH.md) / [ADR-005](ADR/ADR-005-search-architecture.md).
- **Dependencies**: Phase 3 (needs at least one domain table to index —
  can use Phase 6 tables, so may run just after Phase 6 begins).
- **Files/modules**: `apps/api/app/search/`.
- **Technical work**: `tsvector` columns/indexes, `pg_trgm` indexes,
  search query API, autocomplete endpoint.
- **Tests**: Search relevance tests against fixture data; typo-tolerance
  test cases.
- **Documentation**: [SEARCH.md](SEARCH.md) updated with real query
  patterns and index definitions.
- **Acceptance criteria**: Search endpoint returns correct, ranked results
  for fixture data including a deliberately misspelled query.
- **Risks**: Postgres FTS Telugu limitations (see
  [ADR-005](ADR/ADR-005-search-architecture.md)) — tracked as a known
  limitation, not blocking.
- **Rollback**: Search is a read-side projection; disabling it does not
  affect source-of-truth data.

## Phase 6 — Government Jobs
- **Objective**: First real domain: jobs, notifications, exams, deadlines.
- **Dependencies**: Phases 2–5.
- **Files/modules**: `apps/api/app/jobs/`, `apps/api/app/exams/`,
  `apps/web/app/jobs/`.
- **Technical work**: Domain tables + migrations, CRUD/read API per
  [API.md](API.md), job listing/detail pages, source/verification display.
- **Tests**: API contract tests, provenance-field-required tests (a job
  cannot be created without a `source_id`), frontend rendering tests.
- **Documentation**: [DATABASE.md](DATABASE.md), [API.md](API.md) updated
  with realized job/exam schema and endpoints.
- **Acceptance criteria**: A manually-entered, clearly-marked test job
  notification (fictional) renders end-to-end with source/verification
  status visible; no real government data entered yet (that begins only
  once [DATA_SOURCES.md](DATA_SOURCES.md) ingestion tooling and editorial
  review exist, Phase 13).
- **Risks**: Temptation to seed "realistic-looking" data before ingestion
  tooling exists — explicitly prohibited
  ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §7).
- **Rollback**: Domain tables are additive; feature-flag the `/jobs` route
  if rollback needed.

## Phase 7 — Government Services
- **Objective**: Services domain (documents/certificates, service pages).
- **Dependencies**: Phase 6 pattern established.
- **Files/modules**: `apps/api/app/services/`, `apps/api/app/documents/`,
  `apps/web/app/services/`.
- **Technical work**: Services + documents schema, API, pages, document
  checklist linkage (Document Intelligence engine, read-only checklist
  form at this phase).
- **Tests**: As Phase 6, plus document-checklist correctness tests.
- **Documentation**: [DATABASE.md](DATABASE.md), [API.md](API.md) updates.
- **Acceptance criteria**: Fictional test service renders with its document
  checklist and source; no real data yet.
- **Risks**: Document taxonomy sprawl — mitigated by starting with the
  documents actually referenced by real services once ingestion begins.
- **Rollback**: Additive; feature-flaggable.

## Phase 8 — Schemes + Scholarships
- **Objective**: Schemes and scholarships domains.
- **Dependencies**: Phase 6–7 patterns.
- **Files/modules**: `apps/api/app/schemes/`, `apps/api/app/scholarships/`,
  corresponding frontend routes.
- **Technical work**: Schema, API, pages, eligibility linkage stub (full
  engine arrives Phase 10 — for now, schemes just reference
  `eligibility_rules` rows without an evaluation UI).
- **Tests**: As prior domain phases.
- **Documentation**: Updates to [DATABASE.md](DATABASE.md), [API.md](API.md).
- **Acceptance criteria**: Fictional test scheme/scholarship renders with
  full provenance.
- **Risks**: None beyond prior domain phases.
- **Rollback**: Additive; feature-flaggable.

## Phase 9 — Public Representatives + Elections
- **Objective**: Representatives/elections domains, politically-neutral by
  construction.
- **Dependencies**: Phase 3 (constituencies).
- **Files/modules**: `apps/api/app/representatives/`,
  `apps/api/app/elections/`, corresponding frontend routes.
- **Technical work**: Schema, API, pages — no ranking/scoring fields or UI
  per [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §5.
- **Tests**: Neutrality checks (no comparative/ranking language in
  templates); provenance tests.
- **Documentation**: Updates to [DATABASE.md](DATABASE.md), [API.md](API.md);
  explicit neutrality review noted in PR description.
- **Acceptance criteria**: Fictional test representative/election renders
  with dates and source only — no score/rank UI element exists in the
  codebase.
- **Risks**: Perceived political bias in copy/UI — mitigated by an
  explicit neutrality review step in this phase's PR checklist.
- **Rollback**: Additive; feature-flaggable.

## Phase 10 — Eligibility Engine
- **Objective**: Implement the deterministic eligibility engine per
  [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) / [ADR-007](ADR/ADR-007-eligibility-engine.md).
- **Dependencies**: Phases 6–8 (entities to attach rules to).
- **Files/modules**: `apps/api/app/eligibility/`, frontend eligibility
  check UI.
- **Technical work**: `eligibility_rules`/`conditions` migrations,
  evaluation function, evaluation-trace API, frontend result rendering.
- **Tests**: Full deterministic unit-test matrix (every operator ×
  PASS/FAIL/UNKNOWN) — mandatory, see
  [TESTING.md](TESTING.md) §eligibility.
- **Documentation**: [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) updated
  with the finalized attribute enum.
- **Acceptance criteria**: 100% branch coverage on the evaluation function;
  a fictional rule set evaluates correctly against fictional profiles
  including an `INCOMPLETE` case.
- **Risks**: Attribute enum growing unmanaged — mitigated by requiring a
  documented product need (§2 of the eligibility doc) per new attribute.
- **Rollback**: Evaluation is a pure function with no side effects; safe to
  disable the check UI without data loss.

## Phase 11 — Civic AI + RAG
- **Objective**: Implement the AI pipeline per
  [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) / [ADR-006](ADR/ADR-006-ai-rag-architecture.md).
- **Dependencies**: Phases 5 (search), 6–9 (retrievable content), 10
  (eligibility explanation source).
- **Files/modules**: `apps/api/app/ai/`, `embeddings` table/migration,
  provider-abstraction interface, frontend Civic AI chat UI.
- **Technical work**: Intent parsing, retrieval, context assembly, provider
  interface + one concrete provider implementation, citation-carrying
  response contract, groundedness evaluation.
- **Tests**: Groundedness/citation-accuracy/refusal-correctness evaluation
  suite ([TESTING.md](TESTING.md) §AI evaluation); prompt-injection test
  cases using fixture "malicious" documents.
- **Documentation**: [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) updated with
  finalized prompt/response contract.
- **Acceptance criteria**: AI cannot answer a question outside its grounded
  context without an explicit "I don't know" response in the eval suite;
  every answer in the eval suite carries valid citations.
- **Risks**: Hallucination risk is the single largest product-trust risk in
  this phase — mitigated by shipping behind a flag until eval suite passes
  a defined accuracy bar, TBD with product owner.
- **Rollback**: AI feature is additive and can be feature-flagged off
  without affecting any other engine (per [ARCHITECTURE.md](ARCHITECTURE.md)
  §4, AI holds no authoritative data of its own).

## Phase 12 — Tracking + Notifications
- **Objective**: User tracking subscriptions and change notifications.
- **Dependencies**: Phase 6–9 (trackable entities), Phase 3 (users).
- **Files/modules**: `apps/api/app/tracking/`,
  `apps/api/app/notifications/`.
- **Technical work**: `tracking_items`/`notifications` schema (already
  planned in Phase 3, implemented here), subscription API, in-app +
  email notification delivery, dashboard integration.
- **Tests**: Notification-trigger tests (a `change_record` on a tracked
  entity produces exactly one notification).
- **Documentation**: [DATABASE.md](DATABASE.md) confirmed against
  implementation.
- **Acceptance criteria**: Tracking a fictional test entity and simulating
  a change record produces a visible in-app notification.
- **Risks**: Notification spam from noisy change detection — mitigated by
  only notifying on changes that pass human review (Phase 13), consistent
  with [DATA_SOURCES.md](DATA_SOURCES.md) §4.
- **Rollback**: Additive; feature-flaggable.

## Phase 13 — Admin Intelligence Center
- **Objective**: Ingestion pipeline + human review tooling per
  [DATA_SOURCES.md](DATA_SOURCES.md).
- **Dependencies**: Phases 3, 6–9 (entities to ingest into), Phase 12
  (notification trigger on approved change).
- **Files/modules**: `services/ingestion/`, `apps/api/app/admin/`
  (review queue endpoints), `apps/web/app/admin/`.
- **Technical work**: Source onboarding tooling (per-source legal
  checklist record), fetch/extract/normalize/validate pipeline stages,
  change-detection diffing, review queue UI, publish/index triggers.
- **Tests**: Pipeline stage unit tests; end-to-end test of a fictional
  source producing a reviewable change record; permission tests (only
  `editor`/`admin` can approve).
- **Documentation**: [DATA_SOURCES.md](DATA_SOURCES.md) updated with the
  realized pipeline; first real source onboarding checklist recorded.
- **Acceptance criteria**: A test source's detected change appears in the
  review queue and only becomes live data after explicit approval; this is
  the gate before any real government data enters the system.
- **Risks**: This phase carries the highest legal/compliance risk (§2 of
  [DATA_SOURCES.md](DATA_SOURCES.md)) — mitigated by requiring a completed
  per-source legal checklist before enabling fetch for that source.
- **Rollback**: Ingestion writes only to staging/change tables before
  approval — rollback of a bad publish is a `change_record` revert, not a
  destructive operation.

## Phase 14 — SEO + Content Infrastructure
- **Objective**: Full SEO implementation per [SEO.md](SEO.md).
- **Dependencies**: Phases 6–9 (indexable content).
- **Files/modules**: `apps/web/app/sitemap.ts`, `apps/web/app/robots.ts`,
  structured data components, breadcrumb components.
- **Technical work**: Sitemap generation, canonical URLs, JSON-LD
  structured data, OpenGraph metadata, breadcrumbs, internal linking.
- **Tests**: Structured-data validation tests; broken-link checks in CI.
- **Documentation**: [SEO.md](SEO.md) finalized against real URL patterns.
- **Acceptance criteria**: Sitemap validates; sample pages pass structured-
  data validation; no low-value/thin programmatic pages are generated.
- **Risks**: Programmatic page generation producing thin content —
  mitigated by the explicit "every indexed page must provide meaningful
  user value" rule in [SEO.md](SEO.md).
- **Rollback**: SEO metadata is additive; safe to revert individual
  templates.

## Phase 15 — Security + Privacy Hardening
- **Objective**: Formal security/privacy review and hardening pass across
  everything built so far.
- **Dependencies**: All prior phases.
- **Files/modules**: Cross-cutting — auth, input validation, rate limiting,
  secrets management, privacy controls (export/delete).
- **Technical work**: Penetration-test-style review against
  [SECURITY.md](SECURITY.md) checklist; implement account deletion/export
  per [PRIVACY.md](PRIVACY.md); rate limiting on public and AI endpoints.
- **Tests**: Security test suite (injection, auth-bypass, rate-limit
  tests); privacy-flow tests (delete removes/anonymizes data correctly).
- **Documentation**: [SECURITY.md](SECURITY.md), [PRIVACY.md](PRIVACY.md)
  updated with any findings and remediations.
- **Acceptance criteria**: No critical/high findings open; account
  deletion/export flows verified end-to-end.
- **Risks**: Findings requiring architectural change late — mitigated by
  security being a running concern from Phase 2 onward (see
  [SECURITY.md](SECURITY.md)), not deferred entirely to this phase.
- **Rollback**: Security fixes are not rolled back; any that break
  functionality are fixed forward.

## Phase 16 — Performance + Production Readiness
- **Objective**: Load/performance validation against
  [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) NFRs.
- **Dependencies**: All prior phases.
- **Files/modules**: Cross-cutting; caching layers, query optimization,
  CDN configuration.
- **Technical work**: Load testing, query plan review on hot paths (search,
  job listing), caching strategy for read-heavy public pages.
- **Tests**: Load/performance test suite with defined thresholds
  ([TESTING.md](TESTING.md) §performance).
- **Documentation**: [OBSERVABILITY.md](OBSERVABILITY.md) dashboards
  reflect production-readiness metrics.
- **Acceptance criteria**: Defined latency/throughput targets met under
  simulated launch-scale load.
- **Risks**: Untested scaling assumptions — mitigated by load testing
  against realistic (not just fixture-sized) synthetic data volumes.
- **Rollback**: Performance changes are typically additive (caching,
  indexes); revertible individually.

## Phase 17 — Deployment + Monitoring
- **Objective**: Production deployment per
  [DEPLOYMENT.md](DEPLOYMENT.md) / [ADR-010](ADR/ADR-010-deployment-architecture.md).
- **Dependencies**: Phases 15–16.
- **Files/modules**: `infra/`, CI/CD pipeline definitions.
- **Technical work**: Provision production environment, configure secrets
  management, set up monitoring/alerting per
  [OBSERVABILITY.md](OBSERVABILITY.md), configure backups.
- **Tests**: Deployment smoke tests; rollback drill.
- **Documentation**: [DEPLOYMENT.md](DEPLOYMENT.md) finalized with actual
  environment topology.
- **Acceptance criteria**: Successful production deploy with monitoring
  live and a tested rollback procedure.
- **Risks**: First production deploy always carries unknowns — mitigated
  by a staging environment mirroring production and a rehearsed rollback.
- **Rollback**: Documented redeploy-previous-image procedure; database
  migrations for this phase are infra-only (no schema changes expected).

## Phase 18 — Post-launch Expansion
- **Objective**: Expand geography/domains/languages based on real usage.
- **Dependencies**: Successful Phase 17 launch with real users.
- **Files/modules**: TBD based on prioritized expansion (new state data,
  additional domains, additional languages).
- **Technical work**: Data-only for new-state expansion (per
  [ARCHITECTURE.md](ARCHITECTURE.md) §3, state-agnostic design); new
  language packs; monetization feature evaluation
  ([MONETIZATION.md](MONETIZATION.md)).
- **Tests**: Regression suite must stay green; new-state data passes the
  same provenance/review gates as launch data.
- **Documentation**: All docs updated to reflect expanded scope.
- **Acceptance criteria**: Defined per specific expansion initiative at the
  time — not fixed here.
- **Risks**: Scope creep diluting quality — mitigated by the "quality over
  coverage" principle in [PRODUCT.md](PRODUCT.md) §7.
- **Rollback**: New-state/domain data can be unpublished without affecting
  existing launched data (state-scoped foreign keys).
