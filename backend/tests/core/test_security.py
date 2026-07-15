import pytest
from fastapi import HTTPException

from app.core.security import (
    hash_password,
    hash_secret,
    new_secret,
    validate_new_password,
    verify_password,
)


def test_password_is_argon2_hashed_and_verifiable():
    encoded = hash_password("correct horse battery staple")
    assert encoded.startswith("$argon2")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_weak_password_is_rejected():
    with pytest.raises(HTTPException):
        validate_new_password("short", "user@example.com")


def test_session_secrets_are_random_and_stored_as_hashes():
    first = new_secret()
    second = new_secret()
    assert first != second
    assert len(first) >= 40
    assert hash_secret(first) != first
