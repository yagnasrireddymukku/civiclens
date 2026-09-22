"""Dev convenience: `uv run python scripts/seed_job_fixtures.py`.

Loads the synthetic job fixtures (app/jobs/fixtures.py) into whatever
database DATABASE_URL currently points at — the module itself refuses to
run unless APP_ENV is "local" or "test", so this is safe to leave
undocumented-but-discoverable rather than needing its own guard.
"""

from app.core.db import model_registry  # noqa: F401 -- see docstring below
from app.core.db.session import get_sessionmaker
from app.jobs.fixtures import load_fixtures

# `model_registry` must be imported (for its side effect of registering
# every model module) before any ORM operation, not just `app.jobs`'s
# own models: `Organization`/`Department` (app/institutions/models.py)
# declare relationships to both `Job` and `Service` by name, resolved
# lazily against SQLAlchemy's shared registry the first time any mapper
# configures. A standalone script importing only `app.jobs` would
# otherwise fail with "expression 'Service' failed to locate a name" —
# verified by hand running this script without the import above.


def main() -> None:
    session = get_sessionmaker()()
    try:
        load_fixtures(session)
        print("Loaded synthetic job fixtures.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
