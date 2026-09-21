"""Aggregates all /api/v1 routers. Domain routers (jobs, exams, schemes,
...) are added here as each lands, per docs/API.md §3 and docs/ROADMAP.md
Phases 6-12. Only `health` exists in Phase 1.
"""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)
