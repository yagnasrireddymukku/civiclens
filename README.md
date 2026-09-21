# CivicLens

**India's Personal Public-Information Intelligence Platform**

Search → Understand → Check → Prepare → Act → Track

CivicLens helps citizens discover public information (government jobs,
exams, services, schemes, scholarships, representatives, elections,
documents), understand what it means for them, check eligibility
deterministically, find required documents and next steps, and track
deadlines — all grounded in verified, source-attributed data. See
[docs/PRODUCT.md](docs/PRODUCT.md) for the full product vision.

## Status

**Phase 1 — Monorepo Foundation.** Phase 0 (product vision, architecture,
and governance documentation) is complete — see [docs/](docs/) and
[CLAUDE.md](CLAUDE.md). This phase adds the repository skeleton, tooling,
and CI, with **no business functionality**: no jobs/schemes/eligibility/
search/AI/tracking, no domain database schema, and no real government data.
See [docs/ROADMAP.md](docs/ROADMAP.md) for the phased plan.

## Project Structure

```
civiclens/
├── apps/
│   ├── web/           Next.js + TypeScript frontend
│   └── api/            FastAPI backend (Python, managed by uv)
├── packages/
│   ├── types/          Shared TypeScript types (hand-written until
│   │                    OpenAPI-generated types land, docs/API.md §10)
│   ├── validation/      Shared Zod validation schemas
│   ├── ui/              Reserved for a future shared UI package — empty
│   │                    until apps/web has a real component-reuse need
│   │                    (docs/FRONTEND.md §10)
│   └── config/          Shared tsconfig base
├── scripts/             Repo-level dev scripts (e.g. check-setup.mjs)
├── docs/                 Architecture, governance, and roadmap (Phase 0)
└── .github/workflows/    CI
```

## Prerequisites

- Node.js >= 20 ([.nvmrc](.nvmrc) pins 20)
- pnpm (`npm install -g pnpm`, or via [Corepack](https://pnpm.io/installation#using-corepack) if you have permission to enable it)
- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) for the backend (`uv sync` will download a
  matching Python automatically if needed)

Run `pnpm check-setup` (or `node scripts/check-setup.mjs`) to verify these
are all on your `PATH`.

## Setup

```bash
# Frontend + shared packages
pnpm install
cp apps/web/.env.example apps/web/.env.local

# Backend
cd apps/api
uv sync
cp .env.example .env
cd ../..
```

## Development

```bash
# Frontend (http://localhost:3000)
pnpm dev

# Backend, in a separate terminal (http://localhost:8000)
cd apps/api && uv run uvicorn app.main:app --reload
```

With both running:

- `http://localhost:3000` redirects to `http://localhost:3000/en` (or
  `/te` — see [docs/FRONTEND.md](docs/FRONTEND.md) §7) and shows a live
  API status pulled from `GET /api/v1/health`, proving the frontend/
  backend/shared-package wiring works. It is not the product homepage
  yet — that starts in [docs/ROADMAP.md](docs/ROADMAP.md) Phase 6.
- `http://localhost:3000/en/dev/design-system` is the internal design
  system showcase (development only — it 404s in a production build; see
  [docs/FRONTEND.md](docs/FRONTEND.md) §9).

## Testing, Linting, Type Checking

```bash
# From the repo root (frontend + shared packages)
pnpm build       # also generates Next.js's route types; run before typecheck
pnpm lint
pnpm typecheck
pnpm test
pnpm format:check   # or `pnpm format` to fix

# Backend
cd apps/api
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs all of the
above on every pull request.

## Initial Scope

- **Geography**: Andhra Pradesh + Telangana (architecture is state-agnostic
  — see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §3)
- **Languages**: English, Telugu
- **Domains**: Government Jobs, Exams, Services, Schemes, Scholarships,
  Public Representatives, Elections, Documents & Certificates, Eligibility,
  Calculators, Civic AI, Tracking & Alerts

## Documentation

| Area | Document |
|---|---|
| Product vision | [docs/PRODUCT.md](docs/PRODUCT.md) |
| Product requirements | [docs/PRODUCT_REQUIREMENTS.md](docs/PRODUCT_REQUIREMENTS.md) |
| Architecture overview | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| System / infra architecture | [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) |
| Database | [docs/DATABASE.md](docs/DATABASE.md) |
| API | [docs/API.md](docs/API.md) |
| Frontend | [docs/FRONTEND.md](docs/FRONTEND.md) |
| AI / RAG architecture | [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) |
| Eligibility engine | [docs/ELIGIBILITY_ENGINE.md](docs/ELIGIBILITY_ENGINE.md) |
| Data sources & ingestion | [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) |
| Data governance | [docs/DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md) |
| Search | [docs/SEARCH.md](docs/SEARCH.md) |
| SEO | [docs/SEO.md](docs/SEO.md) |
| Security | [docs/SECURITY.md](docs/SECURITY.md) |
| Privacy | [docs/PRIVACY.md](docs/PRIVACY.md) |
| Testing | [docs/TESTING.md](docs/TESTING.md) |
| Observability | [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md) |
| Monetization | [docs/MONETIZATION.md](docs/MONETIZATION.md) |
| Deployment | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Roadmap | [docs/ROADMAP.md](docs/ROADMAP.md) |
| Architecture Decision Records | [docs/ADR/](docs/ADR/README.md) |

## Core Principle

CivicLens never treats an LLM as the source of truth. The hierarchy is:

```
OFFICIAL SOURCE → VERIFIED STRUCTURED DATA → CIVICLENS APPLICATION → AI EXPLANATION
```

Full doctrine: [docs/DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md).

## Contributing

Read [CLAUDE.md](CLAUDE.md) before making any change.
