"""Dev convenience: `uv run python scripts/seed_service_fixtures.py`.

Loads the synthetic service fixtures (app/services/fixtures.py) into
whatever database DATABASE_URL currently points at — the module itself
refuses to run unless APP_ENV is "local" or "test", so this is safe to
leave undocumented-but-discoverable rather than needing its own guard.
"""

from app.core.db import model_registry  # noqa: F401 -- see scripts/seed_job_fixtures.py
from app.core.db.session import get_sessionmaker
from app.services.fixtures import load_fixtures


def main() -> None:
    session = get_sessionmaker()()
    try:
        load_fixtures(session)
        print("Loaded synthetic service fixtures.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
