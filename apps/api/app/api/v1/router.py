"""Aggregates all /api/v1 routers. Domain routers (exams, ...) are added
here as each lands, per docs/API.md §3 and docs/ROADMAP.md.
`health` (Phase 1), `search` (Phase 5), `jobs` (Phase 6), `services`
(Phase 7), `schemes` (Phase 8), `documents` (Phase 10), `eligibility`
(Phase 11), `ai` (Phase 12), `auth`/`tracking`/`notifications`
(Tracking + Notifications, rescheduled from Phase 12), and `admin`
(Phase 13, Admin Intelligence Center) exist so far.
"""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    ai,
    auth,
    documents,
    eligibility,
    health,
    jobs,
    notifications,
    schemes,
    search,
    services,
    tracking,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(search.router)
api_router.include_router(jobs.router)
api_router.include_router(services.router)
api_router.include_router(schemes.router)
api_router.include_router(documents.router)
api_router.include_router(eligibility.router)
api_router.include_router(ai.router)
api_router.include_router(auth.router)
api_router.include_router(tracking.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
