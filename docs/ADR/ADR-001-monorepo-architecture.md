# ADR-001: Monorepo Architecture

## Status
Accepted

## Context
CivicLens has a frontend, a backend, shared types, and (later) an ingestion
service. These need to evolve together, especially the API contract between
frontend and backend, and share tooling/config.

## Decision
Use a single monorepo (`apps/web`, `apps/api`, `packages/*`,
`services/ingestion`, `infra/`, `docs/`). JS/TS packages use **pnpm
workspaces**; the Python API uses **Poetry or uv** for its own dependency
management. No monorepo build orchestrator (Turborepo/Nx) at MVP — there is
one real frontend app and one real backend app, so the coordination problem
that tools like Turborepo solve doesn't yet exist. Introduce one only when
there are multiple JS apps/packages with real build-graph complexity.

## Alternatives Considered
- **Polyrepo** (separate frontend/backend/ingestion repos): rejected —
  adds cross-repo versioning overhead and PR coordination cost for a small
  team building a tightly-coupled product surface at this stage.
- **Turborepo/Nx from day one**: rejected as premature — see
  [CLAUDE.md](../../CLAUDE.md) "avoid unnecessary dependencies." Revisit
  when there are 3+ JS packages/apps with real shared build steps.
- **Modular monolith as a single Python/JS app** (no separation of
  frontend/backend): rejected — Next.js and FastAPI are genuinely different
  runtimes; forcing them into one deployable would fight both frameworks.

## Consequences
- Single source of truth for API contracts (OpenAPI schema generated from
  FastAPI, consumed by `packages/shared-types`).
- One CI pipeline can run frontend + backend checks together on a PR.
- Slightly more initial repo-structure setup than a single-app repo, offset
  by avoiding cross-repo release coordination later.
