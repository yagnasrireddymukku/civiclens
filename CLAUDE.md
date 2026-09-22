# CLAUDE.md — CivicLens Engineering Rules

This file governs how Claude (and any contributor) works in this
repository. It does not replace the documents in `docs/` — it is the
enforcement summary. When in doubt, the linked document is authoritative.

## Current Phase

Phases 0–5 are complete and approved (architecture/governance, monorepo
foundation, database + core data model, frontend design system, search
infrastructure). The project is now in **Phase 6 — Government Jobs**
(see [docs/ROADMAP.md](docs/ROADMAP.md)), the first real domain module.
Real government data still does not exist and must not be added until
the project explicitly enters a real-data phase (Phase 13, per
[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)) — Phase 6 uses a single,
clearly-synthetic fixture job only
(see [docs/DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md) §7).

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
