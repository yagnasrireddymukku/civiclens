"""Shared helper for spinning up a real, ephemeral PostgreSQL instance in
tests via `pgserver` (a pip-installable embedded Postgres with prebuilt
binaries for Linux/macOS/Windows).

Why not Docker: docs/TESTING.md §3 requires integration tests to run
against a real PostgreSQL database, never mocks. Docker is the normal way
to provide that in CI/dev, but this specific development environment has
no Docker daemon / WSL2 available. `pgserver` gets the same guarantee (a
real Postgres, not a mock or a different database engine standing in for
it) without that dependency. Production and every deployed environment
remain plain PostgreSQL per ADR-004 — this is purely a test-execution
detail, isolated to this module.
"""

import pgserver


def to_sqlalchemy_url(pgserver_uri: str) -> str:
    """`pgserver` returns a `postgresql://` URI; the app's models/engine
    use the psycopg3 dialect (`postgresql+psycopg://`) everywhere else
    (app.core.config.Settings.database_url), so tests must match."""
    return pgserver_uri.replace("postgresql://", "postgresql+psycopg://", 1)


def start_test_postgres(directory: str) -> pgserver.PostgresServer:
    return pgserver.get_server(directory)
