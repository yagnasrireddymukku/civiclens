# ADR-010: Deployment Architecture

## Status
Accepted

## Context
CivicLens needs a production deployment path that is reliable and secure
without the operational burden of orchestration platforms unjustified at
current scale ([CLAUDE.md](../../CLAUDE.md): no Kubernetes unless
documented need).

## Decision
Containerize both apps (Docker). Deploy the Next.js frontend to a
platform purpose-built for it (e.g., Vercel) to get edge caching, image
optimization, and ISR for free — directly benefiting
[SEO.md](../SEO.md)/Core Web Vitals goals. Deploy the FastAPI backend as a
container on a managed container platform (e.g., a single service on
Fly.io / Render / AWS ECS Fargate — final vendor selection is an
infrastructure decision made in [DEPLOYMENT.md](../DEPLOYMENT.md), not
fixed here) with a managed PostgreSQL instance (e.g., RDS/Neon/Supabase
Postgres). No Kubernetes, no service mesh, no message broker at this stage.
Local development uses Docker Compose to run API + Postgres together.

## Alternatives Considered
- **Kubernetes**: rejected — orchestration overhead (cluster ops, YAML
  surface area, networking complexity) is unjustified for one backend
  service and one database at MVP scale.
- **Fully serverless backend (e.g., Lambda-per-endpoint)**: rejected — cold
  starts and connection-pooling complexity against Postgres, plus a poor
  fit for a modular-monolith FastAPI app; revisit only for specific
  bursty/independent workloads (e.g., ingestion jobs) if ever split out.
- **Single monolithic VM (no containers)**: rejected — containers give
  reproducible builds and a clean local/prod parity without committing to
  orchestration complexity.

## Consequences
- Frontend and backend can scale and deploy independently, matching their
  different traffic/release patterns (frontend is read-heavy/cacheable;
  backend handles auth, writes, AI calls).
- Environment parity (dev/staging/prod) is achieved via the same container
  image promoted across environments plus environment-specific config —
  not separate builds per environment.
- A future extraction of a module (e.g., ingestion) into its own deployable
  is straightforward since it is already a separate directory/package
  under the modular monolith ([ARCHITECTURE.md](../ARCHITECTURE.md) §1, §6).
- Full topology, environments, and CI/CD pipeline detailed in
  [DEPLOYMENT.md](../DEPLOYMENT.md).
