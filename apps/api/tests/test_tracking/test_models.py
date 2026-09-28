"""Database-level constraint tests for `TrackedItem` — the `CHECK`
constraint (exactly one entity FK set) and, most importantly, the
`UNIQUE ... NULLS NOT DISTINCT` constraint that makes duplicate-active-
tracking prevention a real database guarantee rather than only an
application-level check (see app/tracking/models.py's module docstring
for why a plain `UNIQUE` would silently fail to catch this on Postgres).
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.tracking.models import TrackedItem
from tests.test_auth._helpers import make_user
from tests.test_documents._helpers import make_document, make_organization, make_source, make_state
from tests.test_jobs._helpers import make_job


def test_tracked_item_with_zero_entities_violates_check_constraint(db_session: Session) -> None:
    user = make_user(db_session)
    db_session.add(TrackedItem(user_id=user.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_tracked_item_with_two_entities_violates_check_constraint(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    document = make_document(db_session, organization=organization, source=source)
    user = make_user(db_session)

    db_session.add(TrackedItem(user_id=user.id, job_id=job.id, document_id=document.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_active_tracking_for_the_same_user_and_entity_is_rejected(
    db_session: Session,
) -> None:
    """The property this phase's §4.1 requires at the database layer:
    Postgres's *default* NULL handling would treat every `NULL` as
    unique-from-every-other-NULL, silently defeating a plain `UNIQUE`
    constraint across mostly-NULL columns — `NULLS NOT DISTINCT`
    (Postgres 16, this project's actual version) is what makes this
    test pass rather than a false negative."""

    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)

    db_session.add(TrackedItem(user_id=user.id, job_id=job.id))
    db_session.flush()

    db_session.add(TrackedItem(user_id=user.id, job_id=job.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_two_different_users_can_track_the_same_entity(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user_a = make_user(db_session)
    user_b = make_user(db_session)

    db_session.add(TrackedItem(user_id=user_a.id, job_id=job.id))
    db_session.add(TrackedItem(user_id=user_b.id, job_id=job.id))
    db_session.flush()  # must not raise


def test_one_user_can_track_two_different_entities(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    document = make_document(db_session, organization=organization, source=source)
    user = make_user(db_session)

    db_session.add(TrackedItem(user_id=user.id, job_id=job.id))
    db_session.add(TrackedItem(user_id=user.id, document_id=document.id))
    db_session.flush()  # must not raise


def test_deleting_the_tracked_job_cascades_to_the_tracked_item(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)
    item = TrackedItem(user_id=user.id, job_id=job.id)
    db_session.add(item)
    db_session.flush()
    item_id = item.id

    db_session.delete(job)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(TrackedItem, item_id) is None


def test_deleting_the_user_cascades_to_their_tracked_items(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)
    item = TrackedItem(user_id=user.id, job_id=job.id)
    db_session.add(item)
    db_session.flush()
    item_id = item.id

    db_session.delete(user)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(TrackedItem, item_id) is None
