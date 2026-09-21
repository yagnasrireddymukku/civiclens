# CivicLens — Data Ingestion & Source Architecture

This document defines how CivicLens will bring authoritative public
information into the system. **No ingestion pipeline is built yet** — this
is the target architecture for Phase 13 (Admin Intelligence Center) onward,
though the `sources`/`verification_records` schema exists from Phase 3
because every domain table depends on it.

## 1. Potential Future Sources

- Official government websites and department portals
- Official recruitment notification boards (e.g., APPSC, TSPSC, SSC
  regional units)
- Official gazettes and public-record repositories
- Public APIs where legally available (e.g., open government data portals)

CivicLens does **not** assume every website may be scraped. Each source is
onboarded individually with an explicit legal/compliance check (§2) before
any automated fetching begins.

## 2. Legal & Ethical Constraints (per-source checklist)

Before any source is added to the ingestion allowlist:
1. Check `robots.txt` and the site's terms of service for scraping/reuse
   restrictions.
2. Prefer official APIs/open-data feeds over scraping where they exist.
3. Respect rate limits — ingestion must be a well-behaved client (bounded
   concurrency, backoff, identifying user agent).
4. Respect copyright/licensing — store what is factually necessary
   (dates, numbers, structured facts) with attribution; do not
   republish entire copyrighted documents verbatim beyond fair use.
5. Attribute the source clearly on every derived page (see
   [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §3–4).
6. Log the decision (source name, legal basis, constraints) so it is
   auditable — this becomes part of the source's onboarding record.

A source that fails this checklist is not onboarded, regardless of how
useful its data would be.

## 3. Ingestion Pipeline (target architecture)

```
SOURCE → FETCH → EXTRACT → NORMALIZE → VALIDATE → CHANGE DETECT
       → REVIEW (human) → PUBLISH → INDEX
```

| Stage | Responsibility |
|---|---|
| FETCH | Retrieve raw content from an allowlisted source, respecting §2; store a `source_version` snapshot |
| EXTRACT | Pull structured fields from raw content (HTML/PDF parsing, manual entry tools for low-volume sources) |
| NORMALIZE | Map extracted fields onto CivicLens schema (dates, IDs, entity references) |
| VALIDATE | Schema/type validation, referential integrity, plausibility checks (e.g., a date range makes sense) |
| CHANGE DETECT | Diff against current published state; produce a `change_record` when a value differs (§4) |
| REVIEW | A human reviewer (editor/admin role) approves or rejects the proposed publish/change |
| PUBLISH | Approved data is written to the live tables |
| INDEX | Search index and AI retrieval embeddings are refreshed for affected entities |

Ingestion runs as a **separate module/service** (`services/ingestion`, see
[ARCHITECTURE.md](ARCHITECTURE.md) §6) from the public-facing API. It only
ever writes to staging/change tables directly — never to published domain
tables without passing REVIEW. This is enforced architecturally (separate
DB roles/permissions), not just by convention.

## 4. Human-in-the-Loop Requirement (v1)

At v1, **no ingestion path publishes autonomously.** Every new record and
every detected change surfaces in an admin review queue
(Phase 13 — Admin Intelligence Center) and requires explicit approval by an
`editor`/`admin` user before it becomes visible to the public or feeds the
AI/search layers. Autonomous publish is a possible future optimization for
narrow, high-confidence source types, and would require its own ADR and a
demonstrated accuracy track record — it is out of scope until then.

## 5. Change Detection (see also [DATABASE.md](DATABASE.md) §2.7)

Example: an official source changes an application deadline from
20 October to 27 October. Target behavior:

1. A scheduled or triggered re-fetch detects the source content differs
   from the last `source_version`.
2. A `change_record` is created: entity, field, old value, new value,
   detected_at, source_version reference.
3. The prior value is preserved (never overwritten in place before review).
4. Affected entities are flagged `NEEDS_REVIEW`
   ([DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §4).
5. An admin reviews and approves/rejects.
6. On approval: structured data updates, search re-indexes the entity,
   and any users tracking the entity receive a notification
   ([DATABASE.md](DATABASE.md) §2.8 `notifications`).

## 6. Source Types & Cadence (design guidance, not a commitment)

| Source type | Example | Expected change frequency | Review priority |
|---|---|---|---|
| Recruitment notification | APPSC/TSPSC job notice | Once, then occasional corrigenda | High — dates are time-critical |
| Scheme/service page | Department scheme portal | Infrequent | Medium |
| Election/representative record | State election commission | Rare, event-driven | Medium |
| Scholarship portal | State/central scholarship site | Seasonal | High during application season |

## 7. What Is Explicitly Deferred

- Fully automated, unattended ingestion (§4)
- OCR/document-parsing pipelines for scanned notifications
- Multi-source cross-validation/consensus scoring
- Any ingestion of non-official sources (news aggregators, social media) as
  a fact source — these may only ever inform an editor's manual review, and
  are never treated as authoritative under
  [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §1.
