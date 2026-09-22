"""Aggregates all /api/v1 routers. Domain routers (exams, ...) are added
here as each lands, per docs/API.md §3 and docs/ROADMAP.md Phases 6-12.
`health` (Phase 1), `search` (Phase 5), `jobs` (Phase 6), `services`
(Phase 7), `schemes` (Phase 8), and `documents` (Phase 10) exist so far.
"""

from fastapi import APIRouter

from app.api.v1 import documents, health, jobs, schemes, search, services

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(search.router)
api_router.include_router(jobs.router)
api_router.include_router(services.router)
api_router.include_router(schemes.router)
api_router.include_router(documents.router)
