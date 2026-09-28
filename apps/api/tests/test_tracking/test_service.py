"""Tracking service-layer tests: entity resolution, idempotent
tracking/reactivation, pause/resume/remove, and — critically — that one
user can never read or mutate another user's tracked items.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.tracking import service
from app.tracking.enums import TrackedEntityType
from app.tracking.models import TrackedItem
from tests.test_auth._helpers import make_user
from tests.test_documents._helpers import make_organization, make_source, make_state
from tests.test_jobs._helpers import make_job


def test_resolve_entity_finds_a_visible_job(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)

    resolved = service.resolve_entity(db_session, TrackedEntityType.JOB, job.slug)

    assert resolved is not None
    assert resolved.entity_id == job.id


def test_resolve_entity_returns_none_for_unknown_slug(db_session: Session) -> None:
    assert service.resolve_entity(db_session, TrackedEntityType.JOB, "no-such-job") is None


def test_track_entity_creates_a_new_row(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)

    item = service.track_entity(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    assert item.job_id == job.id
    assert item.is_active is True


def test_tracking_the_same_entity_twice_is_idempotent(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)

    first = service.track_entity(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )
    second = service.track_entity(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    assert first.id == second.id
    count = db_session.query(TrackedItem).filter_by(user_id=user.id, job_id=job.id).count()
    assert count == 1


def test_tracking_a_paused_entity_again_reactivates_it(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)

    item = service.track_entity(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )
    service.pause_tracked_item(db_session, user_id=user.id, tracked_item_id=item.id)
    db_session.flush()

    reactivated = service.track_entity(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    assert reactivated.id == item.id
    assert reactivated.is_active is True
    assert reactivated.paused_at is None


def test_pause_and_resume_toggle_is_active(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)
    item = service.track_entity(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    service.pause_tracked_item(db_session, user_id=user.id, tracked_item_id=item.id)
    db_session.flush()
    assert item.is_active is False
    assert item.paused_at is not None

    service.resume_tracked_item(db_session, user_id=user.id, tracked_item_id=item.id)
    db_session.flush()
    assert item.is_active is True
    assert item.paused_at is None


def test_remove_tracked_item_deletes_the_row(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)
    item = service.track_entity(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )
    item_id = item.id

    service.remove_tracked_item(db_session, user_id=user.id, tracked_item_id=item_id)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(TrackedItem, item_id) is None


def test_removing_and_re_tracking_the_same_entity_works(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)
    first = service.track_entity(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )
    service.remove_tracked_item(db_session, user_id=user.id, tracked_item_id=first.id)
    db_session.flush()

    second = service.track_entity(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )
    db_session.flush()  # must not raise a uniqueness violation

    assert second.id != first.id


class TestOwnership:
    def test_pausing_another_users_tracked_item_is_rejected(self, db_session: Session) -> None:
        state = make_state(db_session)
        source = make_source(db_session)
        organization = make_organization(db_session, state)
        job = make_job(db_session, organization=organization, state=state, source=source)
        owner = make_user(db_session)
        attacker = make_user(db_session)
        item = service.track_entity(
            db_session, user_id=owner.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
        )

        with pytest.raises(service.TrackedItemNotFoundError):
            service.pause_tracked_item(db_session, user_id=attacker.id, tracked_item_id=item.id)

    def test_removing_another_users_tracked_item_is_rejected(self, db_session: Session) -> None:
        state = make_state(db_session)
        source = make_source(db_session)
        organization = make_organization(db_session, state)
        job = make_job(db_session, organization=organization, state=state, source=source)
        owner = make_user(db_session)
        attacker = make_user(db_session)
        item = service.track_entity(
            db_session, user_id=owner.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
        )

        with pytest.raises(service.TrackedItemNotFoundError):
            service.remove_tracked_item(db_session, user_id=attacker.id, tracked_item_id=item.id)

    def test_operating_on_a_nonexistent_tracked_item_is_rejected(self, db_session: Session) -> None:
        user = make_user(db_session)
        with pytest.raises(service.TrackedItemNotFoundError):
            service.pause_tracked_item(db_session, user_id=user.id, tracked_item_id=uuid.uuid4())

    def test_list_tracked_items_only_returns_the_caller_s_own(self, db_session: Session) -> None:
        state = make_state(db_session)
        source = make_source(db_session)
        organization = make_organization(db_session, state)
        job = make_job(db_session, organization=organization, state=state, source=source)
        owner = make_user(db_session)
        other = make_user(db_session)
        service.track_entity(
            db_session, user_id=owner.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
        )

        assert service.list_tracked_items(db_session, user_id=other.id) == []
