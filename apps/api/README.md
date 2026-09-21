# CivicLens API

FastAPI backend. See [../../docs/API.md](../../docs/API.md) for conventions
and [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) for the
modular-monolith structure this app follows. No business endpoints exist
yet — see [../../docs/ROADMAP.md](../../docs/ROADMAP.md).

## Setup

```bash
cd apps/api
uv sync
cp .env.example .env
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

Then visit `http://localhost:8000/api/v1/health` or
`http://localhost:8000/docs` for the interactive OpenAPI docs.

## Test / Lint / Typecheck

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```
