# CivicLens — Database Architecture

Primary datastore: **PostgreSQL** (see [ADR-004](ADR/ADR-004-postgresql.md)).
This document defines the core entities, their purpose, and relationships.

**Phase 3 status**: geography (§2.1), provenance (§2.7), and the
user/profile identity foundation (§2.8, minus `saved_items`/
`tracking_items`/`notifications`, which are Phase 12) are implemented —
one Alembic migration (`apps/api/alembic/versions/`), SQLAlchemy models
under `apps/api/app/geography/`, `apps/api/app/sources/`, and
`apps/api/app/users/`.

**Phase 6 status**: institutions (§2.2) and the Jobs slice of
opportunities (§2.3) are implemented — see §9.

**Phase 7 status**: the Services slice of opportunities (§2.3) is
implemented — see §10, which also covers institutions (§2.2) moving to
its own module (`app.institutions`) now that a second domain depends on
it. Exams, schemes, and scholarships (the rest of §2.3) remain
design-only, implemented incrementally against real domain content in
[ROADMAP.md](ROADMAP.md) Phase 8 onward. Requirements/eligibility
(§2.4), time (§2.5), and people/elections (§2.6) also remain
design-only — see §7 for what Phase 3 deliberately deferred and why.

## 0. Design Rules

1. Every entity is created because a documented requirement in
   [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) needs it — not because
   it "sounds useful."
2. Every table that stores a public fact carries a path to provenance
   (`source_id` or via a join table) — see [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md).
3. All tables: `id` (UUID), `created_at`, `updated_at`. Soft-delete
   (`deleted_at` nullable) is used where retiring an entity must preserve
   history (jobs, schemes, representatives); hard delete is used for
   ephemeral/user-owned data on request (privacy deletion).
4. Translatable text fields (title, description) are modeled either as a
   companion `*_translations` table (`entity_id`, `locale`, `field`,
   `value`) or JSONB keyed by locale — decided per-table at Phase 3 based on
   query patterns, not decided speculatively here.
5. Money, dates, and ages are never free text where a rule needs to evaluate
   them — they are typed columns.

## 1. Why Not a Table Per Engine

Engines are mostly **behavior**, not new data. Civic Search projects
existing domain tables into an index. Civic AI retrieves from existing
tables plus `sources`. The Life Event Navigator and Personal Dashboard are
read-composition, not new domains. This keeps the schema close to the real
world (jobs, schemes, people, places) instead of the product's internal
feature list.

## 2. Core Entity Groups

### 2.1 Geography (state-agnostic — see [ARCHITECTURE.md](ARCHITECTURE.md) §3) — **implemented, Phase 3**
- **states** — id, name (unique), code (unique), slug (unique),
  status (`active`/`planned`)
- **districts** — id, state_id, name, code, slug (code and slug unique
  within a state, reusable across states)
