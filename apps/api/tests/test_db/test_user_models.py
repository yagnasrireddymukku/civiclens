"""User/Profile model tests — docs/DATABASE.md §2.8, docs/PRIVACY.md §1.

Phase 3 scope is identity storage only (no auth flows) — these tests
cover the schema, not any login/auth behavior.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.geography.enums import StateStatus
from app.geography.models import State
from app.users.enums import UserRole
from app.users.models import Profile, User


def make_user(**overrides) -> User:
    defaults = dict(email="test.user@example-test.invalid")
    defaults.update(overrides)
    return User(**defaults)


def test_create_user_defaults_to_user_role(db_session: Session) -> None:
    user = make_user()
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)

    assert user.role == UserRole.USER
    assert user.password_hash is None


def test_user_email_must_be_unique(db_session: Session) -> None:
    db_session.add(make_user())
    db_session.flush()

    db_session.add(make_user())  # same email
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_profile_with_no_optional_fields_set_is_valid(db_session: Session) -> None:
    """Every profile field is optional per docs/PRIVACY.md §1 — a user
    with an empty profile must still be a valid row."""
    user = make_user()
    db_session.add(user)
    db_session.flush()

    profile = Profile(user_id=user.id)
    db_session.add(profile)
    db_session.flush()  # must not raise
    db_session.refresh(profile)

    assert profile.date_of_birth is None
    assert profile.qualification is None
    assert profile.state_id is None
    assert profile.district_id is None
    assert profile.category is None


def test_profile_is_one_to_one_with_user(db_session: Session) -> None:
    user = make_user()
    db_session.add(user)
    db_session.flush()

    db_session.add(Profile(user_id=user.id))
    db_session.flush()

    db_session.add(Profile(user_id=user.id))  # second profile, same user
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_profile_requires_an_existing_user(db_session: Session) -> None:
    db_session.add(Profile(user_id=uuid.uuid4()))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_user_cascades_to_profile(db_session: Session) -> None:
    user = make_user()
    db_session.add(user)
    db_session.flush()
    profile = Profile(user_id=user.id)
    db_session.add(profile)
    db_session.flush()
    profile_id = profile.id

    db_session.delete(user)
    db_session.flush()

    assert db_session.get(Profile, profile_id) is None


def test_profile_can_reference_geography_across_modules(db_session: Session) -> None:
    """Cross-module FK: profiles.state_id -> states.id. Confirms the
    users module and geography module compose correctly at the DB level
    without a Python import between them (see app/users/models.py's
    string-based ForeignKey)."""
    state = State(name="Testland", code="ZZ", slug="testland", status=StateStatus.PLANNED)
    db_session.add(state)
    user = make_user()
    db_session.add(user)
    db_session.flush()

    profile = Profile(user_id=user.id, state_id=state.id)
    db_session.add(profile)
    db_session.flush()  # must not raise
    db_session.refresh(profile)

    assert profile.state_id == state.id
