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

**Phase 0 — Architecture & Governance.** This repository currently
contains product vision, architecture, and governance documentation only.
No application code, database migrations, or data have been implemented
yet. See [docs/ROADMAP.md](docs/ROADMAP.md) for the phased plan and
[CLAUDE.md](CLAUDE.md) for the engineering rules that govern this project.

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
