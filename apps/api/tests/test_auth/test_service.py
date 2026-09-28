"""Auth domain-logic tests — registration, login, and the refresh-
rotation/replay-detection property (docs/SECURITY.md §2).
"""

import pytest
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.models import RefreshToken
from app.core.config import Settings
from tests.test_auth._helpers import make_user

SETTINGS = Settings(jwt_secret_key="test-only-secret-not-a-real-credential")


def test_register_user_hashes_the_password(db_session: Session) -> None:
    user = service.register_user(
        db_session, email="new-user@example-test.invalid", password="a-real-password-123"
    )
    assert user.password_hash != "a-real-password-123"
    assert user.email == "new-user@example-test.invalid"


def test_register_user_rejects_a_duplicate_email(db_session: Session) -> None:
    service.register_user(db_session, email="dupe@example-test.invalid", password="password-one")
    with pytest.raises(service.EmailAlreadyRegisteredError):
        service.register_user(
            db_session, email="dupe@example-test.invalid", password="password-two"
        )


def test_register_user_email_uniqueness_is_case_insensitive(db_session: Session) -> None:
    service.register_user(db_session, email="Person@Example-Test.invalid", password="password-one")
    with pytest.raises(service.EmailAlreadyRegisteredError):
        service.register_user(
            db_session, email="person@example-test.invalid", password="password-two"
        )


def test_authenticate_user_succeeds_with_correct_credentials(db_session: Session) -> None:
    user = make_user(db_session, email="known@example-test.invalid")
    authenticated = service.authenticate_user(
        db_session, email="known@example-test.invalid", password="Correct-Horse-Battery-Staple"
    )
    assert authenticated is not None
    assert authenticated.id == user.id


def test_authenticate_user_fails_with_wrong_password(db_session: Session) -> None:
    make_user(db_session, email="known2@example-test.invalid")
    assert (
        service.authenticate_user(
            db_session, email="known2@example-test.invalid", password="wrong-password"
        )
        is None
    )


def test_authenticate_user_fails_for_unknown_email(db_session: Session) -> None:
    assert (
        service.authenticate_user(
            db_session, email="nobody@example-test.invalid", password="whatever"
        )
        is None
    )


def test_authenticate_user_fails_for_oauth_only_account_with_no_password(
    db_session: Session,
) -> None:
    make_user(db_session, email="oauth-only@example-test.invalid", password_hash=None)
    assert (
        service.authenticate_user(
            db_session, email="oauth-only@example-test.invalid", password="anything"
        )
        is None
    )


def test_issue_token_pair_creates_a_refresh_token_row(db_session: Session) -> None:
    user = make_user(db_session)
    tokens = service.issue_token_pair(db_session, settings=SETTINGS, user=user)
    stored = (
        db_session.query(RefreshToken)
        .filter_by(token_hash=service.hash_refresh_token(tokens.refresh_token))
        .one()
    )
    assert stored.user_id == user.id
    assert stored.revoked_at is None


def test_rotate_refresh_token_issues_a_new_pair_and_revokes_the_old(db_session: Session) -> None:
    user = make_user(db_session)
    first = service.issue_token_pair(db_session, settings=SETTINGS, user=user)

    rotated_user, second = service.rotate_refresh_token(
        db_session, settings=SETTINGS, raw_refresh_token=first.refresh_token
    )

    assert rotated_user.id == user.id
    assert second.refresh_token != first.refresh_token
    old_row = (
        db_session.query(RefreshToken)
        .filter_by(token_hash=service.hash_refresh_token(first.refresh_token))
        .one()
    )
    assert old_row.revoked_at is not None


def test_rotate_refresh_token_shares_the_same_family(db_session: Session) -> None:
    user = make_user(db_session)
    first = service.issue_token_pair(db_session, settings=SETTINGS, user=user)
    old_row = (
        db_session.query(RefreshToken)
        .filter_by(token_hash=service.hash_refresh_token(first.refresh_token))
        .one()
    )

    _, second = service.rotate_refresh_token(
        db_session, settings=SETTINGS, raw_refresh_token=first.refresh_token
    )
    new_row = (
        db_session.query(RefreshToken)
        .filter_by(token_hash=service.hash_refresh_token(second.refresh_token))
        .one()
    )
    assert new_row.family_id == old_row.family_id


def test_replaying_an_already_rotated_refresh_token_revokes_the_whole_family(
    db_session: Session,
) -> None:
    """The critical security property: presenting a refresh token that
    has already been rotated away must revoke the entire family — not
    just fail once, but lock out every token descended from it,
    forcing a fresh login."""

    user = make_user(db_session)
    first = service.issue_token_pair(db_session, settings=SETTINGS, user=user)
    _, second = service.rotate_refresh_token(
        db_session, settings=SETTINGS, raw_refresh_token=first.refresh_token
    )

    # Replay the now-stale `first` token (as a thief who intercepted it
    # earlier might).
    with pytest.raises(service.RefreshTokenError):
        service.rotate_refresh_token(
            db_session, settings=SETTINGS, raw_refresh_token=first.refresh_token
        )

    # The legitimate `second` token — the one actually in the user's
    # browser — must also now be dead.
    with pytest.raises(service.RefreshTokenError):
        service.rotate_refresh_token(
            db_session, settings=SETTINGS, raw_refresh_token=second.refresh_token
        )


def test_rotate_refresh_token_rejects_an_unrecognized_token(db_session: Session) -> None:
    with pytest.raises(service.RefreshTokenError):
        service.rotate_refresh_token(
            db_session, settings=SETTINGS, raw_refresh_token="not-a-real-token"
        )


def test_revoke_refresh_token_prevents_further_rotation(db_session: Session) -> None:
    user = make_user(db_session)
    tokens = service.issue_token_pair(db_session, settings=SETTINGS, user=user)
    service.revoke_refresh_token(db_session, raw_refresh_token=tokens.refresh_token)

    with pytest.raises(service.RefreshTokenError):
        service.rotate_refresh_token(
            db_session, settings=SETTINGS, raw_refresh_token=tokens.refresh_token
        )
