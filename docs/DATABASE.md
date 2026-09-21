# CivicLens — Database Architecture

Primary datastore: **PostgreSQL** (see [ADR-004](ADR/ADR-004-postgresql.md)).
This document defines the core entities, their purpose, and relationships.
It is a design reference for Phase 3 — **no migrations exist yet.**

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

### 2.1 Geography (state-agnostic — see [ARCHITECTURE.md](ARCHITECTURE.md) §3)
- **states** — id, name, code, status (`active`/`planned`)
- **districts** — id, state_id, name, code
- **constituencies** — id, state_id, type (`assembly`/`parliamentary`),
  name, district_id (nullable, some constituencies span districts)

### 2.2 Institutions
- **organizations** — recruiting boards, universities, corporations (e.g.,
  APPSC, TSPSC) — id, name, type, state_id (nullable for national bodies)
- **departments** — government departments issuing schemes/services — id,
  name, organization_id (nullable), state_id

### 2.3 Opportunities
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

### 2.4 Requirements & Eligibility
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

### 2.5 Time
- **deadlines** — id, entity_type, entity_id, stage (`notification`,
  `application_open`, `application_close`, `correction_window`,
  `admit_card`, `exam_date`, `answer_key`, `result`, custom), date,
  source_id, is_estimated (bool — some dates are provisional)

### 2.6 People & Elections (politically neutral — see
[DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §5)
- **representatives** — id, name, role (`MLA`/`MP`/`Minister`/`CM`), party,
  constituency_id (nullable for state-wide roles), term_start, term_end,
  source_id
- **elections** — id, constituency_id, election_date, type, source_id
- **election_results** — id, election_id, candidate_name, party, votes,
  outcome, source_id

### 2.7 Provenance (see [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) for full model)
- **sources** — id, url, title, organization, source_type, published_date,
  retrieved_date
- **source_versions** — id, source_id, content_hash/snapshot_ref,
  captured_at
- **verification_records** — id, entity_type, entity_id, source_id, status
  (`VERIFIED`/`NEEDS_REVIEW`/`EXPIRED`/`UNVERIFIED`), verified_by,
  verified_at, review_due_at
- **change_records** — id, entity_type, entity_id, field, old_value,
  new_value, detected_at, source_version_id, review_status, reviewed_by,
  applied_at

### 2.8 Users & Personalization
- **users** — id, email (unique), password_hash (nullable if OAuth-only),
  role (`user`/`editor`/`admin`), created_at — minimal fields, see
  [PRIVACY.md](PRIVACY.md) for data minimization
- **profiles** — id, user_id, explicitly-provided attributes used for
  eligibility/personalization (age/DOB, qualification, state/district,
  category) — every field optional, nothing inferred
- **saved_items** — id, user_id, entity_type, entity_id, saved_at
- **tracking_items** — id, user_id, entity_type, entity_id, created_at,
  active (bool)
- **notifications** — id, user_id, tracking_item_id (nullable),
  change_record_id (nullable), message, read_at, created_at

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
