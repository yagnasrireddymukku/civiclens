# Architecture Decision Records

ADRs capture significant, hard-to-reverse architectural decisions: the
context, the decision, alternatives considered, and consequences. They are
append-only history — a superseded decision gets a new ADR that supersedes
the old one; existing ADRs are not rewritten.

## Format

Each ADR has: Context, Decision, Alternatives Considered, Consequences,
Status (`Proposed` / `Accepted` / `Superseded by ADR-xxx` / `Deprecated`).

## Index

| ADR | Title | Status |
|---|---|---|
| [001](ADR-001-monorepo-architecture.md) | Monorepo architecture | Accepted |
| [002](ADR-002-nextjs-frontend.md) | Next.js frontend | Accepted |
| [003](ADR-003-fastapi-backend.md) | FastAPI backend | Accepted |
| [004](ADR-004-postgresql.md) | PostgreSQL as primary database | Accepted |
| [005](ADR-005-search-architecture.md) | Search architecture | Accepted |
| [006](ADR-006-ai-rag-architecture.md) | AI / RAG architecture | Accepted |
| [007](ADR-007-eligibility-engine.md) | Eligibility engine architecture | Accepted |
| [008](ADR-008-source-verification-architecture.md) | Source / verification architecture | Accepted |
| [009](ADR-009-authentication-strategy.md) | Authentication strategy | Accepted |
| [010](ADR-010-deployment-architecture.md) | Deployment architecture | Accepted |

All ADRs in this initial set are proposed and accepted together as part of
the Phase 0 architecture checkpoint, pending explicit product-owner
approval before Phase 1 implementation begins.