- **constituencies** — id, state_id, type (`assembly`/`parliamentary`),
  name, slug (unique within state+type), district_id (nullable, some
  constituencies span districts or aren't meaningfully scoped to one)

`slug` on all three was added during Phase 3 implementation, beyond this
section's original field list — needed for the stable public URLs
[SEO.md](SEO.md) specifies (`/representatives/{state}/{constituency}`).
None of the three carry a direct `source_id`: geography is treated as
administrative reference data, not an evolving fact requiring
per-row provenance (contrast with §2.3's `source_id` columns).

### 2.2 Institutions — **implemented, Phase 6; its own module, Phase 7** (see §9, §10)
- **organizations** — recruiting boards, universities, corporations (e.g.,
  APPSC, TSPSC) — id, name, org_type (`CENTRAL`/`STATE`/`AUTONOMOUS_BODY`),
  state_id (nullable for national bodies), website_url. Treated as
  administrative reference data like geography (§2.1) — no `source_id`.
- **departments** — government departments issuing recruitment/services
  (and, in future phases, schemes) — id, name, organization_id (nullable
  — not every department sits under a recruiting board), state_id
  (nullable). Same reference-data treatment as organizations.

### 2.3 Opportunities — Jobs (Phase 6) and Services (Phase 7) slices **implemented** (see §9, §10); exams/schemes/scholarships deferred to Phase 8 onward
- **jobs** — id, slug (public identifier), locale, title, organization_id,
  department_id (nullable), summary, description, employment_type
  (`PERMANENT`/`CONTRACT`/`TEMPORARY`), category (free text), state_id,
  district_id (nullable), min_age/max_age (nullable — eligibility-relevant
  structured fields per [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md),
  not an eligibility rule itself), qualification_summary/
  experience_summary (prose — real notification wording rarely reduces to
  one structured value), salary_summary (text, never a fabricated number),
  status (free text, browse-friendly), publication_status
  (`DRAFT`/`PUBLISHED`/`ARCHIVED` — the public-visibility gate),
  source_id, verification_status, last_verified_at, deleted_at (soft
  delete, per §0 rule 3)
- **job_notifications** — id, job_id, notification_number (nullable),
  status (`DRAFT`/`REVIEW`/`PUBLISHED`/`APPLICATION_OPEN`/
  `APPLICATION_CLOSED`/`EXAMINATION`/`RESULT`/`ARCHIVED` — the detailed
  recruitment-cycle lifecycle a job's own `status` free-text field
  doesn't attempt to replicate), published_date, application_start/end,
  correction_window_end, exam_date, total_vacancies,
  official_notification_url, official_application_url, source_id,
  verification_status, last_verified_at (a job may have multiple
  notifications over time — amendments, corrigenda, or a wholly new
  recruitment cycle)
- **job_vacancies** — id, job_notification_id, post_name, vacancy_count
  (nullable), category (free text — reservation categories vary by
  state/organization and are deliberately not a hardcoded enum),
  location. Carries no provenance of its own — it inherits its parent
  notification's `source_id`.
- **exams** — id, job_notification_id (nullable — some exams aren't
  job-linked, e.g. academic entrance exams), name, conducting_body_id,
  source_id
- **schemes** — id, department_id, state_id, name, description, target
  beneficiary summary, source_id
- **scholarships** — id, department_id/organization_id, state_id, name,
  award_amount, education_level, source_id
- **services** — id, slug (public identifier), locale, organization_id,
  department_id (nullable), name, short_description, description,
  category (`ServiceCategory` — a controlled, bounded enum, unlike
  `jobs.category`'s free text: services form a citizen-facing set worth
  filtering by), service_type (free text), target_audience (prose),
  delivery_mode (`ONLINE`/`OFFLINE`/`BOTH`), state_id/district_id (both
  nullable — a service may be available statewide/nationally, unlike a
  job's required `state_id`), official_service_url, application_url,
  fee_summary/processing_time_summary/location_summary (text, never a
  fabricated figure), status (free text), publication_status
  (`DRAFT`/`PUBLISHED`/`ARCHIVED`), source_id, verification_status,
  last_verified_at, deleted_at — same provenance/visibility pattern as
  `jobs` (§9's denormalized-column rationale, unchanged for Phase 7)
  - **service_requirements** — id, service_id, requirement_type
    (`AGE`/`RESIDENCY`/`INCOME`/`OCCUPATION`/`OTHER`), description
    (prose), min_value/max_value (nullable numeric range) — structured
    just enough for a future Eligibility Engine
    ([ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md), Phase 10) to read
    without a migration; not that engine's own
    `attribute`/`operator`/`value` model
  - **service_required_documents** — id, service_id, name, description
    (nullable), is_mandatory
  - **service_application_methods** — id, service_id, channel_type
    (`ONLINE`/`OFFLINE`/`MOBILE_APP`/`MEESEVA`/`DEPARTMENT_PORTAL`/
    `SERVICE_CENTER`/`IN_PERSON`/`OTHER`), url (nullable, never
    fabricated), instructions (nullable prose)

  The three child tables carry no provenance of their own — like
  `job_vacancies`, each inherits its parent `services` row's `source_id`.

### 2.4 Requirements & Eligibility — deferred to Phase 10
- **documents** — id, name, description, issuing_authority_id
  (organization/department), typical_use
- **eligibility_rules** — id, entity_type, entity_id (polymorphic reference
  to job/scheme/scholarship/service), source_id, effective_date
- **eligibility_conditions** — id, rule_id, attribute (e.g. `age`,
  `qualification`, `domicile_state_id`, `income_annual`), operator
  (`>=`,`<=`,`in`,`==`, etc.), value — see
  [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) for evaluation semantics
- Join table **entity_documents** — links jobs/schemes/services to required
  `documents`

### 2.5 Time — deferred to Phases 6–8 (alongside the entities deadlines attach to)
- **deadlines** — id, entity_type, entity_id, stage (`notification`,
  `application_open`, `application_close`, `correction_window`,
  `admit_card`, `exam_date`, `answer_key`, `result`, custom), date,
  source_id, is_estimated (bool — some dates are provisional)

### 2.6 People & Elections — deferred to Phase 9 (politically neutral — see
[DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §5)
- **representatives** — id, name, role (`MLA`/`MP`/`Minister`/`CM`), party,
  constituency_id (nullable for state-wide roles), term_start, term_end,
  source_id
- **elections** — id, constituency_id, election_date, type, source_id
- **election_results** — id, election_id, candidate_name, party, votes,
  outcome, source_id

### 2.7 Provenance (see [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) for full model) — **implemented, Phase 3**
- **sources** — id, url, title, organization, source_type, published_date,
  retrieved_date
- **source_versions** — id, source_id, content_hash/snapshot_ref,
  captured_at
- **verification_records** — id, entity_type, entity_id, source_id, status
  (`VERIFIED`/`NEEDS_REVIEW`/`EXPIRED`/`UNVERIFIED`, a native Postgres
  enum), verified_by, verified_at, review_due_at
- **change_records** — id, entity_type, entity_id, field, old_value,
  new_value, detected_at, source_version_id, review_status
  (`PENDING`/`APPROVED`/`REJECTED` — named here for the first time; §2.7's
  original text didn't enumerate values), reviewed_by, applied_at

On `verification_records`/`change_records`, `entity_type` is a plain,
indexed `varchar`, not a database enum: Phase 3 has no domain tables yet
to enumerate (jobs, schemes, etc. arrive in Phases 6–9), and a hardcoded
enum here would need editing on every future domain phase. Validating
`entity_type` against real entity types is that future phase's
responsibility. `entity_id` has no FK (a polymorphic reference can't
target one specific table) — referential integrity for it is therefore
an application-level guarantee, not a DB-level one; this is a deliberate,
documented tradeoff of the polymorphic-association pattern.

### 2.8 Users & Personalization — identity implemented, Phase 3; the rest deferred (see §7)
- **users** — id, email (unique), password_hash (nullable if OAuth-only),
  role (`user`/`editor`/`admin`, a native Postgres enum), created_at —
  minimal fields, see [PRIVACY.md](PRIVACY.md) for data minimization.
  No auth flows exist yet (ADR-009/Phase 15) — this is identity storage.
- **profiles** — id, user_id (1:1 with `users`), explicitly-provided
  attributes used for eligibility/personalization (date_of_birth,
  qualification, state_id, district_id, category) — every field optional,
  nothing inferred. `category` is the reservation-category field flagged
  sensitive in [PRIVACY.md](PRIVACY.md) §2.
- **saved_items**, **tracking_items**, **notifications** — deferred to
  [ROADMAP.md](ROADMAP.md) Phase 12 (Tracking + Notifications); out of
  Phase 3's explicit scope (identity only, no tracking/notification
  features).

## 3. Relationships (summary)

```
states 1─* districts 1─* constituencies
organizations 1─* jobs 1─* job_notifications 1─* exams
departments 1─* schemes / scholarships / services
(jobs|schemes|scholarships|services) 1─* eligibility_rules 1─* eligibility_conditions
(jobs|schemes|scholarships|services) 1─* deadlines
(jobs|schemes|scholarships|services) *─* documents (via entity_documents)
constituencies 1─* representatives
constituencies 1─* elections 1─* election_results
every fact-bearing row ──> sources / verification_records
users 1─* profiles, saved_items, tracking_items, notifications
change_records reference the entity + source_version that produced them
```

## 4. Indexing & Performance (design intent, not implementation)

- Foreign keys indexed by default; composite indexes on
  `(state_id, status)` for domain tables (primary browse pattern).
- `pg_trgm` GIN indexes on searchable text fields for MVP search
  (see [SEARCH.md](SEARCH.md), [ADR-005](ADR/ADR-005-search-architecture.md)).
- `pgvector` index on an `embeddings` table (entity_type, entity_id, vector)
  for AI retrieval (see [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)).

## 5. Auditability & Versioning

- `change_records` is the audit trail for factual changes — this is not
  optional (see [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) NFR-A1).
- Row-level `updated_at` plus `change_records` is sufficient at MVP scale;
  full temporal tables are not introduced without a documented need.
- Soft deletion (`deleted_at`) preserves history for anything a user may
  have tracked or that appears in past change records.

## 6. What Is Deliberately Not Modeled Yet

- Multi-tenancy (not needed — single platform)
- Full-text document storage/OCR pipelines (Document Intelligence v1 is
  checklists, not document parsing)
- Event sourcing / CQRS (unjustified complexity at this scale)

These are documented absences, not oversights — revisit only with a stated
requirement.

## 7. Phase 3 Implementation Notes

The [ROADMAP.md](ROADMAP.md) Phase 3 kickoff scoped this phase to
geography, provenance, and user/profile identity specifically —
narrower than this document's original Phase 3 scope line, which also
named Institutions (§2.2). That's a disclosed scope decision, not an
oversight: §2.3–§2.6 (Institutions, Opportunities, Requirements &
Eligibility, Time, People & Elections) are implemented incrementally
against real domain content starting Phase 6, per the "deferred to
Phase N" notes on each subsection above. Organizations/departments will
be added as part of whichever domain phase first needs them as a foreign
key target (most likely Phase 6, Government Jobs).

**Module layout.** [ARCHITECTURE.md](ARCHITECTURE.md) §6 lists `sources/`
and `users/` as their own top-level backend modules (sibling to `core/`);
this document's original Phase 3 roadmap entry sketched a single
`app/core/models` location instead. Implementation followed
[ARCHITECTURE.md](ARCHITECTURE.md) — the modular-monolith boundary is the
stronger, more foundational commitment (§1 of that document) — plus a new
`app/geography/` module (not previously listed anywhere) for
states/districts/constituencies, since every future domain module will
need to reference geography and it deserves the same clean boundary as
`sources`/`users`. The DB session/engine itself lives under
`app/core/db/`, matching `core`'s documented role as "settings, db
session, shared deps." See [ROADMAP.md](ROADMAP.md) Phase 3 for the
updated files/modules line.

**Enums.** `state_status`, `constituency_type`, `verification_status`,
`change_review_status`, and `user_role` are all native PostgreSQL enum
types (via SQLAlchemy's `Enum`), not `varchar` + application-level
validation — enforced at the database level, per this phase's
constraints requirement. One Alembic gotcha worth recording:
autogenerate creates these types but does not emit a matching `DROP
TYPE` in the generated `downgrade()` — without adding that explicitly,
a downgrade-then-upgrade cycle fails with "type already exists." Fixed
in the initial migration; verified by an automated test
([TESTING.md](TESTING.md)) that runs upgrade → downgrade → upgrade.

**Test execution detail.** Integration/model tests run against a real
PostgreSQL instance, not Docker — this development environment has no
Docker/WSL2 available. As of Phase 3 this was `pgserver` (a
pip-installable embedded Postgres); as of Phase 5 it's a full-PostgreSQL
binary distribution instead, since the migration chain now requires
`pg_trgm` (§8), which `pgserver`'s Windows build doesn't bundle.
Production and every deployed environment remain plain PostgreSQL per
[ADR-004](ADR/ADR-004-postgresql.md); this is purely how the test suite
provisions a database, detailed in [TESTING.md](TESTING.md).

## 8. Phase 5 Implementation Note: `search_documents`

Phase 5 added one table outside the entity groups above:
`search_documents`, Civic Search's read-side projection
([SEARCH.md](SEARCH.md) §3, §12) — polymorphic (`entity_type`/`entity_id`,
no foreign key to any domain table, matching §2.7's `sources` pattern),
since no domain table exists yet for it to project from. It is not a
system of record (§1) and carries its own `source_id`/
`verification_status` columns so provenance survives into search
results even before a domain table exists to look them up from.

## 9. Phase 6 Implementation Notes: Jobs Domain

The first real domain module — `organizations`, `departments`, `jobs`,
`job_notifications`, `job_vacancies` (§2.2, §2.3) — landed largely as
originally sketched, with these realized-implementation details worth
recording:

**Provenance is denormalized onto the fact rows themselves.**
`jobs.verification_status`/`last_verified_at` and
`job_notifications.verification_status`/`last_verified_at` mirror
`search_documents`'s Phase 5 pattern (§8) rather than requiring a join to
`verification_records` for the common "is this displayable, and since
when" check. `verification_records` remains the authoritative audit
trail of verification *events*; these columns are a display-convenience
cache of current state, not a second source of truth. `jobs`/
`job_notifications` each carry their own independent `source_id` (an
amendment can cite a different official document than the original
notification) — both `RESTRICT` on delete, matching every other
fact-bearing table's FK-to-`sources` convention.

**Three distinct "status" concepts, deliberately not collapsed into
one**: `jobs.publication_status` (`DRAFT`/`PUBLISHED`/`ARCHIVED`) is the
one hard visibility gate — nothing reaches the public API or the search
index unless `PUBLISHED` and `VERIFIED`/`NEEDS_REVIEW`. `jobs.status` is
a free-text, browse-friendly label mirroring `search_documents.status`'s
existing convention (no fixed taxonomy for a still-forming domain).
`job_notifications.status` is the detailed 8-value recruitment-cycle
lifecycle this phase's kickoff named — it lives on the notification, not
the job, because the same job concept recurs across cycles with
independent lifecycles.

**No bilingual content model.** `jobs.locale` tags the language a row's
content is actually written in; it is not a translation pairing. Machine
translation of official text is prohibited
([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)), and human-translated
summaries are out of this phase's scope, so `/te/jobs` honestly shows
only `locale="te"` rows (none exist yet from fixtures) rather than a
fabricated translation of the English fixture — mirroring
[SEARCH.md](SEARCH.md) §7's Telugu-limitation disclosure.

**Fixture geography is shared, not duplicated.** Both
`app/search/fixtures.py` and `app/jobs/fixtures.py` reference
docs/TESTING.md §15's canonical fictional state ("Testland"/`ZZ`) — a
real bug, found by hand (seeding both fixture sets into the same
database failed with a duplicate-state-code error), was fixed by making
each loader get-or-create that row instead of blindly inserting it, so
either loader can now run first, or both, without collision.

## 10. Phase 7 Implementation Notes: Services Domain & Institutions Extraction

**Institutions moved to their own module.** `Organization`/`Department`
lived inside `app/jobs/models.py` from Phase 6 (§2.2's tables, always
conceptually distinct from §2.3's Jobs, just implemented together since
Jobs was the only consumer). Phase 7's Services domain needs the same
two tables, and importing them from `app.jobs.models` would be exactly
the cross-module reach-around CLAUDE.md rule 10 prohibits — so they
moved to `app.institutions.models`, the same role `app.geography`
already plays for every domain module. This was a model-layer move
only: `alembic check` showed zero schema diff after the move (same
table/column names, same constraints) — no migration needed for the
move itself, only for the new `services*` tables Phase 7 added on top.

**The `Organization`/`Department` ↔ `Job`/`Service` relationships are
resolved by name, not import**, to avoid a real circular import
(`app.jobs`/`app.services` import `app.institutions`, so the reverse
can't be a normal top-level import). SQLAlchemy resolves
`Mapped[list["Job"]]`/`Mapped[list["Service"]]` lazily against its
shared declarative registry the first time any mapper configures — which
requires every model module to have been imported by then. A real bug,
found by hand: a standalone script importing only `app.jobs.fixtures`
(not `app.services.models`) crashed with "expression 'Service' failed to
locate a name" the first time it touched `Organization`. Fixed by having
every `scripts/seed_*.py` entry point import `app.core.db.model_registry`
(this side-effect import registers every model module) before doing
anything else — the running API server was never affected, since
`app.main` already imports every domain's router, which transitively
imports every domain's models together.

**Services reuses Jobs' exact provenance/visibility/status pattern**
(§9) — denormalized `verification_status`/`last_verified_at`,
`publication_status` as the one hard visibility gate, a free-text
`status` for browse convenience, no bilingual content model
(`services.locale` tags actual content language, not a translation
pair). `service_category` is the one deliberate schema difference from
Jobs: a controlled, bounded enum (this phase's §5 requirement) rather
than `jobs.category`'s free text, since Services form a bounded,
citizen-facing taxonomy worth filtering by, unlike Jobs' open-ended
recruitment classification.

**`service_requirements` is deliberately not the eligibility engine.**
It stores a `requirement_type` (a small closed enum) plus an optional
numeric range plus prose — enough for a future Eligibility Engine
([ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md), Phase 10) to find "does
this service have an age requirement" without parsing prose, but no
`attribute`/`operator`/`value` predicate model, no evaluation logic, and
no `eligibility_rules`/`eligibility_conditions` rows are created —
Phase 10's domain, entirely.

**Fixture organizations/departments are shared across domains, not
duplicated**, extending §9's "shared fixture geography" fix: since
`organizations.name` is globally unique, `app/services/fixtures.py`
get-or-creates the same "Test Recruitment Board — Not Real" row
`app/jobs/fixtures.py` creates, rather than risking the same
duplicate-key collision found and fixed for the shared fictional state.
`app/jobs/fixtures.py`'s department creation was also changed to
get-or-create (and to link `organization_id`, previously left null) for
the same reason.
