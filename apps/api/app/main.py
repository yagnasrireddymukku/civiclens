"""Application factory. See docs/ARCHITECTURE.md §1 for the modular-monolith
boundary rule this app is structured around, and docs/API.md for the
conventions every route (from Phase 2 onward) must follow.

No business/domain endpoints exist yet — this is the Phase 1 foundation:
settings, logging, CORS, error handling, and one health check.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="CivicLens API",
        version="0.1.0",
        description=(
            "See docs/API.md for API conventions. Phase 1 foundation only — "
            "no business endpoints exist yet."
        ),
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
