# CLAUDE.md — CivicLens Engineering Rules

This file governs how Claude (and any contributor) works in this
repository. It does not replace the documents in `docs/` — it is the
enforcement summary. When in doubt, the linked document is authoritative.

## Current Phase

Phases 0–12 are complete and approved (architecture/governance,
monorepo foundation, database + core data model, frontend design
system, search infrastructure, government jobs, government services,
government schemes, scholarships & education opportunities, documents
& certificates, the eligibility engine, Civic AI + RAG). Scholarships
(Phase 9) are a `Scheme` specialization, not a new domain module;
Documents (Phase 10), Eligibility (Phase 11), and Civic AI (Phase 12)
*are* new domain modules (`app.documents`/`CivicDocument`,
`app.eligibility`/`EligibilityRule`, `app.ai`/`KnowledgeChunk`) — see
[docs/ROADMAP.md](docs/ROADMAP.md)'s Phase 9/10/11/12 entries and
[docs/DATABASE.md](docs/DATABASE.md) §13/§14/§15/§16 for all four
architectural decisions. **Civic AI does not use pgvector** — verified
unavailable in this project's actual local/test Postgres distribution
and development environment (no Docker); embeddings are stored as plain
float arrays with Python-side cosine similarity instead, a disclosed
deviation from ADR-006's aspiration (see
[docs/DATABASE.md](docs/DATABASE.md) §16). Tracking + Notifications
(originally planned as Phase 12, rescheduled) is also now realized —
real JWT cookie authentication (`app.auth`, ADR-009), a tracking module
(`app.tracking`/`TrackedItem`), and a notifications module
(`app.notifications`/`Notification`) — see the "Tracking +
Notifications" entry in [docs/ROADMAP.md](docs/ROADMAP.md) (placed
after Phase 12, still without its own phase number: this document does
not guess at a sequencing decision that belongs to explicit
product-owner approval) and [docs/DATABASE.md](docs/DATABASE.md)
§17-18. Its commits use a `tracking-notifications:` prefix rather than
a `phase-N:` one for the same reason.

**Phase 13 — Admin Intelligence Center — is now partially realized.**
Change-detected notifications, wired and tested by Tracking +
Notifications but previously gated on a `ChangeRecord.review_status`
nothing could set, can now actually be set: `app.admin` adds a
`require_role`-gated (`app.auth.dependencies`) review console —
listing and approving/rejecting `ChangeRecord`s (which then calls the
existing notification generator), and submitting `VerificationRecord`
decisions that update an entity's own `verification_status` and
re-sync its search-index membership. **This is only half of this
phase's original sketch.** The other half — `services/ingestion/`,
live source fetching, and per-source legal-checklist onboarding —
remains entirely unbuilt, per this phase's own explicit exclusion of
"uncontrolled web scraping or automatic publication." See
[docs/ROADMAP.md](docs/ROADMAP.md)'s Phase 13 entry for the full
scope-difference note and [docs/DATABASE.md](docs/DATABASE.md) §19.

One feature, originally planned as Phase 9 (Public Representatives +
Elections), remains rescheduled — its scope is unchanged but it has no
new phase number yet; see the rescheduling note in
[docs/ROADMAP.md](docs/ROADMAP.md) after the Phase 9 entry (the Civic
AI + RAG feature's own earlier "rescheduled from Phase 11" placeholder
is likewise resolved — it is Phase 12, realized). The project is now
awaiting approval to begin its next phase (the ingestion-pipeline half
of Phase 13, or Representatives + Elections). Real government data
still does not exist and must not be added until the project explicitly
completes that ingestion-pipeline half (still Phase 13, per
[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) — the review console
alone does not satisfy that gate, since it has no fetch step to gate)
— every domain module built so far uses clearly-synthetic fixtures
only, gated to `local`/`test` environments (see
[docs/DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md) §7).

## Non-Negotiable Rules

1. **Inspect before changing.** Read the relevant code/docs before editing.
   Never assume file contents or existing structure.
2. **Plan before implementing.** For anything beyond a trivial change,
   state the approach before writing code.
3. **Never invent factual public information.** No schemes, jobs, exams,
   eligibility rules, dates, salaries, URLs, representatives, or election
   results may be fabricated — not in code, not in docs, not in fixtures
   presented as real. See [docs/DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md).
