# ADR-003: FastAPI Backend

## Status
Accepted

## Context
The backend must serve a REST API, run deterministic eligibility logic,
host the AI/RAG orchestration layer, and (later) an ingestion pipeline.
Python has the strongest ecosystem for the AI/RAG and data-processing
pieces of this product.

## Decision
Use **FastAPI** (Python 3.12+) as a modular monolith
(see [ARCHITECTURE.md](../ARCHITECTURE.md) §1), with **SQLAlchemy 2.0** for
the ORM and **Alembic** for migrations, **Pydantic v2** for request/response
and internal data validation.

## Alternatives Considered
- **Django/DRF**: rejected — heavier batteries-included framework than
  needed; FastAPI's async support and native OpenAPI generation better fit
  an API-first, type-safe contract with the Next.js frontend.
- **Node.js backend (e.g., NestJS)**: rejected — would unify the language
  with the frontend, but the AI/RAG, data-validation, and future
  data-science/ingestion work are better served by Python's ecosystem
  (pydantic, pandas, ML/embedding libraries).
- **Go**: rejected — excellent performance profile, but slower iteration
  for data-shape-heavy CRUD and weaker AI/RAG tooling maturity relative to
  Python for this team's near-term needs.

## Consequences
- Native OpenAPI schema generation drives typed client generation for the
  frontend (`packages/shared-types`), keeping the contract in sync.
- Async-first framework suits I/O-bound workloads (DB queries, LLM calls,
  external source fetches in ingestion).
- Single language (Python) across API, eligibility engine, AI orchestration,
  and ingestion — one dependency ecosystem to secure and maintain.
