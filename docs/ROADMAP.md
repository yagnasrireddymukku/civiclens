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
- **Scope**: Alembic migrations for geography, provenance, users/profiles
  tables. Institutions (organizations/departments) and all
  domain-specific tables (jobs, schemes, etc.) are added incrementally in
  their own phases (6–9), not here — a scope narrowing from this entry's
  original wording, disclosed in [DATABASE.md](DATABASE.md) §7.
- **Dependencies**: Phase 2 (folded into the start of this phase — the
  backend foundation it called for was substantially established during
  Phase 1).
- **Files/modules**: `apps/api/app/core/db/` (engine, session, declarative
  base, model registry), `apps/api/app/geography/`, `apps/api/app/sources/`,
  `apps/api/app/users/` (each with `models.py` + `enums.py`),
  `apps/api/alembic/`. Per-module rather than a single `app/core/models`
  (this entry's original sketch) to match
  [ARCHITECTURE.md](ARCHITECTURE.md) §6's modular-monolith module list —
  see [DATABASE.md](DATABASE.md) §7 for the full reconciliation.
- **Technical work**: SQLAlchemy 2.0 models + one Alembic migration for
  `states`, `districts`, `constituencies` (with slugs — see
  [DATABASE.md](DATABASE.md) §2.1), `sources`, `source_versions`,
  `verification_records`, `change_records`, `users`, `profiles`;
  lazy engine/session with a request-scoped `get_db` FastAPI dependency
  (commit-on-success/rollback-on-exception); a `GET /api/v1/health/ready`
  endpoint proving the DB foundation end to end.
- **Tests**: Migration up/down/up-again test (catches an Alembic
  autogenerate gap — native Postgres enum types aren't dropped by
  `op.drop_table`, fixed explicitly); model constraint tests (uniqueness,
  FK integrity, cascade/restrict delete behavior, native-enum rejection of
  invalid values); `get_db` commit/rollback transaction tests; a
  regression test proving the app still boots with no reachable database.
  All run against a real PostgreSQL instance (via `pgserver`, since this
  environment has no Docker/WSL2 — see [TESTING.md](TESTING.md)), never
  mocks.
- **Documentation**: [DATABASE.md](DATABASE.md) updated with the realized
  schema, deferred sections, and module-layout reconciliation.
- **Acceptance criteria**: Migrations apply cleanly on a fresh DB and
  reverse cleanly (verified, including a re-upgrade after downgrade); no
  seed data beyond clearly-fictional test fixtures.
- **Risks**: Schema churn once domain tables arrive — mitigated by
  reviewing [DATABASE.md](DATABASE.md) relationships before writing
  migrations, not after. A connect/statement timeout was added to the
  engine after manual testing showed an unreachable database could hang
  a request indefinitely rather than failing fast.
- **Rollback**: Alembic downgrade path required for every migration
  ([CLAUDE.md](../CLAUDE.md): keep migrations reversible where practical) —
  exercised by the migration test, not just asserted.

## Phase 4 — Frontend + Design System
- **Objective**: Implement the design system primitives and app shell.
- **Scope**: Design tokens, component library base, layout, i18n
  foundation (English/Telugu), no real content pages.
- **Dependencies**: Phase 1 (ran independently of Phases 2–3).
- **Files/modules**: `apps/web/app/globals.css` (tokens),
  `apps/web/components/{primitives,feedback,navigation,layout,civic}/`,
  `apps/web/components/icons.tsx`, `apps/web/i18n/`, `apps/web/proxy.ts`,
  `apps/web/messages/{en,te}.json`, `apps/web/app/[locale]/` (restructured
  from Phase 1's flat `app/`), `apps/web/lib/seo.ts`. No
  `apps/web/components/ui/` or `apps/web/styles/` — folder names refined
  during implementation; see [FRONTEND.md](FRONTEND.md) §4.
- **Technical work**: CSS custom-property design tokens (no Tailwind);
  ~20 primitives/feedback/navigation components (native `<dialog>`,
  `<details>`, `<select>` used instead of hand-built equivalents where
  possible); 9 CivicLens-specific components (`SourceBadge`,
  `VerificationStatus`, `EligibilityStatus`, `DeadlineBadge`,
  `LastVerified`, `OfficialSourceCard`, `InformationCard`,
  `SearchResultCard`, `SearchBar`); `AppShell`/`TopNav`/`Footer` with a
  "coming soon" pattern for unbuilt nav sections (no dead links);
  `next-intl`-based locale routing (`/en`, `/te`) with a working
  language switcher; a development-only design-system showcase page,
  blocked in production at the proxy layer.
- **Tests**: Component tests for accessibility-critical behavior (`Tabs`
  keyboard/ARIA, `Dialog` open/close/labeling, `VerificationStatus`
  never-color-alone), a `LanguageSwitcher` test proving the i18n
  foundation actually switches locale, plus the existing `Button`/home-page
  tests updated for the new route structure. No Storybook — not justified
  at this scale ([CLAUDE.md](../CLAUDE.md) rule 13).
- **Documentation**: [FRONTEND.md](FRONTEND.md) updated with the realized
  component inventory, token values, and i18n implementation;
  [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) NFR-ACC1 raised from
  WCAG 2.1 AA to 2.2 AA per this phase's instruction (a superset, not a
  conflicting bar).
- **Acceptance criteria**: App shell renders in English and Telugu locale
  routes with placeholder content; lint/typecheck/format/build/test all
  pass for both `apps/web` and (regression-checked, unchanged)
  `apps/api`; the showcase page 404s in a production build and renders in
  development.
- **Risks**: Design system built ahead of real content needs, causing
  rework — mitigated by validating tokens/components against Phase 6's
  actual job-listing page before finalizing. One real bug found and fixed
  during implementation: `notFound()` called from inside the showcase
  page component did not reliably produce an HTTP 404 in a production
  build (observed directly, not assumed) — the authoritative guard is
  now `apps/web/proxy.ts`, with the in-page `notFound()` kept only as
  defense in depth.
- **Rollback**: Revert; no backend dependency (confirmed — `apps/api`'s
  Phase 3 test suite was re-run unchanged and stayed green throughout).

## Phase 5 — Search Infrastructure
- **Objective**: Stand up Postgres-based search per
  [SEARCH.md](SEARCH.md) / [ADR-005](ADR/ADR-005-search-architecture.md).
- **Dependencies**: Phase 3 only, not Phase 6 — this document originally
  assumed indexing needed a real domain table to point at, but the
  "clean search abstraction" requirement led to a generic, polymorphic
  `search_documents` projection (`entity_type`/`entity_id`, no FK to any
  domain table, matching `sources`'s existing pattern) instead of
  per-domain generated columns, so Phase 5 ran entirely against synthetic
  fixtures with no Phase 6 dependency. A disclosed scope correction, not
  an oversight (see [SEARCH.md](SEARCH.md) §3, [DATABASE.md](DATABASE.md)
  §8).
- **Files/modules**: `apps/api/app/search/` (models, schemas, service,
  enums, fixtures), `apps/api/app/api/v1/search.py`,
  `apps/api/scripts/seed_search_fixtures.py`,
  `apps/web/app/[locale]/search/`, `apps/web/lib/search.ts`; shared
  response types added to `packages/types`/`packages/validation`.
- **Technical work**: `search_documents` table with a generated
  `search_vector`, weighted A/B/C across title/summary/body
  (`app/search/models.py`); exact `websearch_to_tsquery` matching with a
  `word_similarity`-based `pg_trgm` fallback for typos (`app/search/
  service.py`); filters (entity_type/state/district/category/status/date
  range), pagination, and a `sort=last_verified` override; `GET
  /api/v1/search` (`app/api/v1/search.py`); a locale-aware, shareable-URL
  search page composing Phase 4's `SearchBar`/`SearchResultCard` with a
  persistent "development data" notice. Autocomplete was scoped out
  (§4 of [SEARCH.md](SEARCH.md)) — not needed for this phase's
  acceptance criteria.
- **Tests**: 14 deterministic backend service tests plus a migration
  up/down/up-again test (`apps/api/tests/test_search/`); 10 frontend
  tests covering the results/empty/error/fuzzy-fallback states and the
  query/pagination navigation (`apps/web/app/[locale]/search/`).
- **Documentation**: [SEARCH.md](SEARCH.md), [DATABASE.md](DATABASE.md),
  [API.md](API.md), and [TESTING.md](TESTING.md) updated with the
  realized schema, query flow, and test infrastructure.
- **Acceptance criteria**: Search endpoint returns correct, ranked results
  for fixture data including a deliberately misspelled query
  ("recuritment" → "Recruitment") — verified directly against a live
  backend, not just unit tests.
- **Risks**: Postgres FTS Telugu limitations (see
  [ADR-005](ADR/ADR-005-search-architecture.md)) — tracked as a known,
  documented limitation, not blocking. One real regression found and
  fixed during implementation, not assumed away: the migration's own
  `CREATE EXTENSION pg_trgm` broke every existing Phase 1/3 backend test,
  since those ran against `pgserver` (a pip-installed embedded Postgres),
  whose Windows build doesn't bundle `pg_trgm`. Fixed by moving every
  backend test onto a shared full-PostgreSQL test fixture (a `postgres:16`
  CI service container, or a local full-Postgres binary distribution) and
  removing the now-unnecessary `pgserver` dependency entirely — see
  [TESTING.md](TESTING.md) §3.
- **Rollback**: Search is a read-side projection; disabling it does not
  affect source-of-truth data.

## Phase 6 — Government Jobs
- **Objective**: First real domain: organizations, departments, jobs, job
  notifications, and vacancies (initial geographic scope: Andhra Pradesh
  + Telangana, architecture state-agnostic throughout).
- **Dependencies**: Phases 2–5.
- **Files/modules**: `apps/api/app/jobs/` (models, enums, schemas,
  service, fixtures), `apps/api/app/api/v1/jobs.py`,
  `apps/api/scripts/seed_job_fixtures.py`, `apps/web/app/[locale]/jobs/`
  (list + `[slug]` detail), `apps/web/lib/jobs.ts`. Exams were named in
  this document's original Phase 6 scope line but not in this phase's
  actual kickoff instructions — deferred to whichever later phase
  introduces them, a disclosed scope correction, not an oversight.
- **Technical work**: `organizations`/`departments` treated as reference
  data like geography (no `source_id`); `jobs`/`job_notifications` each
  carry independent `source_id`+denormalized `verification_status` (the
  `search_documents` Phase 5 pattern); `job_vacancies` inherit their
  parent notification's provenance. `GET /api/v1/jobs` (filtered, paged)
  and `GET /api/v1/jobs/{slug}` (notifications+vacancies nested inline)
  per [API.md](API.md) §13. Jobs integrate with `search_documents` as
  `entity_type="job"` (`sync_job_search_index()`,
  [SEARCH.md](SEARCH.md) §14) — the first real domain module to call the
  Phase 5 search abstraction. Frontend list/detail pages reuse Phase 4's
  `InformationCard`/`SourceBadge`/`VerificationStatus`/`LastVerified`/
  `Breadcrumb` rather than introducing a bespoke `JobCard`; `JobPosting`
  + `BreadcrumbList` JSON-LD on the detail page (Phase 6 realized
  [SEO.md](SEO.md)'s Jobs pattern ahead of Phase 14's full rollout, since
  Jobs is the first phase with real page content to attach it to).
- **Tests**: 34 new backend tests (models/constraints, service-layer
  visibility rules and search-index sync, API contract, migration
  up/down/up-again, fixture loading) plus 14 new frontend tests (list,
  detail, and filter/pagination controls) — 86 backend / 40 frontend
  tests passing in total, including full Phase 0–5 regression.
- **Documentation**: [DATABASE.md](DATABASE.md) §9,
  [API.md](API.md) §13, [SEARCH.md](SEARCH.md) §14, and
  [SEO.md](SEO.md) §12 updated with the realized schema, endpoints,
  search integration, and Jobs-specific SEO implementation.
- **Acceptance criteria**: A single, clearly-marked synthetic test job
  (`TEST_CIVICLENS_JOB_001`) renders end-to-end — list page, detail page
  with nested notification/vacancies, source/verification status
  visible, findable via `/search` — verified directly against a live
  backend and frontend, not only via automated tests. No real government
  data entered (that begins only once [DATA_SOURCES.md](DATA_SOURCES.md)
  ingestion tooling and editorial review exist, Phase 13).
- **Risks**: Temptation to seed "realistic-looking" data before ingestion
  tooling exists — explicitly prohibited
  ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §7); avoided. One real
  regression found and fixed by hand: `app/search/fixtures.py` and
  `app/jobs/fixtures.py` each independently created their own
  "Testland"/`ZZ` fictional state, so seeding both into the same
  database collided on `states.code`'s uniqueness constraint — fixed by
  making both loaders get-or-create that shared canonical fixture state
  instead of blindly inserting it. Separately, a known, already-disclosed
  Next.js limitation from Phase 4 (`notFound()` not reliably producing a
  404 HTTP status under this project's `[locale]` routing) recurred for
  the dynamic job-slug case; mitigated with a `noindex, nofollow` robots
  tag rather than solved outright — see [SEO.md](SEO.md) §12.
- **Rollback**: Domain tables are additive; feature-flag the `/jobs`
  route if rollback needed.

## Phase 7 — Government Services
- **Objective**: Services domain (second real domain module, following
  Jobs' Phase 6 pattern exactly) — organizations/departments moved to a
  shared `app.institutions` module now that Services needs them too.
- **Dependencies**: Phase 6 pattern established.
- **Files/modules**: `apps/api/app/institutions/` (extracted from
  `app.jobs`), `apps/api/app/services/` (models, enums, schemas,
  service, fixtures), `apps/api/app/api/v1/services.py`,
  `apps/api/scripts/seed_service_fixtures.py`,
  `apps/web/app/[locale]/services/` (list + `[slug]` detail),
  `apps/web/lib/services.ts`. A standalone `app/documents/` module was
  named in this document's original Phase 7 scope line but not built —
  the document-checklist requirement is satisfied by
  `service_required_documents`, a child table of `Service` itself
  (simpler than a separate module, and matches the actual kickoff
  instructions, which described document requirements as part of the
  Services domain rather than a standalone one); a general-purpose
  Document Intelligence capability remains future scope, undisturbed.
- **Technical work**: `services` carries the same denormalized
  provenance/visibility pattern as `jobs` (independent `source_id` +
  `verification_status`/`last_verified_at`, `publication_status` as the
  one hard visibility gate); `service_category` is a controlled enum
  (unlike `jobs.category`'s free text — this phase's explicit
  requirement) plus `service_requirements` (light eligibility-relevant
  structure: type + optional numeric range + prose, not the eligibility
  engine itself), `service_required_documents`, and
  `service_application_methods` as provenance-free child tables.
  `GET /api/v1/services` (filtered, paged) and
  `GET /api/v1/services/{slug}` (requirements/documents/methods nested
  inline) per [API.md](API.md) §14. Services is the *second* real
  domain to integrate with `search_documents`
  (`entity_type="service"`, [SEARCH.md](SEARCH.md) §15), proving the
  Phase 5 search abstraction generalizes rather than being Jobs-specific
  — verified with a live cross-domain query returning both a job and a
  service. Frontend list/detail pages reuse the same Phase 4 components
  Jobs' pages do, plus `GovernmentService` + `BreadcrumbList` JSON-LD
  (schema.org fit checked against real documented properties, not
  guessed — [SEO.md](SEO.md) §13).
- **Tests**: 36 new backend tests (models/constraints, service-layer
  visibility and search-index sync including cross-domain search, API
  contract, migration up/down/up-again, fixture loading) plus 15 new
  frontend tests (list, detail, and filter/pagination controls) — 122
  backend / 55 frontend tests passing in total, including full Phase
  0–6 regression.
- **Documentation**: [DATABASE.md](DATABASE.md) §10, [API.md](API.md)
  §14, [SEARCH.md](SEARCH.md) §15, [SEO.md](SEO.md) §13,
  [FRONTEND.md](FRONTEND.md) §12, and [ARCHITECTURE.md](ARCHITECTURE.md)
  updated with the realized schema, endpoints, search integration, SEO
  implementation, and the institutions-module extraction.
- **Acceptance criteria**: A single, clearly-marked synthetic test
  service (`test-civiclens-service-001`) renders end-to-end — list page,
  detail page with requirements/documents/application methods, source/
  verification status visible, findable via `/search` alongside the
  Phase 6 test job in the same query — verified directly against a live
  backend and frontend. No real government data entered.
- **Risks**: Document taxonomy sprawl — mitigated by keeping
  `service_required_documents` a simple name+description+mandatory
  list rather than a controlled taxonomy this phase would have to
  guess at; a real taxonomy is deferred until real services exist to
  derive one from (Phase 13). Two real problems found and fixed by
  hand: (1) `Organization`/`Department`'s relationships to `Job`/
  `Service` are resolved by name against SQLAlchemy's shared registry,
  which requires every model module to be imported first — a standalone
  script importing only `app.jobs.fixtures` crashed until every
  `scripts/seed_*.py` was fixed to import `app.core.db.model_registry`
  first (the running API server was never affected, since it already
  imports every domain together). (2) Extending Phase 6's shared-fixture-
  geography fix: `app/services/fixtures.py` and `app/jobs/fixtures.py`
  both reference the same fictional organization by name, so both were
  made to get-or-create it (`organizations.name` is globally unique) —
  the same class of bug Phase 6 already found and fixed for state.
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
