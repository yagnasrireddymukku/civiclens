"""Aggregates all /api/v1 routers. Domain routers (jobs, exams, schemes,
...) are added here as each lands, per docs/API.md §3 and docs/ROADMAP.md
Phases 6-12. `health` (Phase 1) and `search` (Phase 5) exist so far.
"""

from fastapi import APIRouter

from app.api.v1 import health, search

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(search.router)
