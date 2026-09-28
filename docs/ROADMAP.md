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

## Phase 8 — Government Schemes
- **Objective**: Schemes domain (third real domain module, following
  Jobs'/Services' Phase 6/7 pattern exactly) — a benefit/support program a
  citizen may be eligible for, conceptually distinct from a Service
  (something a citizen requests/accesses). Scholarships were **deferred**
  from this document's original combined "Schemes + Scholarships" scope
  line, per the actual Phase 8 kickoff's narrower instruction — a
  scholarship is close enough to a scheme's shape that folding it in
  without a real example to derive requirements from risked guessing at a
  distinction that doesn't hold up; it remains future scope.
- **Dependencies**: Phase 6–7 pattern established.
- **Files/modules**: `apps/api/app/requirements/` (extracted from
  `app.services.enums` — `RequirementType`/`ApplicationChannelType`
  vocabulary only, no tables), `apps/api/app/schemes/` (models, enums,
  schemas, service, fixtures), `apps/api/app/api/v1/schemes.py`,
  `apps/api/scripts/seed_scheme_fixtures.py`,
  `apps/web/app/[locale]/schemes/` (list + `[slug]` detail),
  `apps/web/lib/schemes.ts`. No `eligibility_rules` table or evaluation
  stub was built — this document's original Phase 8 scope line named one,
  but the actual kickoff explicitly prohibited it: the full Eligibility
  Engine (predicate model, evaluation logic, ELIGIBLE/NOT_ELIGIBLE/
  INCOMPLETE verdicts) remains entirely Phase 10 scope. What Phase 8
  builds instead is the *structured ground* that engine will read from
  later — `scheme_requirements` (type + optional numeric range + prose,
  reusing the same shape `service_requirements` already established).
