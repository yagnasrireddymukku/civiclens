# CivicLens — Database Architecture

Primary datastore: **PostgreSQL** (see [ADR-004](ADR/ADR-004-postgresql.md)).
This document defines the core entities, their purpose, and relationships.

**Phase 3 status**: geography (§2.1), provenance (§2.7), and the
user/profile identity foundation (§2.8, minus `saved_items`/
`tracking_items`/`notifications`, which are Phase 12) are implemented —
one Alembic migration (`apps/api/alembic/versions/`), SQLAlchemy models
under `apps/api/app/geography/`, `apps/api/app/sources/`, and
`apps/api/app/users/`. Institutions (§2.2), opportunities (§2.3),
requirements/eligibility (§2.4), time (§2.5), and people/elections (§2.6)
remain design-only, implemented incrementally in
[ROADMAP.md](ROADMAP.md) Phases 6–9 against real domain content — see §7
below for what Phase 3 deliberately deferred and why.

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

### 2.2 Institutions — deferred (see §7)
- **organizations** — recruiting boards, universities, corporations (e.g.,
  APPSC, TSPSC) — id, name, type, state_id (nullable for national bodies)
- **departments** — government departments issuing schemes/services — id,
  name, organization_id (nullable), state_id

### 2.3 Opportunities — deferred to Phases 6–8
- **jobs** — id, organization_id, title, description, department_id,
  state_id, category, status, source_id
- **job_notifications** — id, job_id, notification_number, published_date,
  total_vacancies, source_id (a job may have multiple notifications over
  time — amendments, corrigenda)
- **exams** — id, job_notification_id (nullable — some exams aren't
  job-linked, e.g. academic entrance exams), name, conducting_body_id,
  source_id
- **schemes** — id, department_id, state_id, name, description, target
  beneficiary summary, source_id
- **scholarships** — id, department_id/organization_id, state_id, name,
  award_amount, education_level, source_id
- **services** — id, department_id, state_id, name, description, channel
  (online/offline/both), source_id

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
PostgreSQL instance via `pgserver` (a pip-installable embedded Postgres
with prebuilt binaries), not Docker — this development environment has
no Docker/WSL2 available. Production and every deployed environment
remain plain PostgreSQL per [ADR-004](ADR/ADR-004-postgresql.md); this is
purely how the test suite provisions a database, detailed in
[TESTING.md](TESTING.md).
