"""Ops convenience: `uv run python scripts/reindex_ai_knowledge.py`.

Rebuilds `ai_knowledge_chunks` from whatever is currently published in
`search_documents` (docs/AI_ARCHITECTURE.md, docs/DATABASE.md §16) —
idempotent by content hash, so a routine re-run only re-embeds entities
whose content actually changed.

Deliberately a script, not an HTTP endpoint: no auth/role-check
mechanism exists anywhere in this codebase yet (verified by hand), so
per this phase's explicit "never expose an unauthenticated destructive
indexing endpoint," this stays internal-only until a future phase adds
real admin authentication.

Requires AI_EMBEDDING_PROVIDER to be configured (an embedding provider
must exist to build vectors) — exits with a clear message otherwise
rather than silently doing nothing.
"""

import asyncio

from app.ai.indexing import reindex_all
from app.ai.providers import get_embedding_provider
from app.core.db import model_registry  # noqa: F401 -- see scripts/seed_job_fixtures.py
from app.core.db.session import get_sessionmaker


async def main() -> None:
    embedding_provider = get_embedding_provider()
    if embedding_provider is None:
        print(
            "No embedding provider is configured (AI_EMBEDDING_PROVIDER=none or no API key "
            "set) — nothing to do. Set AI_EMBEDDING_PROVIDER/AI_EMBEDDING_API_KEY first."
        )
        return

    session = get_sessionmaker()()
    try:
        summary = await reindex_all(session, embedding_provider=embedding_provider)
        print(
            f"Indexed {summary.indexed}, skipped (unchanged) {summary.skipped_unchanged}, "
            f"removed (orphaned) {summary.removed}, failed {summary.failed}."
        )
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())