4. **Never fabricate sources or URLs.** If a source can't be verified, say
   so — do not guess a plausible-looking one.
5. **Never treat AI output as authoritative data.** The LLM explains
   verified structured data; it does not originate facts or eligibility
   verdicts. See [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md),
   [docs/ELIGIBILITY_ENGINE.md](docs/ELIGIBILITY_ENGINE.md).
6. **Preserve source provenance.** Any table or feature holding a public
   fact must carry a path to a `source` record and verification status.
   See [docs/DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md).
7. **Test every feature.** Deterministic logic (eligibility, calculators)
   requires deterministic unit tests. See [docs/TESTING.md](docs/TESTING.md).
8. **Do not break existing functionality.** Run relevant tests before
   considering a change complete.
9. **Do not change frozen architecture without approval.** The decisions in
   [docs/ADR/](docs/ADR/README.md) are accepted; changing one requires a
   new ADR and explicit sign-off, not a silent deviation.
10. **Keep modules separated by responsibility.** Respect the modular-
    monolith boundaries in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §1,
    §6 — no cross-module reach-around into another domain's internals.
11. **Prefer simple, maintainable architecture.** No microservices,
    Kubernetes, message buses, or extra databases without a documented,
    approved reason (a new ADR).
12. **Avoid premature optimization.** Build for the current phase's
    requirements, not hypothetical future scale.
13. **Avoid unnecessary dependencies.** Justify any new dependency against
    what's already in the stack.
14. **Never expose secrets.** No credentials, API keys, or tokens in code,
    logs, or commit history.
15. **Never commit `.env` files containing secrets.** Use `.env.example`
    with placeholder values only.
16. **Update documentation after architecture changes.** A PR that changes
    architecture without a corresponding `docs/` update is incomplete.
17. **Keep migrations reversible where practical.** Every Alembic migration
    should have a working `downgrade`.
18. **Maintain accessibility.** WCAG 2.2 AA is a floor, not a stretch goal,
    per [docs/PRODUCT_REQUIREMENTS.md](docs/PRODUCT_REQUIREMENTS.md).
19. **Maintain SEO.** No feature should regress metadata, canonical URLs,
    or crawlability without a documented reason.
20. **Maintain security.** Every new endpoint gets input validation,
    authz checks, and rate-limit consideration per
    [docs/SECURITY.md](docs/SECURITY.md).
21. **Maintain auditability.** Factual changes go through `change_records`;
    nothing silently overwrites published data.
22. **Ask for approval before major architectural changes.** This includes
    new dependencies that shape the architecture, schema redesigns, and
    anything touching the source-of-truth doctrine.

## Political Neutrality

Representative/election features present dated, sourced facts only — no
ranking, scoring, recommendation, or persuasive framing. See
[docs/DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md) §5.

## Where to Look

| Question | Document |
|---|---|
| What is CivicLens trying to be? | [docs/PRODUCT.md](docs/PRODUCT.md) |
| What must a feature do? | [docs/PRODUCT_REQUIREMENTS.md](docs/PRODUCT_REQUIREMENTS.md) |
| How is the system structured? | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) |
| What's the schema? | [docs/DATABASE.md](docs/DATABASE.md) |
| What are the API conventions? | [docs/API.md](docs/API.md) |
| How does search work? | [docs/SEARCH.md](docs/SEARCH.md) |
| How does the AI layer work? | [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) |
| How does eligibility work? | [docs/ELIGIBILITY_ENGINE.md](docs/ELIGIBILITY_ENGINE.md) |
| How is data sourced and verified? | [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md), [docs/DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md) |
| What are the security/privacy rules? | [docs/SECURITY.md](docs/SECURITY.md), [docs/PRIVACY.md](docs/PRIVACY.md) |
| How do we test this? | [docs/TESTING.md](docs/TESTING.md) |
| What's next? | [docs/ROADMAP.md](docs/ROADMAP.md) |
| Why was X decided this way? | [docs/ADR/](docs/ADR/README.md) |

## Git Workflow

- Meaningful, phase-scoped commits (e.g., `phase-1: establish monorepo
  foundation`). No giant unrelated commits.
- Before every commit: inspect `git diff`, run relevant tests, verify no
  secrets, verify documentation is current, summarize the change.
- Never force-push or rewrite history unless explicitly instructed.