- **Technical work**: `schemes` carries the same denormalized provenance/
  visibility pattern as `jobs`/`services` (independent `source_id` +
  `verification_status`/`last_verified_at`, `publication_status` as the
  one hard visibility gate, its own `scheme_publication_status` enum
  type — not shared with Jobs'/Services', for the same domain-scoping
  reason those two aren't shared with each other); `scheme_category` is a
  16-value controlled enum (this phase's explicit taxonomy requirement).
  `SchemeBenefit` is new to this domain — structured benefit information
  (a `benefit_type` enum plus prose plus an optional `amount_summary`
  string, never a fabricated figure). `RequirementType`/
  `ApplicationChannelType` were extracted from `app.services.enums` into
  a new, neutral `app.requirements.enums` module once Schemes needed the
  same two vocabularies — a pure Python/enum-level move (`alembic check`
  showed zero schema diff), deliberately **not** extending to a shared
  table: `SchemeRequirement`/`SchemeRequiredDocument`/
  `SchemeApplicationMethod` remain their own tables, mirroring
  `ServiceRequirement`/`RequiredDocument`/`ApplicationMethod`'s exact
  shape, to avoid migrating Phase 7's already-shipped tables for a
  theoretical future benefit. `SchemeRelatedService` models the
  Scheme↔Service relationship (this phase's explicit requirement) as the
  smallest structure that supports it — one small mapped class with a
  `note` column and a unique constraint on the pair, not a full
  many-to-many association table. `GET /api/v1/schemes` (filtered, paged)
  and `GET /api/v1/schemes/{slug}` (benefits/requirements/documents/
  methods/related-services nested inline, the last filtered to only
  publicly-visible linked services) per [API.md](API.md) §15. Schemes is
  the *third* real domain to integrate with `search_documents`
  (`entity_type="scheme"`, [SEARCH.md](SEARCH.md) §16) — the explicit
  architectural test that the Phase 5 search abstraction generalizes to a
  third independent caller, verified with a live query returning a job, a
  service, and a scheme together. Frontend list/detail pages reuse the
  same Phase 4 components Jobs'/Services' pages do, plus `GovernmentService`
  + `BreadcrumbList` JSON-LD — `GovernmentService` reused rather than a
  new type invented, since schema.org's own documentation lists benefit
  programs as a direct example of that type ([SEO.md](SEO.md) §14).
- **Tests**: 37 new backend tests (models/constraints including the
  `SchemeRelatedService` unique-pair constraint and its bidirectional
  cascade behavior, service-layer visibility and search-index sync,
  API contract including the explicit Job+Service+Scheme cross-domain
  search test, migration up/down/up-again, fixture loading) plus 14 new
  frontend tests (list, detail, and category-filter/pagination controls)
  — 159 backend / 69 frontend tests passing in total, including full
  Phase 0–7 regression.
- **Documentation**: [DATABASE.md](DATABASE.md) §11–§12, [API.md](API.md)
  §15, [SEARCH.md](SEARCH.md) §16, [SEO.md](SEO.md) §14,
  [ARCHITECTURE.md](ARCHITECTURE.md), and this document updated with the
  realized schema, endpoints, search integration, SEO implementation, and
  the requirements-vocabulary extraction. In the course of this work,
  three pre-existing `docs/DATABASE.md §11` cross-references in
  `app/services/*.py` (written when Services' implementation-notes
  section was expected to land at §11) were corrected to the section's
  actual, current number, §10 — a one-line comment fix, not a schema or
  behavior change, made so the new §11/§12 sections this phase adds
  don't collide with a stale reference.
- **Acceptance criteria**: Three clearly-marked synthetic test schemes
  (`test-civiclens-scheme-001` pension/cash-benefit,
  `test-civiclens-scheme-002` scholarship-like,
  `test-civiclens-scheme-003` linked to a fixture Service) render
  end-to-end — list page, detail page with benefits/requirements/
  documents/application methods/related services, source/verification
  status visible, findable via `/search` alongside the Phase 6 test job
  and Phase 7 test service in the same query — verified directly against
  a live backend and frontend (a self-contained smoke test: scratch
  Postgres migrated to head, all three domains' fixtures loaded, API
  exercised via `TestClient`, scratch database torn down in the same
  process). No real government data entered.
- **Risks**: Requirement-vocabulary sprawl — mitigated by representing
  Schemes' additional beneficiary dimensions (student/employment status,
  social category, gender, disability, landholding) as `RequirementType.
  OTHER` plus descriptive prose rather than expanding the enum, avoiding
  a native-Postgres-enum `ALTER TYPE ... ADD VALUE` migration (and the
  harder-to-reverse downgrade it would need) for dimensions nothing in
  this phase filters or queries by. No new problems needed a hand-fix
  this phase — the `model_registry`-import and shared-fixture-geography
  fixes Phase 6/7 already found were reapplied proactively (get-or-create
  for the shared "Testland" state/"Test Recruitment Board — Not Real"
  organization, `model_registry` imported first in the new seed script)
  rather than being rediscovered by a fresh failure.
- **Rollback**: Additive; feature-flaggable.

## Phase 9 — Scholarships & Education Opportunities
- **Objective**: Establish Scholarships & Education Opportunities as a
  CivicLens domain — structured, searchable, verifiable information about
  educational financial-support opportunities. This document's original
  Phase 9 line named Public Representatives + Elections; the actual
  kickoff for this phase explicitly redirected work to Scholarships
  instead, ahead of Representatives + Elections. **Representatives +
  Elections is rescheduled, not cancelled** — see the note appended at
  the end of this document; it keeps its original scope description
  unchanged, pending an explicit decision on which upcoming phase number
  it now occupies, so this document does not guess a slot for it and
  create a second inconsistency alongside this one.
- **The central architectural question (this phase's §3/§28)**: should
  scholarships be (1) represented entirely as `Scheme` rows, (2) a
  specialized `Scheme` subtype, or (3) a dedicated domain referencing
  `Scheme` where appropriate? **Decision: (2), a specialized `Scheme`
  subtype.** `SchemeCategory` already included `SCHOLARSHIP` and
  `BenefitType` already included `SCHOLARSHIP_AMOUNT` since Phase 8 —
  the codebase already treated scholarships as one kind of scheme, not a
  separate concept. A scholarship shares every lifecycle/provenance/
  visibility/search concern `Scheme` already owns (same
  `publication_status`/`verification_status` gate, same
  `entity_type="scheme"` search projection, same `GET /api/v1/schemes`
  API). What's genuinely new is a fixed set of education-specific fields
  (education level, course/discipline, study mode, academic-performance
  thresholds, an application window, renewal) that would be permanently
  `NULL` on the other 15 `SchemeCategory` values if added directly to
  `schemes`. Resolution: a new 1:1 extension table, `scholarship_details`
  (unique `scheme_id` FK, `ON DELETE CASCADE`), carrying only that delta
  — no new audit architecture (it inherits its parent `Scheme` row's
  provenance entirely, like every other child table in this codebase),
  no new search entity type, no new API endpoint. Option (1) was
  rejected because it would lose genuinely useful structured data (no
  `education_level` to filter by, no application-window dates) by
  forcing everything into prose. Option (3) was rejected because it
  would duplicate the entire provenance/visibility/search machinery
  `Scheme` already provides for something that, in every real sense, IS
  a scheme — two audit trails for one conceptual entity.
- **Dependencies**: Phase 8 (`Scheme`, `SchemeRequirement`,
  `SchemeRequiredDocument`, `SchemeApplicationMethod`,
  `app.requirements` vocabulary).
- **Files/modules**: no new top-level module — `ScholarshipDetail` and
  its `EducationLevel`/`StudyMode` enums live inside `apps/api/app/
  schemes/` (the same "extract only when a second consumer appears"
  precedent §11/§12 already established, applied in reverse: there is
  no second consumer of this vocabulary, so nothing was extracted to its
  own module). One new Alembic migration
  (`f36a332eb8ca_add_scholarship_details.py`). `apps/web/app/[locale]/
  schemes/` gained a scholarship-details section on the detail page and
  an education-level filter on the list page — no new frontend routes.
- **Technical work**: `scholarship_details` — `scheme_id` (unique FK),
  `education_level` (9-value enum, nullable — even the scholarship's
  defining dimension is left unset rather than guessed when a source is
  silent), `course_discipline`/`institution_type`/`year_of_study` (prose,
  deliberately not reference tables — this phase's §10 explicitly warns
  against building an academic-institution database), `study_mode`
  (5-value enum, a genuinely bounded dimension like `DeliveryMode`),
  `minimum_percentage`/`minimum_cgpa` (`Numeric`, not `Float` — exact
  decimal comparison values, never evaluated against a real student in
  this phase), `academic_requirement_notes` (prose catch-all),
  `application_opens`/`application_closes`/`correction_window_end`
  (dates, mirroring `JobNotification`'s field names), `academic_year`
  (a label, not a date), `renewable`/`renewal_notes`. Household-income
  ceilings reuse `SchemeRequirement(requirement_type=INCOME)` rather than
  a duplicate field — the structured requirement model Phase 8 already
  built. Required documents reuse `SchemeRequiredDocument` as-is (no
  `DocumentType` taxonomy existed to extract, and none was invented).
  `GET /api/v1/schemes` gained one filter, `education_level` — only
  joined to `scholarship_details` when actually supplied, so every other
  (non-scholarship) list/count query pays no extra join cost.
  `GET /api/v1/schemes/{slug}` gained one nested field, `scholarship`
  (`null` for every non-scholarship scheme, not an object of all-`null`
  fields). No `ELIGIBLE`/`NOT_ELIGIBLE`/`INCOMPLETE` evaluation anywhere
  — Phase 10's Eligibility Engine domain, entirely.
- **Tests**: 10 new backend tests (model constraints including the
  1:1-uniqueness enforcement and cascade behavior in both directions,
  the `education_level` service-layer and API filter, the `scholarship`
  detail object appearing/being `null` correctly, the new migration's
  own upgrade/downgrade/upgrade cycle, fixture loading) plus 6 new
  frontend tests (education-level filter control, list-page filter
  pass-through, detail-page scholarship section rendering including an
  explicit "never renders a personalized eligibility verdict" check) —
  169 backend / 75 frontend tests passing in total, including full
  Phase 0–8 regression.
- **Documentation**: [DATABASE.md](DATABASE.md) §13 (plus Phase 8/9
  status notes added retroactively to this document's own intro, which
  had been left unwritten when Phase 8 landed), [API.md](API.md) §16,
  [SEARCH.md](SEARCH.md) §17 (documents *not* creating a new
  `entity_type="scholarship"` — scholarships are found via the existing
  `entity_type="scheme"` projection, since they are `Scheme` rows),
  [SEO.md](SEO.md) §15 (documents *not* adding new structured data for
  education-specific fields — no clean schema.org property fits without
  stretching semantics, so the existing `GovernmentService` JSON-LD is
  left unchanged rather than forcing a `Course`/
  `EducationalOccupationalProgram` type onto it), [FRONTEND.md](FRONTEND.md)
  §12, and this document.
- **Acceptance criteria**: The existing scholarship-like fixture scheme
  (`test-civiclens-scheme-002`) now carries a full `scholarship_details`
  row (education level, academic-performance thresholds, an application
  window, a renewal note) rendered on its detail page and reachable via
  the `education_level` filter — verified directly against a live
  backend and frontend (a self-contained smoke test: scratch Postgres
  migrated to head, all three domains' fixtures loaded, the scholarship
  fields and filter exercised via `TestClient`, cross-domain search
  re-verified unaffected, scratch database torn down in the same
  process). No real government data entered; no personalized eligibility
  verdict rendered anywhere.
- **Risks**: A real bug the live smoke test caught, not assumed away:
  an isolated check of `jsonable_encoder(Decimal(...))` outside a real
  response-model serialization path suggested `minimum_percentage`/
  `minimum_cgpa` would serialize as JSON numbers; the actual
  `TestClient` response showed Pydantic v2 serializes a `Decimal`
  response-model field as a **string** ("60.00") to preserve exact
  precision. `@civiclens/types`/`@civiclens/validation` were typed
  `number`, caught before commit, and fixed to `string`. Documented in
  both packages' comments so the next `Decimal`-typed field doesn't
  repeat the same wrong assumption. Requirement-vocabulary sprawl —
  mitigated the same way Phase 8 was: no `RequirementType` enum
  expansion for dimensions this phase names (student/employment status,
  social category, gender, disability, landholding), represented as
  `OTHER` + prose instead.
- **Rollback**: Additive; feature-flaggable.

---

**Representatives + Elections — rescheduled from Phase 9.** Original
scope, unchanged from this document's earlier plan, kept here rather
than assigned a new number so this document does not guess at a
sequencing decision that belongs to explicit product-owner approval
(the same "ask before major architectural changes" standard CLAUDE.md
rule 22 applies to code applies here to roadmap ordering):
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

## Phase 10 — Documents & Certificates
- **Objective**: Establish a first-class CivicLens information domain
  for government certificates, identity-related public documents, and
  other citizen-facing official documents. This document's original
  Phase 10 line named the Eligibility Engine; the actual kickoff for
  this phase explicitly redirected work to Documents & Certificates
  instead, the same kind of redirection Phase 9 already applied once —
  see the note appended at the end of this entry for where the
  Eligibility Engine's original scope now lives.
- **The central architectural question (this phase's §3/§32)**: is a
  document/certificate record (1) an existing document-reference
  abstraction reused, (2) a first-class `CivicDocument` entity, or (3)
  an extension of an existing model? **Decision: (2), a first-class
  `CivicDocument` entity — but explicitly *not* merged with
  `RequiredDocument`/`SchemeRequiredDocument` into one polymorphic
  system**, the specific mistake this phase's §32 warns against by
  name. The distinction the kickoff drew is real and predates this
  phase: `RequiredDocument`/`SchemeRequiredDocument` (Phase 7/8) are
  *requirements that a document be provided* — a name, a description, a
  mandatory flag, itemized under whatever parent needs one.
  `CivicDocument` is *the official document/certificate itself* — what
  an Income Certificate *is*: who issues it, what it's for, how to
  obtain one, what it costs, how long it's valid. Options considered
  and rejected: (1) reusing `Service` for this (an "Income Certificate
  Issuance" service already exists, but conflates the *act of issuing*
  with the *thing issued* — no field for purpose/validity/renewal) and
  (3) a single generic polymorphic table linking documents to
  jobs/services/schemes (exactly this phase's §32 prohibition, and
  literally the shape this document's own original §2.4 sketch — see
  [DATABASE.md](DATABASE.md) §2.4 — had proposed before a real
  implementation had to choose).
- **Dependencies**: Phase 6–9 patterns (Jobs/Services/Schemes/
  Scholarships); Institutions (§2.2); Requirements vocabulary (§11).
- **Files/modules**: `apps/api/app/documents/` (models, enums, schemas,
  service, fixtures) — a genuine new top-level domain module, unlike
  Scholarships (Phase 9), which stayed inside `app.schemes`.
  `apps/api/app/api/v1/documents.py`,
  `apps/api/scripts/seed_document_fixtures.py`,
  `apps/web/app/[locale]/documents/` (list + `[slug]` detail),
  `apps/web/lib/documents.ts`. `app.requirements.enums` gained
  `DeliveryMode` (moved from `app.services.enums`, a second consumer).
  `app.services.models.RequiredDocument` and
  `app.schemes.models.SchemeRequiredDocument` each gained one additive,
  nullable `civic_document_id` column — the "smallest relational
  design" (§14 of the kickoff) supporting the reverse "required by"
  lookup, not a new join table.
- **Technical work**: `civic_documents` carries the same denormalized
  provenance/visibility pattern as every other domain (independent
  `source_id` + `verification_status`/`last_verified_at`,
  `publication_status` as the one hard gate, its own
  `document_publication_status` enum type). `document_type` (7-value
  enum) and `document_category` (13-value enum) are two separate
  controlled taxonomies — the *kind of record* and the *subject
  matter* as distinct axes (this phase's §6/§7). `document_requirements`/
  `document_application_methods` reuse the shared `RequirementType`/
  `ApplicationChannelType` vocabulary as their own tables, mirroring
  `ServiceRequirement`/`ApplicationMethod` exactly.
  `document_supporting_documents` mirrors `RequiredDocument`'s shape
  plus one addition: a nullable, self-referential `civic_document_id`
  FK, for when a supporting document is itself a modeled
  `CivicDocument` (this phase's §11's recursive case). The "obtained
  through" relationship (§13) is a single nullable `service_id` FK
  directly on `civic_documents` — no join table, since (unlike
  Scheme↔Service in Phase 8) this phase named no per-relationship
  metadata to justify one. `GET /api/v1/documents` (filtered, paged)
  and `GET /api/v1/documents/{slug}` (requirements/supporting-documents/
  application-methods nested inline, plus `service` and `required_by`)
  per [API.md](API.md) §17. Documents is the *fourth* real domain to
  integrate with `search_documents` (`entity_type="document"`,
  [SEARCH.md](SEARCH.md) §18) — a genuine fourth `entity_type`, unlike
  Scholarships' deliberate non-addition — verified with a live query
  returning a job, a service, a scheme, and a document together.
  Frontend list/detail pages reuse the same Phase 4 components every
  prior domain does, plus `GovernmentService` + `BreadcrumbList`
  JSON-LD (schema.org fit checked against real documented properties,
  not guessed — [SEO.md](SEO.md) §16; `GovernmentPermit` was
  considered for permit/license/registration document types
  specifically and rejected as unnecessary branching).
- **Tests**: 46 new backend tests (model constraints including the
  recursive supporting-document self-reference and both directions of
  the additive `civic_document_id` columns' cascade behavior,
  service-layer visibility and search-index sync, the `required_by`
  reverse lookup including its explicit "never infers from matching
  names" test, API contract including the Job+Service+Scheme+Document
  cross-domain search test, the new migration's own upgrade/downgrade/
  upgrade cycle, fixture loading) plus 19 new frontend tests
  (document-type/category filter controls, list-page filter
  pass-through, detail-page rendering including the recursive
  supporting-document link, the related-service section, and the
  required-by section) — 216 backend / 94 frontend tests passing in
  total, including full Phase 0–9 regression.
- **Documentation**: [DATABASE.md](DATABASE.md) §14 (plus corrections to
  §2.3/§2.4/§2.6's stale phase-number references this rescheduling
  exposed), [API.md](API.md) §17, [SEARCH.md](SEARCH.md) §18,
  [SEO.md](SEO.md) §16, [FRONTEND.md](FRONTEND.md) §12,
  [ARCHITECTURE.md](ARCHITECTURE.md) §6 (module tree — `app.documents`
  added, `app.eligibility`/`app.representatives`/`app.elections`
  annotated as rescheduled rather than simply absent), and this
  document.
- **Acceptance criteria**: Two clearly-marked synthetic test documents
  (`test-civiclens-document-001`, a Residence Certificate; and
  `test-civiclens-document-002`, an Income Certificate linked to a
  fixture `Service`, with a supporting-document link back to the
  Residence Certificate, and a fixture `Scheme` whose
  `SchemeRequiredDocument` row points back at it) render end-to-end —
  list page, detail page with requirements/supporting documents/
  application methods/related service/required-by, source/verification
  status visible, findable via `/search` alongside the Phase 6 test
  job, Phase 7 test service, and Phase 8 test scheme in the same query
  — verified directly against a live backend and frontend (a
  self-contained smoke test: scratch Postgres migrated to head, all
  four domains' fixtures loaded, every feature exercised via
  `TestClient`, scratch database torn down in the same process). No
  real government data entered; no OCR/upload/verification/eligibility
  capability built.
- **Risks**: The exact "everything is a document" polymorphism this
  phase's §32 warns against — mitigated by keeping `RequiredDocument`/
  `SchemeRequiredDocument`/`CivicDocument` three distinct tables
  connected only by two small additive nullable FKs, never merged.
  Requirement-vocabulary sprawl — mitigated the same way Phase 8/9
  were: no `RequirementType` enum expansion for this phase's
  document-specific dimensions; `DeliveryMode`'s extraction to
  `app.requirements` was the one vocabulary change, verified via
  `alembic check` showing zero schema diff. Migration-test walk-down
  bounds needed re-tuning again (`tests/test_search/test_migrations.py`
  from 5→6 downgrades; `tests/test_schemes/test_scholarship_migration.py`
  converted from a bare `-1` to the walk-down pattern) — an expected,
  recurring maintenance cost of this codebase's "isolate the migration
  under test" strategy as the chain grows, not a new kind of bug.
- **Rollback**: Additive; feature-flaggable.

---

## Phase 11 — Eligibility Engine

**Realizes the "Eligibility Engine — rescheduled from Phase 10" entry**
this document previously carried in this slot (unnumbered, appended
after Phase 9 in the version of this document Phase 10 shipped) — the
scope described there is what actually landed, with one deliberate
narrowing (see below). This is the second phase-number collision this
document has recorded (the first: Phase 9/Scholarships vs. the original
Representatives + Elections plan) — resolved identically: this section
now holds what was actually built; the section it displaces
("Civic AI + RAG") is preserved verbatim, unnumbered, immediately below,
rather than renumbering Phases 12–18 or guessing a new slot for it.

- **Objective**: A deterministic Eligibility Engine evaluating
  ELIGIBLE/NOT_ELIGIBLE/INCOMPLETE for jobs, schemes (including
  scholarships), and services against citizen-submitted answers — never
  an LLM in the decision path (ADR-007).
- **Architecture decision**: `EligibilityRule`/`EligibilityCondition`
  (new tables) deliberately deviate from this document's own §2.4 sketch
  (`entity_type`/`entity_id` polymorphic pair): `EligibilityRule` carries
  three nullable FKs (`job_id`/`scheme_id`/`service_id`, `ON DELETE
  CASCADE`) with a `CHECK` requiring exactly one set — real referential
  integrity instead of an unenforceable pointer, extending Phase 10's
  precedent (rejecting `entity_documents`) to a second, larger case. See
  [DATABASE.md](DATABASE.md) §15 for the full writeup.
- **Scope narrowing**: the supported attribute set is a small, closed
  list (age, annual income, education level, academic percentage/CGPA,
  residence state, category) — date windows were evaluated and
  deliberately excluded (an application-window date is a fact about the
  *opportunity*, already shown on its own detail page, not something an
  *applicant* answers). No auth/session module exists yet, so evaluation
  is stateless over answers submitted in the request — never against a
  stored `Profile` — matching this phase's own privacy-minimization
  instruction more than it contradicts it.
- **Evaluability gate**: stricter than every other domain's display-
  visibility rule (`VERIFIED` OR `NEEDS_REVIEW`) — only
  `verification_status == VERIFIED` rules are ever evaluated, since a
  verdict is a claim of fact, not just displayed content.
- **Dependencies**: Phases 6–8 (entities to attach rules to) — met.
- **Files/modules**: `apps/api/app/eligibility/` (`enums.py`,
  `evaluator.py` — the pure core — `models.py`, `schemas.py`,
  `service.py`, `fixtures.py`), `apps/api/app/api/v1/eligibility.py`,
  `apps/web/app/[locale]/eligibility/[entityType]/[slug]/`.
- **Technical work**: `eligibility_rules`/`eligibility_conditions`
  migration; a pure `evaluate_rule()` function (typed dataclasses in/out,
  `Decimal` throughout, no DB/HTTP/wall-clock access); `GET
  /api/v1/eligibility/criteria` and `POST /api/v1/eligibility/evaluate`;
  a citizen-facing form rendering only the fields a given rule actually
  asks about, reusing the pre-existing `EligibilityStatus` design-system
  component (built in Phase 4, unused until now) plus `LastVerified`/
  `SourceBadge`/`VerificationStatus`.
- **Tests**: 100% branch coverage on `evaluate_rule` (37 dedicated unit
  tests, `--cov-branch`) — the mandatory gate from
  [TESTING.md](TESTING.md) §6; plus model/service/API/fixture/migration
  tests (69 total backend tests) and frontend form/page tests (10 total).
- **Documentation**: [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md),
  [DATABASE.md](DATABASE.md) §15, [API.md](API.md) §18,
  [ARCHITECTURE.md](ARCHITECTURE.md) §6, [FRONTEND.md](FRONTEND.md),
  [SEARCH.md](SEARCH.md), [SEO.md](SEO.md), this entry.
- **Acceptance criteria**: 100% branch coverage on the evaluation
  function — met; a fictional rule set evaluates correctly against
  fictional answers including an `INCOMPLETE` case — met (see the fixture
  job/scheme/service in `app/eligibility/fixtures.py` and the live smoke
  test below).
- **Risks**: Attribute enum growing unmanaged — mitigated by requiring a
  documented product need per new attribute, same as this document's
  original plan. No cross-domain link yet from a job/scheme/service
  detail page to its eligibility check (discoverable only via direct
  URL) — a known, disclosed limitation, not fabricated as done.
- **Rollback**: Evaluation is a pure function with no side effects, and
  the new tables are purely additive; safe to disable the route without
  data loss.

---

## Phase 12 — Civic AI + RAG

**Realizes the "Civic AI + RAG — rescheduled from Phase 11" entry** this
document previously carried in this slot. This is the third
phase-number collision this document has recorded (Phase 9/Scholarships
vs. Representatives + Elections; Phase 10/Documents vs. the Eligibility
Engine; Phase 11/Eligibility vs. Civic AI + RAG) — resolved identically
each time: this section now holds what was actually built; the section
it displaces ("Tracking + Notifications") is preserved verbatim,
unnumbered, immediately below.

- **Objective**: A source-grounded Civic AI system answering from
  retrieved, permitted CivicLens content only — citing sources,
  disclosing insufficient/unavailable evidence, and explaining (never
  computing) Eligibility Engine results — per
  [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) / [ADR-006](ADR/ADR-006-ai-rag-architecture.md).
- **Architecture decisions**:
  - **No pgvector** — verified unavailable in this project's actual
    local/test Postgres distribution and this development environment
    (no Docker); the kickoff's own "if feasible within the existing
    setup" wording anticipates exactly this. Embeddings are a plain
    `ARRAY(Float)` column with Python-side cosine similarity, disclosed
    as a scale-bounded MVP. See [DATABASE.md](DATABASE.md) §16.
  - `ai_knowledge_chunks` uses a shared `(entity_type, entity_id,
    locale)` key (not a foreign key, the opposite of Phase 11's
    `EligibilityRule`), and retrieval always `JOIN`s to
    `search_documents` as the trust/visibility gate — reusing the exact
    mechanism ordinary search already relies on rather than
    re-implementing a verification-status check.
  - Two independent provider abstractions
    (`LLMProvider`/`EmbeddingProvider`), both plain `httpx` adapters
    (Anthropic for completion, OpenAI for embeddings — Anthropic has no
    public embeddings endpoint), both defaulting to `"none"` so the app
    builds/boots/tests with AI fully disabled.
  - No re-indexing HTTP endpoint — no auth/role-check mechanism exists
    anywhere in this codebase yet, so per the kickoff's own
    "never expose an unauthenticated destructive indexing endpoint,"
    indexing is an internal function + `scripts/reindex_ai_knowledge.py`
    only.
- **Dependencies**: Phases 5 (search), 6, 7, 8 (retrievable content), 11
  (eligibility explanation source) — all met.
- **Files/modules**: `apps/api/app/ai/` (`providers.py`,
  `providers_anthropic.py`, `providers_openai.py`, `models.py`,
  `chunking.py`, `indexing.py`, `retrieval.py`, `prompting.py`,
  `citations.py`, `eligibility_explainer.py`, `service.py`,
  `rate_limit.py`, `schemas.py`), `apps/api/app/api/v1/ai.py`,
  `apps/web/app/[locale]/ai/`, an "Explain this result with Civic AI"
  addition to the existing `EligibilityForm` (Phase 11) rather than a
  second eligibility UI.
- **Technical work**: deterministic per-domain chunk builders (one
  chunk per entity, content-hash-keyed for idempotent re-indexing);
  lexical retrieval (reusing `search.service.search_documents` as-is)
  plus semantic retrieval (Python cosine similarity, filtered to the
  currently-configured embedding model/dimensions); a structured
  JSON response contract (not inline citation markers) so citations can
  be validated server-side against the actual retrieved evidence set;
  `<evidence>`-tag wrapping of all retrieved content as the structural
  prompt-injection defense; `POST /api/v1/ai/ask`, `POST /api/v1/ai/
  explain-eligibility`, `GET /api/v1/ai/health`; an in-process per-IP
  rate limiter for `/ai/*`; a real, previously-latent bug fix
  (`handle_http_exception` wasn't forwarding `exc.headers`, so no
  `429` had ever actually carried `Retry-After` before this phase
  exercised the path).
- **Tests**: 84 backend tests (`tests/test_ai/`) — citation-fabrication
  rejection, prompt-injection-wrapping structure, provider-unavailable
  degradation, idempotent-indexing, the `search_documents` trust-gate
  join, and — the phase's core safety property — a fake provider that
  actively tries to override a deterministic eligibility outcome and
  fails to. 20 frontend tests (Civic AI page + form, plus the
  eligibility-explanation addition). All against fake providers; no live
  credentials used or required.
- **Documentation**: [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §9-10,
  [DATABASE.md](DATABASE.md) §16, [API.md](API.md) §20,
  [ARCHITECTURE.md](ARCHITECTURE.md) §6, [SEARCH.md](SEARCH.md) §20,
  [SEO.md](SEO.md) §18, [FRONTEND.md](FRONTEND.md), [TESTING.md](TESTING.md) §8,
  [SECURITY.md](SECURITY.md) §14, this entry.
- **Acceptance criteria**: a fabricated/out-of-range citation can never
  surface as `GROUNDED` — met (proven directly, not just asserted); the
  Eligibility Engine's outcome cannot be changed by the LLM — met
  (proven directly); the app builds, boots, and passes its full test
  suite with zero provider credentials configured — met.
- **Risks**: real-model answer quality/hallucination risk is
  **unmeasured** — this phase proves the mechanical safety guarantees
  (citation validity, eligibility non-interference), not real-model
  groundedness quality, since no live provider calls are made in the
  test suite and no real government content exists yet to evaluate
  against. A live-model eval harness with a product-owner-set accuracy
  bar remains a named future task ([TESTING.md](TESTING.md) §8/§18).
  Rate limiting is a single-process MVP (no cross-instance
  coordination).
- **Rollback**: Both provider settings default to `"none"`; disabling
  either (or both) via environment variables degrades the feature to
  `PROVIDER_UNAVAILABLE` responses with no code change, and the new
  `ai_knowledge_chunks` table is purely additive.

---

**Tracking + Notifications — rescheduled from Phase 12, now realized.**
Built without a new phase number, for the same reason the Phase 9, 10,
and 11 rescheduling notes give — this document does not guess at a
sequencing decision that belongs to explicit product-owner approval.
Commits use a `tracking-notifications:` prefix rather than a
`phase-N:` one for this same reason:
- **Objective**: User tracking subscriptions and change notifications. Met.
- **Dependencies**: Phase 6–9 (trackable entities), Phase 3 (users). Also
  required real authentication (ADR-009 was accepted but not yet
  implemented before this work) — see [SECURITY.md](SECURITY.md) §2-3,
  now realized.
- **Files/modules**: `apps/api/app/auth/`, `apps/api/app/tracking/`,
  `apps/api/app/notifications/`, `apps/web/components/auth/`,
  `apps/web/components/tracking/`,
  `apps/web/app/[locale]/{login,register,dashboard}/`.
- **Technical work**: JWT cookie authentication (register/login/refresh/
  logout, CSRF double-submit); `tracked_items` (4 nullable entity FKs +
  a `CHECK`/`UNIQUE ... NULLS NOT DISTINCT` pair — see
  [DATABASE.md](DATABASE.md) §17) and `notifications`/
  `notification_delivery_attempts` (polymorphic, DB-deduplicated —
  §18); change detection via the pre-existing `ChangeRecord`/
  `ChangeReviewStatus` (§3), gated on `APPROVED`; deadline reminders,
  change notifications, and unavailability notifications; an optional
  Resend-backed email channel (default disabled); a
  `run_notification_sweep`/`deliver_notification_emails` pair invoked
  by `scripts/run_notification_sweep.py` (no scheduler exists yet —
  see the Known Limitations note below); dashboard
  (`/dashboard/tracking`, `/dashboard/profile`) and tracking controls
  on job/scheme/service/document detail pages.
- **Tests**: 495 backend tests (`apps/api/tests/test_auth`,
  `test_tracking`, `test_notifications`, plus updated migration
  walk-downs across every existing package), 139 frontend tests
  (Vitest), and a live smoke test against a real ad-hoc PostgreSQL
  instance exercising register → track → sweep → notify → dedup →
  mark-read → pause/resume → cross-user-denial → remove → logout end
  to end with real cookies/CSRF.
- **Documentation**: [DATABASE.md](DATABASE.md) §17-18,
  [API.md](API.md), [SECURITY.md](SECURITY.md), [PRIVACY.md](PRIVACY.md),
  [FRONTEND.md](FRONTEND.md), [TESTING.md](TESTING.md) updated against
  the realized implementation.
- **Acceptance criteria**: Met — tracking a fictional test entity and
  running the sweep against a real (non-fabricated) deadline produces a
  visible in-app notification; verified in the live smoke test above.
- **Risks**: Notification spam from noisy change detection — mitigated by
  only notifying on changes with `review_status == APPROVED`, consistent
  with [DATA_SOURCES.md](DATA_SOURCES.md) §4. Since Phase 13 (Admin
  Intelligence Center, below) does not exist yet, nothing in this
  codebase can currently move a `ChangeRecord` to `APPROVED` outside a
  test or a future admin tool — change-detected notifications are wired
  and tested but will not fire on real data until Phase 13 ships. This
  is the intended trust boundary, not a bug.
- **Rollback**: Additive; feature-flaggable (email delivery defaults to
  disabled; the sweep script is not invoked by anything else in this
  codebase).
- **Known limitations** (see also
  [FRONTEND.md](FRONTEND.md)/[SECURITY.md](SECURITY.md) for detail):
  no production scheduler/worker exists — `run_notification_sweep`/
  `deliver_notification_emails` are safe, idempotent, documented
  execution boundaries a future scheduler can invoke, not a running
  recurring process; no admin review UI exists yet to approve/reject a
  `ChangeRecord` (Phase 13's job); OAuth login remains deferred per
  ADR-009; no SMS/WhatsApp/push notification channel.

## Phase 13 — Admin Intelligence Center
- **Objective**: Ingestion pipeline + human review tooling per
  [DATA_SOURCES.md](DATA_SOURCES.md).
- **Dependencies**: Phases 3, 6–9 (entities to ingest into), the
  "Tracking + Notifications — rescheduled from Phase 12" entry above
  (notification trigger on approved change) — not yet built; this
  phase's own review-queue tooling does not require it to exist first.
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
