"""Unit tests for security utilities."""
import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    decode_token_safe,
)


def test_hash_and_verify():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert verify_password("mypassword", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_round_trip():
    import uuid
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


def test_refresh_token_type():
    import uuid
    token = create_refresh_token(uuid.uuid4())
    payload = decode_token(token)
    assert payload["type"] == "refresh"


def test_decode_invalid_token():
    result = decode_token_safe("not.a.valid.jwt")
    assert result is None


def test_access_token_rejected_as_refresh():
    import uuid
    token = create_access_token(uuid.uuid4())
    payload = decode_token(token)
    assert payload["type"] != "refresh"
