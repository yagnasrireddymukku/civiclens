"""Provenance model/constraint tests — docs/DATA_GOVERNANCE.md §3-4,
docs/DATABASE.md §2.7.

Fixture URLs use the `.invalid` TLD (reserved for exactly this purpose)
and clearly-fictional organization names, per docs/TESTING.md §15.
"""

import datetime
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.sources.enums import ChangeReviewStatus, VerificationStatus
from app.sources.models import ChangeRecord, Source, SourceVersion, VerificationRecord


def make_source(**overrides) -> Source:
    defaults = dict(
        url="https://example-test.invalid/notice/123",
        title="Test Notice — Not Real",
        organization="Test Board — Not Real",
        source_type="test-fixture",
        retrieved_date=datetime.date(2026, 1, 1),
    )
    defaults.update(overrides)
    return Source(**defaults)


def test_create_source_with_version(db_session: Session) -> None:
    source = make_source()
    db_session.add(source)
    db_session.flush()

    version = SourceVersion(
        source_id=source.id,
        content_hash="deadbeef",
        captured_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )
    db_session.add(version)
    db_session.flush()

    db_session.refresh(source)
    assert version in source.versions


def test_verification_record_requires_a_valid_source(db_session: Session) -> None:
    record = VerificationRecord(
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        source_id=uuid.uuid4(),  # does not exist
        status=VerificationStatus.UNVERIFIED,
    )
    db_session.add(record)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_verification_record_default_status_is_unverified(db_session: Session) -> None:
    source = make_source()
    db_session.add(source)
    db_session.flush()

    record = VerificationRecord(
        entity_type="test_entity", entity_id=uuid.uuid4(), source_id=source.id
    )
    db_session.add(record)
    db_session.flush()
    db_session.refresh(record)

    assert record.status == VerificationStatus.UNVERIFIED


def test_deleting_a_verified_source_is_restricted(db_session: Session) -> None:
    """A source that something has been verified against cannot be
    silently deleted out from under that verification — see
    docs/DATA_GOVERNANCE.md §3 (provenance must remain traceable)."""
    source = make_source()
    db_session.add(source)
    db_session.flush()

    db_session.add(
        VerificationRecord(entity_type="test_entity", entity_id=uuid.uuid4(), source_id=source.id)
    )
    db_session.flush()

    db_session.delete(source)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_verification_status_column_rejects_values_outside_the_enum(db_session: Session) -> None:
    """The DB-level guarantee, not just the Python enum: this bypasses the
    ORM/Pydantic layer entirely with a raw insert of an invalid label,
    proving the native Postgres enum type itself enforces the four
    documented states (docs/DATA_GOVERNANCE.md §4)."""
    source = make_source()
    db_session.add(source)
    db_session.flush()

    with pytest.raises(DataError):
        db_session.execute(
            sa.text(
                "INSERT INTO verification_records "
                "(id, entity_type, entity_id, source_id, status, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'test_entity', gen_random_uuid(), :source_id, "
                "'NOT_A_REAL_STATUS', now(), now())"
            ),
            {"source_id": source.id},
        )


def test_change_record_default_review_status_is_pending(db_session: Session) -> None:
    record = ChangeRecord(
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        field="deadline_date",
        old_value="2026-10-20",
        new_value="2026-10-27",
        detected_at=datetime.datetime.now(datetime.UTC),
    )
    db_session.add(record)
    db_session.flush()
    db_session.refresh(record)

    assert record.review_status == ChangeReviewStatus.PENDING


def test_change_record_links_to_source_version_optionally(db_session: Session) -> None:
    source = make_source()
    db_session.add(source)
    db_session.flush()
    version = SourceVersion(
        source_id=source.id,
        content_hash="cafebabe",
        captured_at=datetime.datetime.now(datetime.UTC),
    )
    db_session.add(version)
    db_session.flush()

    with_version = ChangeRecord(
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        field="title",
        detected_at=datetime.datetime.now(datetime.UTC),
        source_version_id=version.id,
    )
    without_version = ChangeRecord(
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        field="title",
        detected_at=datetime.datetime.now(datetime.UTC),
    )
    db_session.add_all([with_version, without_version])
    db_session.flush()  # must not raise for either row
