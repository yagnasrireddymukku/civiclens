"""Type-safe application configuration.

Loaded from environment variables (and a local `.env` file in development —
see `apps/api/.env.example` for the documented set of variables). No
default here is a real secret or a production value; see
docs/SECURITY.md for the secrets-handling rules this must follow.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "test", "staging", "production"] = "local"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Documented for Phase 3 onward (docs/DATABASE.md, docs/ROADMAP.md
    # Phase 3). No connection is opened against this in Phase 1 — the
    # repository must run locally without a database (see
    # docs/ROADMAP.md Phase 1 scope rules). Never a real credential here.
    database_url: str = "postgresql+psycopg://civiclens:civiclens@localhost:5432/civiclens_dev"

    # Civic AI / RAG (Phase 12, docs/AI_ARCHITECTURE.md) — provider
    # abstraction settings. "none" is the safe default: the app must
    # build, boot, and run its full test suite with the LLM/embedding
    # layer entirely disabled (this phase's explicit requirement). A real
    # deployment sets these via environment variables, never committed
    # here or in `.env.example` with a real value (CLAUDE.md rules 14-15).
    ai_llm_provider: Literal["anthropic", "none"] = "none"
    ai_llm_api_key: str | None = None
    ai_llm_model: str = "claude-haiku-4-5-20251001"
    ai_llm_base_url: str = "https://api.anthropic.com"
    ai_llm_timeout_seconds: float = 20.0
    ai_llm_max_tokens: int = 1024

    ai_embedding_provider: Literal["openai", "none"] = "none"
    ai_embedding_api_key: str | None = None
    ai_embedding_model: str = "text-embedding-3-small"
    # Must match the real model's output dimensionality — validated
    # against the provider's actual response at call time (see
    # app/ai/providers_openai.py), not just trusted here.
    ai_embedding_dimensions: int = 1536
    ai_embedding_base_url: str = "https://api.openai.com"
    ai_embedding_timeout_seconds: float = 20.0

    # In-process, single-instance rate limiting for /api/v1/ai/* only
    # (docs/SECURITY.md §6's "strictest per-user limits" class) — no
    # rate-limiting infrastructure of any kind exists elsewhere in this
    # codebase yet (verified by hand), so this is a deliberately minimal,
    # disclosed MVP: a sliding window keyed by client IP, in memory, not
    # shared across processes. Revisit with real infrastructure
    # (docs/SECURITY.md §14) before a multi-instance deployment.
    ai_rate_limit_requests: int = 10
    ai_rate_limit_window_seconds: float = 60.0

    # Auth (Tracking + Notifications, rescheduled from Phase 12;
    # ADR-009/SECURITY.md §2-3). The default below is an
    # obviously-fake local-only placeholder (same convention as
    # `database_url`'s fake credential above) — `get_settings()` refuses
    # to boot with it when `app_env` is "staging"/"production" (see
    # below), so a real deployment is *forced* to set a real secret via
    # environment variable, never committed here or in `.env.example`
    # (CLAUDE.md rules 14-15).
    jwt_secret_key: str = "local-dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    # ADR-009/SECURITY.md §2's exact TTLs.
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    # `Secure` cookie flag — true whenever the deployment is expected to
    # be served over HTTPS. Local dev/test serve over plain HTTP, so this
    # is computed from `app_env`, not a separate always-on setting (see
    # `Settings.cookies_secure`).
    csrf_cookie_name: str = "civiclens_csrf"
    access_cookie_name: str = "civiclens_access"
    refresh_cookie_name: str = "civiclens_refresh"

    # Tracking & Notifications (rescheduled from Phase 12).
    deadline_reminder_days_before: int = 3
    notification_delivery_max_attempts: int = 3

    email_provider: Literal["resend", "none"] = "none"
    email_api_key: str | None = None
    email_from_address: str = "notifications@civiclens.invalid"
    email_base_url: str = "https://api.resend.com"
    email_timeout_seconds: float = 20.0

    # Admin Intelligence Center. Same disclosed-MVP posture as
    # `ai_rate_limit_*` above (docs/SECURITY.md §14): an in-process,
    # single-instance sliding window, this time keyed by authenticated
    # user id rather than IP (every admin route requires
    # authentication, so the user id is always available and is a
    # tighter key than a shared office/NAT IP). Not shared code with
    # `app.ai.rate_limit` — a second small, disclosed MVP limiter
    # rather than a shared abstraction extracted for two callers
    # (CLAUDE.md rule 12).
    admin_rate_limit_requests: int = 20
    admin_rate_limit_window_seconds: float = 60.0

    @property
    def cookies_secure(self) -> bool:
        return self.app_env in ("staging", "production")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.app_env in ("staging", "production"):
        if settings.jwt_secret_key == Settings.model_fields["jwt_secret_key"].default:
            raise RuntimeError(
                "JWT_SECRET_KEY is still the local-dev placeholder in a "
                f"{settings.app_env!r} environment — set a real secret via the "
                "JWT_SECRET_KEY environment variable before starting (CLAUDE.md rules 14-15)."
            )
    return settings
