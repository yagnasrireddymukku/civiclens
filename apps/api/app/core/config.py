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


@lru_cache
def get_settings() -> Settings:
    return Settings()
