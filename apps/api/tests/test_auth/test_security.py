"""Password hashing and JWT encode/decode — the cryptographic
primitives ADR-009/docs/SECURITY.md §2 specify.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt as pyjwt

from app.auth.security import (
    create_access_token,
    decode_access_token,
    generate_csrf_token,
    generate_refresh_token_secret,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.core.config import Settings
from app.users.enums import UserRole

SETTINGS = Settings(jwt_secret_key="test-only-secret-not-a-real-credential")


def test_hash_password_produces_a_verifiable_hash() -> None:
    hashed = hash_password("Correct-Horse-Battery-Staple")
    assert hashed != "Correct-Horse-Battery-Staple"
    assert verify_password("Correct-Horse-Battery-Staple", hashed) is True


def test_verify_password_rejects_a_wrong_password() -> None:
    hashed = hash_password("Correct-Horse-Battery-Staple")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_handles_a_malformed_hash_safely() -> None:
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_access_token_round_trips() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(settings=SETTINGS, user_id=user_id, role=UserRole.USER)
    claims = decode_access_token(settings=SETTINGS, token=token)
    assert claims is not None
    assert claims.user_id == user_id
    assert claims.role == UserRole.USER


def test_decode_access_token_rejects_an_expired_token() -> None:
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid.uuid4()),
        "role": UserRole.USER.value,
        "type": "access",
        "iat": now - timedelta(minutes=30),
        "exp": now - timedelta(minutes=15),
    }
    expired = pyjwt.encode(payload, SETTINGS.jwt_secret_key, algorithm=SETTINGS.jwt_algorithm)
    assert decode_access_token(settings=SETTINGS, token=expired) is None


def test_decode_access_token_rejects_a_token_signed_with_a_different_secret() -> None:
    other_settings = Settings(jwt_secret_key="a-completely-different-secret-value-here")
    token = create_access_token(settings=other_settings, user_id=uuid.uuid4(), role=UserRole.USER)
    assert decode_access_token(settings=SETTINGS, token=token) is None


def test_decode_access_token_rejects_garbage() -> None:
    assert decode_access_token(settings=SETTINGS, token="not.a.jwt") is None


def test_decode_access_token_rejects_a_refresh_typed_token() -> None:
    # A token with `type` set to anything other than "access" (e.g. if a
    # future token type were introduced) must never be accepted here.
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid.uuid4()),
        "role": UserRole.USER.value,
        "type": "not-access",
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    token = pyjwt.encode(payload, SETTINGS.jwt_secret_key, algorithm=SETTINGS.jwt_algorithm)
    assert decode_access_token(settings=SETTINGS, token=token) is None


def test_refresh_token_secret_is_hashed_non_reversibly() -> None:
    raw = generate_refresh_token_secret()
    hashed = hash_refresh_token(raw)
    assert hashed != raw
    assert hash_refresh_token(raw) == hashed  # deterministic


def test_refresh_token_secrets_are_unique() -> None:
    assert generate_refresh_token_secret() != generate_refresh_token_secret()


def test_csrf_tokens_are_unique() -> None:
    assert generate_csrf_token() != generate_csrf_token()
