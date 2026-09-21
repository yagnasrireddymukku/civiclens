# CivicLens — Data Governance & Source-of-Truth Doctrine

This is the most important document in the repository. Every engine,
migration, ingestion pipeline, and AI feature must comply with it.

## 1. The Hierarchy

```
OFFICIAL / AUTHORITATIVE SOURCE
        ↓
VERIFIED STRUCTURED DATA          (CivicLens database, with provenance)
        ↓
CIVICLENS APPLICATION              (API, search, UI)
        ↓
AI EXPLANATION                     (synthesizes, never originates, facts)
```

Never acceptable: `INTERNET → LLM → CLAIMED FACT`.

The AI layer ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)) may only ground its
output in what already exists in "Verified Structured Data" (or explicitly
approved documents). It cannot promote its own inference to a fact.

## 2. Four Kinds of Content, Never Conflated

1. **Authoritative source** — the government notification, gazette,
   department portal, or official press release itself.
2. **Structured CivicLens data** — our normalized representation of #1,
   always carrying provenance (§3).
3. **AI-generated explanation** — a plain-language synthesis of #2, always
   presented as explanation, never as an independent fact, always with
   citations back to #2/#1.
4. **User-generated content** (future, not in v1) — must be visually and
   structurally distinct from #1–#3 if ever introduced.

## 3. Provenance: Required Fields

Every fact-bearing entity must be traceable to a `sources` record carrying:

| Field | Purpose |
|---|---|
| source URL | where the fact came from |
| source title | human-readable reference |
| source organization | which authority published it |
| source type | e.g. official notification, gazette, portal page |
| published date | when the source published it (if available) |
| retrieved date | when CivicLens ingested it |
| last verified date | when a human/process last confirmed it still holds |
| verification status | see §4 |
| content/version identifier | which snapshot of the source this reflects |
| relevant entity | what CivicLens record this supports |
| expiration/review date | when this fact should be re-checked, if applicable |

See [DATABASE.md](DATABASE.md) §2.7 for the schema
(`sources`, `source_versions`, `verification_records`).

## 4. Verification Statuses

- **VERIFIED** — confirmed against the authoritative source within its
  review window.
- **NEEDS_REVIEW** — a change was detected, or the review window has
  lapsed; shown to users with a visible caveat, not hidden.
- **EXPIRED** — the fact is time-bound and that time has passed (e.g., an
  application window); the UI must reflect this, not just the raw date.
- **UNVERIFIED** — ingested but not yet confirmed; must never be presented
  as equivalent to VERIFIED.

Any page displaying time-sensitive public information exposes
**"Last verified: DATE"** and a link to the source. This is a hard product
requirement ([PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) NFR-T2), not
a nice-to-have.

## 5. Political Neutrality

CivicLens may present factual information about representatives, parties,
constituencies, and elections. It must never:

- rank or score representatives or parties ("best/worst")
- recommend a candidate or a vote
- infer or store a user's political preference
- use language that persuades rather than informs

Representative/election data is dated, sourced, and factual — nothing more.
This is enforced at the data model level (no "rating" or "score" fields
exist on `representatives`/`elections`) and at the AI layer (the AI system
prompt and retrieval scope forbid persuasive or comparative political
framing — see [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) §5).

## 6. Absolute Prohibitions

The system — including any AI component, any seed/fixture data, and any
contributor — must never invent:

- government schemes, jobs, or exams that do not exist
- eligibility requirements not present in an authoritative source
- dates (application windows, exam dates, results)
- salaries, stipends, or award amounts
- official URLs
- representatives, election results, or vote counts
- application procedures or document requirements

If a fact cannot be verified, the system says so. An honest "we could not
verify this" is a correct product outcome; a fabricated fact is a defect
regardless of how plausible it looks.

## 7. Development-Time Rule

**No fake or invented government data may be created at any phase**,
including for testing, demos, or seed data. Test fixtures must be
clearly-fictional (e.g., "Test Scheme — Not Real", obviously fake IDs like
`ZZ`/`Testland`) so they can never be mistaken for real civic information
if a fixture leaks into a non-test environment. See [TESTING.md](TESTING.md)
§fixtures and [CLAUDE.md](../CLAUDE.md).

## 8. Ownership & Change Control

- Publishing new structured data or approving a detected change requires
  human review (see [DATA_SOURCES.md](DATA_SOURCES.md) §4) at v1 — no
  autonomous publish path exists.
- `change_records` (see [DATABASE.md](DATABASE.md) §2.7) preserve the prior
  value, the detected new value, who/what reviewed it, and when it was
  applied — full audit trail, no silent overwrites.
