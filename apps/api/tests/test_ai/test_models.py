"""Database-level constraint tests for `KnowledgeChunk` — the CHECK
constraint guarding against a vector whose length doesn't match its own
declared `embedding_dimensions` (the "safe compatibility check" this
phase requires, enforced at the database layer as a backstop beyond the
provider-side check in `app.ai.providers_openai`).
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.models import KnowledgeChunk


def test_embedding_length_mismatch_violates_check_constraint(db_session: Session) -> None:
    db_session.add(
        KnowledgeChunk(
            entity_type="job",
            entity_id=uuid.uuid4(),
            locale="en",
            chunk_index=0,
            chunk_text="Some text.",
            content_hash="a" * 64,
            embedding_model="fake-embed-1",
            embedding_dimensions=8,
            embedding=[0.1, 0.2, 0.3],  # only 3 values, not 8
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_embedding_length_matching_dimensions_is_valid(db_session: Session) -> None:
    chunk = KnowledgeChunk(
        entity_type="job",
        entity_id=uuid.uuid4(),
        locale="en",
        chunk_index=0,
        chunk_text="Some text.",
        content_hash="a" * 64,
        embedding_model="fake-embed-1",
        embedding_dimensions=3,
        embedding=[0.1, 0.2, 0.3],
    )
    db_session.add(chunk)
    db_session.flush()
    assert chunk.id is not None


def test_duplicate_entity_locale_chunk_index_violates_unique_constraint(
    db_session: Session,
) -> None:
    entity_id = uuid.uuid4()
    db_session.add(
        KnowledgeChunk(
            entity_type="job",
            entity_id=entity_id,
            locale="en",
            chunk_index=0,
            chunk_text="First.",
            content_hash="a" * 64,
            embedding_model="fake-embed-1",
            embedding_dimensions=2,
            embedding=[0.1, 0.2],
        )
    )
    db_session.flush()

    db_session.add(
        KnowledgeChunk(
            entity_type="job",
            entity_id=entity_id,
            locale="en",
            chunk_index=0,
            chunk_text="Second.",
            content_hash="b" * 64,
            embedding_model="fake-embed-1",
            embedding_dimensions=2,
            embedding=[0.3, 0.4],
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
