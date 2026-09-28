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
it. Requirements/eligibility (§2.4), time (§2.5), and people/elections
(§2.6) remain design-only — see §7 for what Phase 3 deliberately
deferred and why.

**Phase 8 status**: the Schemes slice of opportunities (§2.3) is
implemented — see §12, which also covers the `RequirementType`/
`ApplicationChannelType` vocabulary moving to its own neutral module
(`app.requirements`, §11) now that a second domain depends on it.

**Phase 9 status**: Scholarships are represented as a `Scheme`
specialization, not a new opportunities slice — see §13 for the
architectural decision and the `scholarship_details` extension table it
introduces.

**Phase 10 status**: Documents & Certificates (§2.3, a genuinely new
domain module this time — `app.documents`) is implemented — see §14,
which also covers `DeliveryMode` moving to `app.requirements` (a second
consumer, joining `RequirementType`/`ApplicationChannelType` there) and
the additive `civic_document_id` columns Phase 6/7's already-shipped
`service_required_documents`/`scheme_required_documents` tables gained.
Exams remain design-only, implemented incrementally against real domain
content in a future phase (this document does not guess which number,
per [ROADMAP.md](ROADMAP.md)'s Phase 9/10 rescheduling note).

**Phase 11 status**: the Eligibility Engine (§2.4's sketch, realized in a
different shape) is implemented — see §15, which also covers why
`eligibility_rules` deviates from this section's own
`entity_type`/`entity_id` sketch. Representatives/Elections (§2.6) and
exams remain design-only.

**Phase 12 status**: Civic AI + RAG (the `embeddings` table
[ARCHITECTURE.md](ARCHITECTURE.md) §5 named, realized in a different
shape and without pgvector) is implemented — see §16, which also covers
why `ai_knowledge_chunks` deliberately does **not** carry a real foreign
key (unlike §15's `eligibility_rules`), and why it stores plain float
arrays instead of a `vector` column.

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

### 2.3 Opportunities — Jobs (Phase 6), Services (Phase 7), and Schemes (Phase 8, including Scholarships as a Phase 9 Scheme specialization) slices **implemented** (see §9, §10, §12, §13); `civic_documents` (Phase 10 — §14) is listed alongside them for its identical provenance pattern but is not itself part of this "opportunities" family — see §14 for why; exams remain deferred
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
    ([ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md), rescheduled from its
    original Phase 10 slot — see [ROADMAP.md](ROADMAP.md)) to read
    without a migration; not that engine's own
    `attribute`/`operator`/`value` model
  - **service_required_documents** — id, service_id, name, description
    (nullable), is_mandatory, civic_document_id (nullable FK to
    `civic_documents.id`, added Phase 10 — §14)
  - **service_application_methods** — id, service_id, channel_type
    (`ONLINE`/`OFFLINE`/`MOBILE_APP`/`MEESEVA`/`DEPARTMENT_PORTAL`/
    `SERVICE_CENTER`/`IN_PERSON`/`OTHER`), url (nullable, never
    fabricated), instructions (nullable prose)

  The three child tables carry no provenance of their own — like
  `job_vacancies`, each inherits its parent `services` row's `source_id`.
- **schemes** — id, slug (public identifier), locale, organization_id,
  department_id (nullable), name, short_description, description,
  category (`SchemeCategory` — a 16-value controlled enum, distinct from
  `ServiceCategory`), target_audience (prose — the unstructured half of
  the beneficiary profile), state_id/district_id (both nullable, like
  `services`), official_scheme_url, application_url, status (free
  text), publication_status (`DRAFT`/`PUBLISHED`/`ARCHIVED` — its own
  `scheme_publication_status` type, not shared with Services'/Jobs'),
  source_id, verification_status, last_verified_at, deleted_at — same
  provenance/visibility pattern as `jobs`/`services` (§9's
  denormalized-column rationale, unchanged for Phase 8)
  - **scheme_benefits** — id, scheme_id, benefit_type (`CASH_TRANSFER`/
    `SUBSIDY`/`SCHOLARSHIP_AMOUNT`/`PENSION`/`INSURANCE_COVERAGE`/
    `LOAN_SUBSIDY`/`IN_KIND_SUPPORT`/`OTHER`), description (prose),
    amount_summary (nullable text, never a fabricated figure),
    frequency_summary (nullable text)
  - **scheme_requirements** — id, scheme_id, requirement_type (reuses
    the shared `RequirementType` enum — §11), description (prose),
    min_value/max_value (nullable numeric range) — the structured half
    of the beneficiary-profile/eligibility-foundation requirement, not
    the Eligibility Engine's own predicate model (rescheduled from its
    original Phase 10 slot — see [ROADMAP.md](ROADMAP.md))
  - **scheme_required_documents** — id, scheme_id, name, description
    (nullable), is_mandatory, civic_document_id (nullable FK to
    `civic_documents.id`, added Phase 10 — §14)
  - **scheme_application_methods** — id, scheme_id, channel_type
    (reuses the shared `ApplicationChannelType` enum — §11), url
    (nullable, never fabricated), instructions (nullable prose)
  - **scheme_related_services** — id, scheme_id, service_id, note
    (nullable prose explaining the relationship), unique on
    (scheme_id, service_id) — the smallest structure supporting the
    Scheme↔Service relationship (§12); not a many-to-many association
    table, since it needs the `note` column
  - **scholarship_details** — id, scheme_id (unique FK — 1:1, not
    1:many, unlike every table above), education_level (`EducationLevel`
    — 9-value enum, nullable), course_discipline/institution_type/
    year_of_study (prose), study_mode (`StudyMode` — 5-value enum,
    nullable), minimum_percentage/minimum_cgpa (`Numeric`, nullable —
    never evaluated against a real student, the Eligibility Engine's
    domain, rescheduled from its original Phase 10 slot),
    academic_requirement_notes (prose), application_opens/
    application_closes/correction_window_end (nullable dates,
    source-backed only), academic_year (a label, not a date), renewable
    (boolean), renewal_notes (prose) — the Phase 9 education-specific
    delta a `category == SCHOLARSHIP` scheme carries; see §13 for the
    full architectural decision

  The six child tables carry no provenance of their own — each
  inherits its parent `schemes` row's `source_id`.
- **civic_documents** (Phase 10 — §14; not part of the Jobs/Services/
  Schemes "opportunities" family, but listed here alongside them since
  it shares the identical provenance/visibility pattern) — id, slug
  (public identifier), locale, organization_id, department_id
  (nullable), name, short_description, description, document_type
  (`DocumentType` — 7-value enum), category (`DocumentCategory` —
  13-value enum, a distinct axis from `document_type`), purpose (prose,
  source-backed only, never an invented claim about legal significance),
  state_id/district_id (both nullable, like `services`/`schemes`),
  delivery_mode (reuses the shared `DeliveryMode` enum — §14),
  official_document_url, application_url, fee_summary/
  processing_time_summary/validity_summary/renewal_summary (text, never
  a fabricated figure), service_id (nullable FK to `services.id` — the
  "obtained through" relationship, §14), status (free text),
  publication_status (`DRAFT`/`PUBLISHED`/`ARCHIVED` — its own
  `document_publication_status` type), source_id, verification_status,
  last_verified_at, deleted_at — same provenance/visibility pattern as
  `jobs`/`services`/`schemes` (§9's denormalized-column rationale)
  - **document_requirements** — id, document_id, requirement_type
    (reuses the shared `RequirementType` enum — §11), description
    (prose), min_value/max_value (nullable numeric range) — the
    structured half of the eligibility-relevant-to-obtain-this-document
    requirement, not the Eligibility Engine's own predicate model
  - **document_supporting_documents** — id, document_id, name,
    description (nullable), is_mandatory, civic_document_id (nullable,
    self-referential FK to `civic_documents.id` — for when a supporting
    document is itself a modeled `CivicDocument`, §14)
  - **document_application_methods** — id, document_id, channel_type
    (reuses the shared `ApplicationChannelType` enum — §11), url
    (nullable, never fabricated), instructions (nullable prose)

  The three child tables carry no provenance of their own — each
  inherits its parent `civic_documents` row's `source_id`.

### 2.4 Requirements & Eligibility — **fully realized** (documents/entity_documents in a different shape, Phase 10, §14; eligibility_rules/eligibility_conditions in a different shape, Phase 11, §15)
- ~~**documents** — id, name, description, issuing_authority_id
  (organization/department), typical_use~~ — realized as `civic_documents`
  (§14), with substantially more structure than sketched here (document
  type/category taxonomies, purpose, delivery mode, fee/processing-time/
  validity/renewal summaries, an "obtained through" `Service` link,
  requirements, supporting documents, application methods) once a real
  implementation phase worked out what the domain actually needed.
- ~~**eligibility_rules** — id, entity_type, entity_id (polymorphic reference
  to job/scheme/scholarship/service), source_id, effective_date~~ —
  realized as `eligibility_rules` (§15) with three nullable FKs
  (`job_id`/`scheme_id`/`service_id`, a `CHECK` requiring exactly one)
  instead of a polymorphic `entity_type`/`entity_id` pair — the same
  "reject the polymorphic sketch once a real implementation has to choose"
  pattern §14 established for `entity_documents`, applied a second time.
- ~~**eligibility_conditions** — id, rule_id, attribute (e.g. `age`,
  `qualification`, `domicile_state_id`, `income_annual`), operator
  (`>=`,`<=`,`in`,`==`, etc.), value~~ — realized as `eligibility_conditions`
  (§15) with the same attribute/operator shape sketched here, but typed
  value columns (`numeric_value`/`numeric_value_max`/`text_value`/
  `text_values`) instead of one generic `value` column — see
  [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) for evaluation semantics.
- ~~Join table **entity_documents** — links jobs/schemes/services to required
  `documents`~~ — **not built**; superseded by §14's smaller design: two
  additive, nullable `civic_document_id` columns directly on
  `service_required_documents`/`scheme_required_documents`, rather than a
  generic polymorphic join table. Phase 10's kickoff explicitly weighed
  and rejected the polymorphic-table shape this line originally sketched
  (see §14's "options considered and rejected") once a real
  implementation had to choose between the two.

### 2.5 Time — deferred to Phases 6–8 (alongside the entities deadlines attach to)
- **deadlines** — id, entity_type, entity_id, stage (`notification`,
  `application_open`, `application_close`, `correction_window`,
  `admit_card`, `exam_date`, `answer_key`, `result`, custom), date,
  source_id, is_estimated (bool — some dates are provisional)

### 2.6 People & Elections — deferred (Representatives & Elections, rescheduled from this section's original "Phase 9" slot — see [ROADMAP.md](ROADMAP.md)'s Phase 9/10 rescheduling note; this document does not guess its new number); politically neutral — see
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
  features). **Realized (rescheduled from Phase 12, §17-18): only
  `tracked_items` and `notifications`/`notification_delivery_attempts`
  — the kickoff's explicit scope.** `profiles` and `saved_items` remain
  unbuilt; `users` gained one column
  (`email_notifications_enabled`) rather than a separate `profiles`
  table, since no eligibility/personalization attribute storage was in
  scope for this work.

## 3. Relationships (summary)

```
states 1─* districts 1─* constituencies
organizations 1─* jobs 1─* job_notifications 1─* exams
departments 1─* schemes / scholarships / services
(job|scheme|service) 1─* eligibility_rules 1─* eligibility_conditions — three
  direct nullable FKs (§15), not a polymorphic pair; scholarships are
  covered via their parent `scheme_id`
(jobs|schemes|scholarships|services) 1─* deadlines
(jobs|schemes|scholarships|services) *─* civic_documents (via additive
  civic_document_id columns, §14 — not a join table)
constituencies 1─* representatives
constituencies 1─* elections 1─* election_results
(jobs|schemes|services|civic_documents) via search_documents ─┬ ai_knowledge_chunks
  — a shared (entity_type, entity_id, locale) key (§16), not a foreign
  key; retrieval always JOINs through search_documents as the trust gate
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

## 11. Phase 8 Implementation Note: Requirements Vocabulary Extraction

**`RequirementType`/`ApplicationChannelType` moved from
`app.services.enums` to a new, neutral `app.requirements.enums`
module** once Schemes (§12) needed the exact same two vocabularies
Services (§10) already used. This mirrors §10's Institutions
extraction precedent exactly: a pure Python/enum-level move, verified
via `alembic check` showing zero schema diff, with every existing
`service_requirements`/`service_application_methods` column and
constraint left byte-for-byte unchanged (`postgresql.ENUM(...,
create_type=False)` against the same, already-created
`requirement_type`/`application_channel_type` Postgres types).

**Only the vocabulary moved — not the tables.** `ServiceRequirement`/
`RequiredDocument`/`ApplicationMethod` remain Services-only tables;
Schemes gets its own `scheme_requirements`/`scheme_required_documents`/
`scheme_application_methods` tables with the identical shape, importing
only the two enum classes from the new shared module. A single shared
polymorphic table (e.g. one `requirements` table with a nullable
`service_id`/`scheme_id`/`job_id`) was considered and rejected: it would
require migrating Phase 7's already-shipped tables for a theoretical
future benefit, which this phase's explicit "preserve backward
compatibility" instruction and CLAUDE.md rules 9/12/22 counsel against.
`RequiredDocument` has no equivalent vocabulary to extract in the first
place (no `DocumentType` enum exists) — there was nothing to move there,
only tables that stay deliberately domain-specific.

**`RequirementType` was not expanded** to cover the additional
beneficiary dimensions Schemes' beneficiary profile names (student/
employment status, social category, gender, disability, landholding).
Those are represented via `RequirementType.OTHER` plus descriptive prose
in `SchemeRequirement.description`, avoiding a Postgres `ALTER TYPE ...
ADD VALUE` migration (and the harder-to-reverse downgrade it would need)
for dimensions nothing in this phase filters or queries by.

## 12. Phase 8 Implementation Notes: Schemes Domain

**Scheme vs. Service** (this phase's §3): a `Service` is something a
citizen requests/accesses (an issuance, a certificate, a transaction); a
`Scheme` is a benefit/support program a citizen may be eligible for
(financial assistance, a subsidy, a scholarship, a pension, insurance,
or livelihood/agricultural/housing/education/healthcare/employment
support). Both reuse Jobs'/Services' exact provenance/visibility/status
pattern (§9, §10) — denormalized `verification_status`/
`last_verified_at`, `publication_status` as the one hard visibility
gate (its own `scheme_publication_status` Postgres enum type,
deliberately not shared with `service_publication_status`/
`job_publication_status` even though all three have identical values,
for the same domain-scoping reason §10 gives), a free-text `status` for
browse convenience, no bilingual content model.

**`scheme_category` is a 16-value controlled enum** (this phase's §5) —
bounded and citizen-facing like `service_category`, but a distinct
taxonomy since a benefit program's kind (Scholarship, Pension, Subsidy,
...) doesn't map onto a service's kind (Certificates, Documents, ...).

**`SchemeBenefit` is new to this domain** — Services has no equivalent.
It stores a `benefit_type` (a small closed enum: cash transfer, subsidy,
scholarship amount, pension, insurance coverage, loan subsidy, in-kind
support, or other) plus prose plus an optional `amount_summary` string —
never a fabricated figure. Like `Job.salary_summary`/
`Service.fee_summary`, `amount_summary` is populated only when a source
states one.

**`SchemeRequirement` is the structured half of this phase's §7/§8
beneficiary-profile/eligibility-foundation requirement** — it reuses
`ServiceRequirement`'s exact shape and the shared `RequirementType`
vocabulary (§11), never evaluating ELIGIBLE/NOT_ELIGIBLE/INCOMPLETE
(Phase 10's Eligibility Engine domain, entirely).
`SchemeRequiredDocument`/`SchemeApplicationMethod` likewise mirror
Services' `RequiredDocument`/`ApplicationMethod` shape as their own
tables — see §11 for why no shared table was introduced.

**`SchemeRelatedService` models the Scheme↔Service relationship**
(this phase's §11 of the kickoff, not to be confused with this
document's §11 above) as the smallest structure that supports it: one
small mapped class (`scheme_id`, `service_id`, an optional `note`
explaining *why* they're related) with a unique constraint on the pair,
rather than a full many-to-many association table with its own separate
infrastructure. A bare `secondary=` table was considered and rejected —
it can't carry the `note` column this phase's fixture guidance (§25)
wants, so the small mapped class ends up no more complex while
supporting the documented requirement.

**Organization/Department gained a `schemes` relationship** (`app.
institutions.models`) alongside their existing `jobs`/`services` ones —
the third and, per that module's original Phase 7 docstring, expected
consumer of the shared institutions tables.

**Fixture geography/organization/department are shared across all
three domains, not duplicated**, extending §10's fix: `app/schemes/
fixtures.py` get-or-creates the same "Testland" state and "Test
Recruitment Board — Not Real" organization Jobs'/Services' fixtures
create. The service-linked scheme fixture also get-or-creates its own
small `Service` row rather than depending on `app/services/fixtures.py`
having run first, so `app/schemes/fixtures.py` stays independently
runnable like every other domain's fixture loader.

## 13. Phase 9 Implementation Notes: Scholarships as a Scheme Specialization

**Architectural decision (Phase 9's §3/§28)**: scholarships are
represented as a `Scheme` specialization — `category == SCHOLARSHIP`
plus a 1:1 `ScholarshipDetail` extension row — not a new opportunities
slice and not a fully independent domain. `SchemeCategory` already
included `SCHOLARSHIP` and `BenefitType` already included
`SCHOLARSHIP_AMOUNT` since §12 — the schema already treated scholarships
as one kind of scheme before this phase existed. A scholarship shares
every lifecycle/provenance/visibility/search concern `Scheme` already
owns; the two rejected alternatives were (1) representing scholarships
with no new fields at all (loses genuinely useful structured data —
no `education_level` to filter by, no application-window dates,
forcing everything into prose) and (3) a fully independent domain with
its own `source_id`/`verification_status`/`publication_status`/search
`entity_type` (would duplicate the entire provenance/visibility/search
machinery `Scheme` already provides for something that, in every real
sense, IS a scheme — two audit trails for one conceptual entity,
which §21's "do not create a second audit architecture" rules out).

**`scholarship_details` is a 1:1 extension table, not a 1:many child
table** like every other table §9–§12 introduced. Its only identity is
a unique `scheme_id` FK (`ON DELETE CASCADE`) — enforced at the database
level via a unique index, not merely a service-layer convention — so at
most one row exists per scheme. It carries no provenance of its own,
inheriting its parent `Scheme` row's entirely, the same "child inherits
parent's `source_id`" convention every table since §9 follows.
Nothing enforces that a `scholarship_details` row only exists when its
parent's `category == SCHOLARSHIP` — that pairing is a service-layer/
fixture convention, not a hard database rule, deliberately: a `CHECK`
(or trigger) spanning two tables for a convention nothing yet depends on
would be the kind of premature enforcement this phase's §28 warns
against.

**Fields, and why each is shaped the way it is**:
- `education_level` (9-value enum, **nullable**) — even the
  scholarship's defining dimension is left unset rather than guessed
  when a source is silent on it, matching every other domain module's
  "never fabricate, `NULL` when unknown" convention (CLAUDE.md rule 3).
- `course_discipline`/`institution_type`/`year_of_study` — prose, not
  reference tables. Phase 9's §10 explicitly warns against building a
  full academic-institution/course database in this phase; real-world
  values ("Any UGC-recognized undergraduate discipline") don't reduce
  to a small closed set the way `education_level` does.
- `study_mode` (5-value enum) — unlike the three fields above, a
  genuinely bounded dimension, matching `DeliveryMode`'s precedent
  (§10) for when an enum, not prose, is the honest choice.
- `minimum_percentage`/`minimum_cgpa` (`Numeric(5,2)`/`Numeric(4,2)`,
  not `Float`) — exact decimal comparison values (60.00, not
  59.999999...), matching real academic-cutoff notation. Nothing in
  this phase evaluates them against a real student's marks (Phase 10's
  Eligibility Engine domain, entirely) — the exact type is chosen so a
  future comparison doesn't have to migrate away from a lossy one.
- `academic_requirement_notes` — prose catch-all for a documented
  condition that isn't one of the two structured fields above.
- `application_opens`/`application_closes`/`correction_window_end`
  (`Date`) — mirrors `JobNotification`'s exact field names and meaning
  (§9); dates must be source-backed, never invented or generated
  (Phase 9's §13).
- `academic_year` (a label, e.g. "2026-27") — not a `Date`: an academic
  year is a named period, not a point in time.
- `renewable`/`renewal_notes` — a flag plus prose describing renewal
  conditions; no automatic-renewal workflow exists or is implied
  (Phase 9's §14 explicitly prohibits one).

**Household-income ceilings and required documents are reused, not
duplicated.** An income ceiling is a `SchemeRequirement` row
(`requirement_type=INCOME`, `max_value` set) — the exact structured
requirement model §12 already built, reused rather than adding a
duplicate `income_ceiling` column to `scholarship_details`. Required
documents reuse `SchemeRequiredDocument` as-is: unlike `RequirementType`/
`ApplicationChannelType`, `RequiredDocument` never had a vocabulary
*enum* to extract in the first place (no `DocumentType` exists anywhere
in this codebase), so there was nothing to move and nothing to
duplicate — the existing `name`/`description`/`is_mandatory` shape
already fits "income certificate," "caste certificate," "bonafide
certificate," etc. without any change.

**`GET /api/v1/schemes` gained one filter, `education_level`** — see
[API.md](API.md) §16. It joins `scholarship_details` only when actually
supplied, so every other (non-scholarship) list/count query pays no
extra join cost; combining it with a non-scholarship `category` yields
zero results deterministically, the same way any other AND-combined
filter pair would, rather than one filter silently overriding the other.

**A real bug the live smoke test caught, not assumed away**: an
isolated check of `jsonable_encoder(Decimal(...))` outside a real
response-model serialization path suggested `minimum_percentage`/
`minimum_cgpa` would serialize as JSON numbers. The actual `TestClient`
response showed Pydantic v2 serializes a `Decimal` response-model field
as a **string** ("60.00") to preserve exact precision instead.
`@civiclens/types`/`@civiclens/validation` were initially typed
`number`, caught before commit by the live smoke test (not by unit
tests, which had mocked the API layer and so never exercised real
serialization), and fixed to `string`.

## 14. Phase 10 Implementation Notes: Documents & Certificates Domain

**Architectural decision (Phase 10's §3/§32)**: Documents & Certificates
is a genuinely first-class domain module (`app.documents`,
`CivicDocument`) — **not** a `Scheme`/`Service` specialization, and not
a generic polymorphic "everything is a document" abstraction folding
`RequiredDocument`/`SchemeRequiredDocument` together with it. The
distinction the kickoff drew is real and pre-existing in the data:
`RequiredDocument`/`SchemeRequiredDocument` (§9, §12) are *requirements
that a document be provided* — a name, a description, a mandatory flag,
itemized under whatever parent needs one. `CivicDocument` is *the
official document/certificate itself* — what an Income Certificate
*is*: who issues it, what it's for, how to obtain one, what it costs,
how long it's valid. These were never the same entity even before this
phase; Phase 10 gives the second one a table for the first time.
Options considered and rejected: (1) representing documents entirely as
`Service` rows (an "Income Certificate Issuance" service already
exists, but conflates the *act of issuing* with the *thing issued* —
losing purpose/validity/renewal information a service has no field
for) and (3) collapsing `RequiredDocument`/`SchemeRequiredDocument`/
`CivicDocument` into one shared polymorphic table (exactly the
complexity this phase's §32 names and prohibits).

**`civic_documents` carries the same provenance/visibility pattern as
every other domain** (§9/§10/§12) — denormalized `verification_status`/
`last_verified_at`, `publication_status` as the one hard visibility
gate (its own `document_publication_status` Postgres enum type, not
shared with the other three domains' publication-status enums, for the
same domain-scoping reason §10 gives). `document_type` (7-value enum:
Certificate/Identity Document/Record/Permit/License/Registration/Other)
and `document_category` (13-value enum: Personal/Identity/Residence/
Income/Social Category/Education/Birth & Death/Disability/Land &
Revenue/Employment/Business/Family/Other) are two separate controlled
taxonomies, deliberately not collapsed into one — this phase's §6/§7
asks for the *kind of official record* and the *subject matter* as
distinct axes, the same way `Job.employment_type` and `Job.category`
already are.

**`document_requirements`/`document_application_methods` reuse the
shared vocabulary** (`RequirementType`/`ApplicationChannelType` from
`app.requirements.enums`) as their own tables, not shared ones — the
same reasoning `ServiceRequirement`/`ApplicationMethod` already
established, now confirmed by a fourth consumer.

**`DeliveryMode` moved to `app.requirements.enums`** in this phase, for
the identical "extract when a second consumer appears" reason §11
extracted `RequirementType`/`ApplicationChannelType` — Documents needed
the same online/offline/both vocabulary Services already defined. Pure
Python/enum-level move, verified via `alembic check` showing zero
schema diff; `services.delivery_mode` keeps the exact column it always
had, just importing the enum class from its new location.

**`document_supporting_documents` is `RequiredDocument`'s shape plus one
addition**: a nullable, self-referential `civic_document_id` FK to
`civic_documents.id` (`ON DELETE SET NULL`) — for when a supporting
document (e.g. "Residence Certificate" required to obtain an Income
Certificate) is itself a modeled `CivicDocument`. `NULL` when no such
record exists yet, exactly like every other `*RequiredDocument` table's
free-text-only default behavior.

**The "obtained through" relationship** (this phase's §13) is a single
nullable `service_id` FK directly on `civic_documents` (`ON DELETE SET
NULL`), not a join table — unlike Scheme↔Service (§12's
`SchemeRelatedService`), this phase names no per-relationship metadata
(no `note` field requested), so a join table would have added
infrastructure for nothing a plain FK doesn't already provide.

**The "required by" reverse relationship** (this phase's §14/§22 of the
kickoff — the "smallest relational design that allows future
discovery" instruction) is two purely additive, nullable
`civic_document_id` columns (`ON DELETE SET NULL`) added to the
already-shipped `service_required_documents` (Phase 7) and
`scheme_required_documents` (Phase 8) tables — not a new join table, not
a generic polymorphic reference graph (both explicitly considered and
rejected, per the module-level §32 discussion above). `NULL` on both by
default (today's existing behavior, completely unchanged for every
existing row); a source-backed link sets it. `app.documents.service.
get_required_by()` is the one place this domain reads those two
columns back across module boundaries — a legitimate, explicitly-
modeled cross-domain read, the same precedent `app.schemes.service`
already established reading `app.services.service.is_publicly_visible`
for `related_services` (Phase 8). Critically, this reverse lookup is
**never** inferred from two records happening to share a name — only a
real `civic_document_id` link ever appears in `required_by`, per this
phase's explicit §22 prohibition (verified by a dedicated test,
`test_get_required_by_never_infers_from_matching_names`). Jobs have no
document-requirement table at all (verified by hand: `app.jobs.models`
defines only `Job`/`JobNotification`/`JobVacancy`), so Jobs never appear
in `required_by` — an accurate absence, not a gap.

**Fixture geography/organization/department are shared across all four
domains, not duplicated**, extending §10's fix: `app/documents/
fixtures.py` get-or-creates the same "Testland" state and "Test
Recruitment Board — Not Real" organization every other domain's
fixtures create. The linked `Service` and linked `Scheme` fixtures are
likewise this module's own small get-or-create fixtures (not a hard
dependency on `app.services.fixtures`/`app.schemes.fixtures` having run
first), so `app/documents/fixtures.py` stays independently runnable —
and the linked `Scheme`'s one `SchemeRequiredDocument` row is what gives
`get_required_by()` something real to find, demonstrating the full
reverse relationship end to end from fixture data alone.

## 15. Phase 11 Implementation Notes: Eligibility Engine

**Architectural decision (this phase's §3/§C)**: informational
requirements (`SchemeRequirement`/`ServiceRequirement`/
`DocumentRequirement` — prose + a bounded `requirement_type` + an
optional integer range) stay exactly as they were, untouched by this
phase. A new, additive pair of tables — `eligibility_rules` and
`eligibility_conditions` — holds the machine-evaluable predicate model
these tables were always documented as *not* being (see each of their
module docstrings, going back to Phase 7). This confirms, rather than
changes, three phases' worth of "this is deliberately not the
eligibility engine" comments.

**`eligibility_rules` deviates from this document's own §2.4 sketch**
(a polymorphic `entity_type`/`entity_id` pair). Instead it carries three
nullable foreign keys — `job_id`, `scheme_id`, `service_id`, each
`ON DELETE CASCADE` — with a Postgres `CHECK` constraint
(`num_nonnulls(job_id, scheme_id, service_id) = 1`) enforcing that
exactly one is set. This is the same "reject the polymorphic sketch for
a small, fixed type set" reasoning Phase 10 applied to
`entity_documents` (§14), scaled to a second, larger case: a real
foreign key gives referential integrity a `(text, uuid)` pair never
could (a rule can't outlive or mis-point at the entity it governs), and
cascading delete cleans up automatically. The cost — a new migration if
a fourth entity type is ever added — was judged acceptable against
CLAUDE.md rule 12 ("avoid premature optimization") for a set this
phase's kickoff names as exactly three (jobs, schemes — which cover
scholarships via their parent `scheme_id`, since Scholarships remain a
`Scheme` specialization per §13 — and services). `CivicDocument` is
deliberately excluded: a document isn't itself something a citizen is
eligible/not-eligible for.

**`eligibility_conditions`** holds one predicate per row: `attribute`
(a closed 7-value enum — `AGE`, `INCOME_ANNUAL`, `EDUCATION_LEVEL`,
`ACADEMIC_PERCENTAGE`, `ACADEMIC_CGPA`, `RESIDENCE_STATE`, `CATEGORY`),
`operator` (`EQ`/`NEQ`/`GTE`/`LTE`/`BETWEEN`/`IN`/`NOT_IN` — the fixed
set [ELIGIBILITY_ENGINE.md](ELIGIBILITY_ENGINE.md) §3 specifies, no
free-form expression evaluation), and typed value columns
(`numeric_value`/`numeric_value_max` as `Numeric(12,2)` — never `Float`,
matching `ScholarshipDetail`'s precedent — for numeric attributes;
`text_value`/`text_values` (`JSONB`) for text/enum attributes) rather
than one generic `value` column, so a malformed attribute/operator/value
combination can be rejected in application code
(`app.eligibility.evaluator.validate_condition_shape`) before it ever
reaches the evaluation function. A `CHECK` constraint
(`ck_eligibility_conditions_has_a_value`) guards against a row with no
value at all, as a cheap database-level backstop.

**Date windows are deliberately not a supported attribute.** This
phase's kickoff lists "date windows" among the criteria types the engine
should support "provided the underlying rule has adequate structured
data." An application-opens/application-closes window is a fact about
the *opportunity* (already shown on the job/scheme's own detail page via
existing fields — `JobNotification.application_start/end`,
`ScholarshipDetail.application_opens/closes`), not something an
*applicant* answers in a Q&A form — so it was excluded from the
applicant-facing answer set rather than forced in. This is the
"integration gap disclosed, not fabricated" pattern the kickoff itself
permits (§ "If the existing domain data is insufficient, implement the
reusable engine and clearly identify the integration gap").

**Evaluability is stricter than the standard display-visibility rule.**
Every prior domain treats `verification_status IN (VERIFIED,
NEEDS_REVIEW)` plus `publication_status == PUBLISHED` as sufficient to
*display* a fact. This phase's kickoff explicitly asks that "unverified,
expired, or review-required rules must not silently produce
authoritative outcomes" — since an eligibility verdict is a claim of
fact about a real person's situation, not merely displayed content, only
`verification_status == VERIFIED` rules are ever evaluated
(`app.eligibility.service.get_evaluable_rule`). A published, verified
rule with zero conditions is also treated as not evaluable — it can't
express anything, so it's never a silent, vacuous `ELIGIBLE`.

**No `profiles` read, by design.** `app.users.models.Profile` already
holds `date_of_birth`/`qualification`/`state_id`/`district_id`/
`category` — exactly the shape a future authenticated flow could map to
this engine's answers. But no `app.auth` module exists yet (Phase 3
built identity storage only, per that phase's own scope note), so there
is no session to attach a persisted profile to. The engine is therefore
stateless: `POST /api/v1/eligibility/evaluate` takes submitted answers
directly in the request body, evaluates them, and returns a result — no
answer is read from or written to `profiles` or any other table. This
is also the more privacy-conservative choice
([PRIVACY.md](PRIVACY.md) §1's minimization principle), not merely a
consequence of missing auth.

**The pure evaluation core has zero infrastructure dependencies.**
`app.eligibility.evaluator.evaluate_rule` takes plain dataclasses in and
returns plain dataclasses out — no SQLAlchemy `Session`, no Pydantic
model, no wall-clock read. `app.eligibility.service` is the only caller,
responsible for converting ORM rows to `RuleSpec`/`ConditionSpec` and a
validated `EligibilityAnswers` Pydantic model to the plain
`Mapping[EligibilityAttribute, Decimal | str | None]` the evaluator
accepts. This is what makes "100% branch coverage on the evaluation
function" ([TESTING.md](TESTING.md) §6) tractable as a pure-unit-test
target with no database in the loop.

**Fixture geography/organization/department are shared, not
duplicated**, extending §14's identical fix: `app/eligibility/
fixtures.py` get-or-creates the same "Testland" state and "Test
Recruitment Board — Not Real" organization every other domain's
fixtures create, plus its own small, dedicated Job/Scheme/Service (not a
hard dependency on `app.jobs.fixtures`/`app.schemes.fixtures`/
`app.services.fixtures` having run), each carrying exactly one
`EligibilityRule` — together exercising every supported attribute and
operator from fixture data alone.

## 16. Phase 12 Implementation Notes: Civic AI + RAG

**No pgvector — verified unavailable in this project's actual
environment, not assumed.** [ARCHITECTURE.md](ARCHITECTURE.md) §5 and
[AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) both name `pgvector` as the
target embedding store. Checked by hand before building anything: the
local/test PostgreSQL distribution this project's own test suite uses
(`C:/civiclens-test-postgres/pgsql`, per `tests/_full_pg_utils.py`) ships
no `vector.control` file — the `pgvector` extension was never installed
into it — and this development environment has no Docker, the usual way
to get a pgvector-enabled Postgres without a manual extension build.
This phase's kickoff itself conditions pgvector on "if feasible within
the existing setup," which it explicitly is not. `ai_knowledge_chunks.
embedding` is therefore a plain `ARRAY(Float)` column, with cosine
similarity computed in Python (`app.ai.retrieval.semantic_retrieve`,
bounded to a capped candidate scan) rather than an in-database `<=>`
operator. This is disclosed as a real, current limitation — adequate at
this project's actual scale (fixture-only content; no real government
data before Phase 13) — not a claim of production-scale performance. A
`CHECK` constraint (`array_length(embedding, 1) = embedding_dimensions`)
guards against a corrupted-length vector at the database layer as a
backstop beyond the provider-side dimension check
(`app.ai.providers_openai.OpenAIEmbeddingProvider.embed`). Swapping to a
real `vector(N)` column later is a migration plus a rewrite of that one
query function — every caller's signature (`semantic_retrieve(...)  ->
list[RetrievedChunk]`) stays the same.

**`ai_knowledge_chunks` deliberately does NOT carry a real foreign
key** — the opposite choice from Phase 11's `EligibilityRule` (three
real FKs for a small, fixed entity set). Instead it uses a plain,
indexed `(entity_type, entity_id, locale)` key, following
`app.search.models.SearchDocument`'s established precedent (itself
following `VerificationRecord`/`ChangeRecord`'s precedent) rather than
Phase 11's. Two reasons, both explicit: (1) the entity-type set here is
the same open-ended "any current or future fact-bearing domain" set
`SearchDocument` already serves, not Phase 11's fixed three (jobs,
schemes, services); (2) FK'ing to `search_documents.id` specifically was
considered and rejected — `search_documents` is explicitly documented
as droppable/rebuildable at any time "with no data loss" (its own module
docstring), and cascading that drop onto every knowledge chunk would
force a costly full re-embedding (a real LLM-provider API cost) of
everything on what is meant to be a cheap, lossless operation for that
table alone.

**No `source_id`/`verification_status`/`route` columns on
`ai_knowledge_chunks`** — retrieval always `JOIN`s to `search_documents`
on the shared `(entity_type, entity_id, locale)` key to get them. This
is the trust gate, not a duplicated one: a chunk whose entity is no
longer in `search_documents` (unpublished, expired, or never re-indexed
after a status change) simply cannot be retrieved — an `INNER JOIN`
filters it out automatically, the same way `VERIFIED`/`NEEDS_REVIEW`-only
membership in `search_documents` already gates ordinary search results.
Belt-and-suspenders: `app.ai.indexing.reindex_all` also actively deletes
any `ai_knowledge_chunks` row whose key no longer appears in
`search_documents`, rather than relying on the join alone.

**Knowledge-chunk text is built from richer per-domain detail than
`search_documents` carries**, not reused verbatim from it.
`search_documents.searchable_text` is deliberately thin (a low-weight
full-text snippet, per that table's own module docstring) — real grounded
answers need an entity's fuller description and structured child rows
(requirements, benefits, fees, application methods), so
`app.ai.chunking` reads each domain's own ORM models directly (the same
established cross-module-read precedent `app.eligibility.service` and
`app.documents.service.get_required_by` already use) and formats one
deterministic plain-text chunk per entity per locale — one chunk per
entity is this phase's deliberate MVP granularity, avoiding
chunk-boundary/overlap logic a real multi-chunk-per-entity split would
need; `chunk_index` exists in the schema so that split is a future
chunking-logic change, not a migration.

**Idempotent re-indexing via content hash, not source-version
tracking.** `ai_knowledge_chunks.content_hash` (a sha256 of the built
chunk text) lets `app.ai.indexing.index_one` skip calling the embedding
provider entirely when an entity's chunk text hasn't changed since the
last index run — satisfying this phase's explicit "avoid unnecessary
embedding regeneration" cost-control requirement without needing to
separately track which `source_version_id` produced the current
content. `embedding_model`/`embedding_dimensions` are recorded per row
(not only in application config) so retrieval can filter to the
currently-configured provider identity — the "safe compatibility check"
this phase requires — without every row needing to be re-indexed the
moment `AI_EMBEDDING_MODEL` changes; old rows simply become invisible to
semantic search (never silently compared against incompatible vectors)
until re-indexed.

**No re-indexing HTTP endpoint exists.** No auth/role-check mechanism
exists anywhere in this codebase yet (verified by hand — see Phase 11's
identical finding). Per this phase's explicit "never expose an
unauthenticated destructive indexing endpoint," `reindex_all` is exposed
only as an internal service function and a manual ops script
(`scripts/reindex_ai_knowledge.py`), never a route.

## 17. Tracking + Notifications Implementation Notes (rescheduled from Phase 12)

**Real authentication was built first — this work's actual prerequisite.**
Phase 11's identical finding ("no auth/role-check mechanism exists
anywhere") was still true at the start of this work. ADR-009 (JWT
access+refresh, httpOnly cookies, email/password baseline) was already
*accepted* but never implemented. Since every requirement below depends
on real per-user ownership, implementing ADR-009 was executing an
already-approved architecture, not inventing one. `app.auth` adds
`users.email_notifications_enabled` (opt-in-only default, per
[PRIVACY.md](PRIVACY.md) §3) and one new table, `refresh_tokens`
(`user_id`, `token_hash` — SHA-256, not bcrypt, since a refresh token is
already a random secret, not a human password — `family_id`,
`expires_at`, `revoked_at`). Refresh rotation is family-scoped: replaying
an already-rotated (revoked) token revokes every token in that
`family_id`, the explicit anti-theft design in
[SECURITY.md](SECURITY.md) §2.

**`TrackedItem` uses four real nullable FKs + a `CHECK`, not a
polymorphic key — the opposite choice from `ai_knowledge_chunks`
(§16) for a deliberate reason.** The entity-reference design question
was resolved by direct analogy to two existing precedents rather than
picked arbitrarily: Phase 11's `EligibilityRule` (real FKs; small,
fixed entity set; cascade-delete is a real correctness requirement —
a dangling tracked item pointing at a deleted job is a dashboard bug,
not an acceptable trade-off) versus `ai_knowledge_chunks`/
`SearchDocument`/`ChangeRecord` (polymorphic; open-ended entity-type
set; the record is audit-trail-like and should survive entity
deletion). `TrackedItem`'s characteristics — four fixed entity types
(job/service/scheme/document; scholarships are tracked via their
parent `scheme_id`, not a fifth column, per Phase 9's scholarship-as-
scheme-specialization decision, §13), and a real dashboard-correctness
cost to a dangling reference — match the `EligibilityRule` precedent:
`job_id`/`service_id`/`scheme_id`/`document_id` (all nullable FK
`ON DELETE CASCADE`), `CHECK (num_nonnulls(...) = 1)`.

**Preventing duplicate active tracking rows required
`postgresql_nulls_not_distinct=True`, not a plain `UNIQUE`
constraint.** A naive `UNIQUE(user_id, job_id, service_id, scheme_id,
document_id)` would not actually prevent a user from tracking the same
job twice: Postgres's *default* NULL semantics treat every `NULL` as
distinct from every other `NULL`, so two rows both
`(user=X, job=Y, NULL, NULL, NULL)` would not collide under the
default constraint. Caught before implementing, not after a bug
report. `postgresql_nulls_not_distinct=True` (a Postgres 15+ feature;
confirmed available on this project's actual Postgres 16.2, and
confirmed supported by the installed SQLAlchemy 2.0.51) closes this
gap — verified directly by a dedicated duplicate-insert test, not
assumed from the option's name.

**`Notification` uses a polymorphic `(entity_type, entity_id)` pair,
no FK — matching `ChangeRecord`/`ai_knowledge_chunks`, not
`TrackedItem`.** A notification is an audit-trail-like record of an
event that happened (a deadline approached, a change was detected, an
entity disappeared) — it should remain readable in a user's inbox even
after the underlying entity or `TrackedItem` is later deleted, the
same reasoning that put `ai_knowledge_chunks` on the polymorphic side
of this decision in §16. `source_id`/`change_record_id` are real
nullable FKs with `ON DELETE SET NULL` (provenance links, safe to lose
without losing the notification itself).

**Notification deduplication is enforced at the database layer, not
just in application logic** — this phase's explicit requirement.
`UNIQUE(user_id, dedup_key)` (`uq_notifications_user_dedup_key`) is the
actual guarantee; `app.notifications.service.create_notification` uses
a Postgres `INSERT ... ON CONFLICT (user_id, dedup_key) DO NOTHING
RETURNING *` so a sweep that runs twice, or is retried after a partial
failure, silently no-ops on the second attempt (`None` return, not an
error) rather than crashing or duplicating. Dedup keys are built from
the triggering event's own stable identity — e.g.
`DEADLINE_REMINDER:{entity_type}:{entity_id}:{deadline.isoformat()}`,
`CHANGE_DETECTED:{change_record_id}:{user_id}` — never from a
timestamp or a counter, so the same underlying event can never produce
two rows no matter how many times the sweep re-runs.

**`NotificationDeliveryAttempt` exists as its own table, separate from
`Notification`, specifically so a crash between "we decided to try
sending" and "the provider responded" leaves a durable, retryable
record** — this phase's explicit "persist pending work before
delivery" requirement. `IN_APP` delivery is instantaneous by
construction (writing the `Notification` row *is* delivery for that
channel), so `create_notification` also writes a `SENT` `IN_APP`
attempt row at creation time, with nothing further to track. `EMAIL`
delivery is different: `app.notifications.delivery.deliver_pending_emails`
writes a `PENDING` attempt row and flushes it to the database *before*
calling the email provider, so a crash mid-call is recoverable rather
than silently lost. Retries are bounded by counting existing `EMAIL`
attempts against `settings.notification_delivery_max_attempts`
(default 3) — an exhausted notification simply stops being retried
(stays `FAILED`), never retried forever.

## 18. Deadline and Change-Detection Semantics (Tracking + Notifications)

**Deadlines use a fixed IST (`Asia/Kolkata`) convention, not the
server's local timezone.** `app.tracking.deadlines` treats a bare
`Date` deadline field as ending at 23:59:59 IST on the stated day
(inclusive of that day) — `deadline_end_instant`, `is_expired`, and
`time_to_deadline` are pure functions taking an explicit `now`
parameter rather than reading the wall clock internally, so their
behavior is reproducible in tests and never silently depends on the
machine's local timezone. `get_deadline_for_entity` never infers or
generates a deadline: for a `Job` it is
`max(n.application_end for n in job.notifications if
n.application_end is not None)` (the furthest-future stated deadline
across recruitment cycles — deliberately not "most recently created,"
since two `JobNotification` rows inserted in the same transaction can
share an identical `created_at` from Postgres's transaction-time
`now()`, making creation order an unreliable tiebreaker); for a
`Scheme` it is `scheme.scholarship_detail.application_closes` when
present; `Service`/`Document` currently have no structured deadline
field and always return `None` — never a guessed one.

**Change detection compares a small, named set of fields per entity
type against the most recent prior observation — never a full-row
diff, and never triggers on an unrelated field edit, a re-index, or a
reformat.** `app.tracking.change_detection.detect_changes` reuses the
`ChangeRecord`/`ChangeReviewStatus` model defined in Phase 3 (§7) and
never previously instantiated anywhere — the schema was already
correct; this phase built the first producer for it. Only
`publication_status` and `deadline` are watched (`_SUPPORTED_FIELDS`),
each entity type's real current value is compared against that exact
`(entity_type, entity_id, field)` triple's most recent prior
`ChangeRecord.new_value` — a value equal to the last-recorded one
never creates a new row, so repeated sweeps are idempotent and a field
nobody watches can never trigger a spurious notification. A new
`PENDING` `ChangeRecord` is created on any real difference, including
the first-ever observation (no prior baseline). Critically, a
`ChangeRecord` being created is *not* itself notifiable —
`generate_change_notifications` only ever considers records with
`review_status == APPROVED`. `approve_change_record`/
`reject_change_record` exist as plain internal functions (the smallest
capability a future admin-review UI would call) but are deliberately
never exposed as routes — no unauthenticated or unreviewed path can
turn a detected difference into a live notification. This is the same
trust boundary [DATA_SOURCES.md](DATA_SOURCES.md) §4 describes for
Phase 13's ingestion pipeline, applied here ahead of that pipeline
existing.

## 19. Admin Intelligence Center Implementation Notes (Phase 13, review/approval half only)

**No new table, no new migration.** Every model this phase's
`app.admin` module touches already existed: `ChangeRecord`/
`VerificationRecord`/`Source`/`SourceVersion` (§7, Phase 3) and each
domain's own `verification_status`/`last_verified_at` columns (§9-§14).
`approve_change_record`/`reject_change_record` (§17-18, written by
Tracking + Notifications as unexposed internal functions specifically
anticipating this phase) are now wrapped by `app.admin.service` and
exposed as routes behind RBAC. This phase adds exactly one new runtime
concept — `require_role` (`app.auth.dependencies`) — and it needed no
schema change: `users.role` (`UserRole`: `user`/`editor`/`admin`) has
existed since ADR-009/Phase-13-of-Tracking-and-Notifications; nothing
before this phase ever *checked* it beyond "is this a real
authenticated user."

**Approving a `ChangeRecord` means "notify trackers," not "publish" —
worth stating precisely, since the word "approve" invites the wrong
reading.** No staging table exists in this codebase (that is the
unbuilt ingestion-pipeline half of this phase, §ROADMAP.md). By the
time a `ChangeRecord` exists at all, `detect_changes` (§18) has already
observed the entity's *current, live* database value — the fact
already changed before any human looked at it. What `app.admin.
approve_change_record` actually gates is solely whether
`generate_change_notifications` (Tracking + Notifications) is allowed
to notify trackers about that already-live change. This is a real,
useful trust boundary (an editor confirms a detected diff is
legitimate/worth surfacing before anyone is told about it) — it is
just not the "nothing becomes public without approval" gate
[DATA_SOURCES.md](DATA_SOURCES.md) describes for the full pipeline,
and this document does not overstate it as such.

**Valid-transition enforcement, with idempotent re-decision as the
deliberate exception.** A `ChangeRecord` already `REJECTED` cannot be
approved, and vice versa (`InvalidChangeRecordTransitionError`, mapped
to `409 Conflict`) — a decision, once made, is not silently reversed by
a second call. Re-issuing the *same* decision (approving an
already-`APPROVED` record) is instead treated as an idempotent retry,
not an error — the same "make approval and notification creation
idempotent" requirement this phase's kickoff states explicitly,
resolved by distinguishing "retry of the same decision" from "attempt
to reverse a prior decision" rather than picking one blanket rule for
both.

**Verification writes span two rows in one transaction, and are never
allowed to drift apart.** `submit_verification` creates a
`VerificationRecord` (the evidence: `source_id`, `status`,
`verified_by`, `verified_at` — `source_id` is `nullable=False` at the
column level already, and this function additionally checks the id
resolves to a real `Source` row before proceeding, rather than letting
a bad id surface as an opaque FK-violation 500) *and* sets the target
entity's own `verification_status`/`last_verified_at` to match, in the
same function, then re-syncs that entity's search-index membership via
its domain's own already-existing `sync_*_search_index` function
(§9-§14) — the same visibility mechanism every other domain already
relies on, not a new one invented for this phase.

**The verification queue and per-entity-type dispatch are Python-side,
not a UNION query — and dispatch uses explicit if/elif, not a dict of
model types.** The four entity tables (`jobs`, `schemes`, `services`,
`civic_documents`) have no common base table to query across in one
statement, so `get_verification_queue` queries each in full (filtered
by `verification_status`) and combines/sorts/paginates the results in
Python — acceptable at this project's actual fixture-only scale
(CLAUDE.md rule 12), not a claim of query efficiency at real-data
volume. Every function that needs a concretely-typed ORM object
(`session.get(SomeModel, id)`, `select(SomeModel).where(...)`)
dispatches with explicit `if entity_type == ...: elif ...` branches
rather than a `dict[AdminEntityType, type[...]]` lookup — the same fix
this codebase already applied once before, in `app.ai.chunking`'s
`_BUILDERS` table (Phase 12): a dict keyed by an enum whose values are
themselves types (or callables with different per-branch signatures)
loses its specific type information to mypy, which falls back to the
ORM `Base` class and then every attribute access on it errors.
