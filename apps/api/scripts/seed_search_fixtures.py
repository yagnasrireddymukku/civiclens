"""Dev convenience: `uv run python scripts/seed_search_fixtures.py`.

Loads the synthetic search fixtures (app/search/fixtures.py) into
whatever database DATABASE_URL currently points at — the module itself
refuses to run unless APP_ENV is "local" or "test", so this is safe to
leave undocumented-but-discoverable rather than needing its own guard.
"""

from app.core.db.session import get_sessionmaker
from app.search.fixtures import load_fixtures


def main() -> None:
    session = get_sessionmaker()()
    try:
        load_fixtures(session)
        print("Loaded synthetic search fixtures.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
