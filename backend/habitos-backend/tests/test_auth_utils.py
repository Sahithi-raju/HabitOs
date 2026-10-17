import time
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from auth_utils import hash_password, verify_password, create_token, decode_token, get_current_user, _b64url, _sign


def test_hash_password_and_verify():
    password = "MySecret123"
    hashed = hash_password(password)
    assert ":" in hashed
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-pass", hashed) is False


def test_verify_password_invalid_format():
    assert verify_password("x", "invalid-format") is False


def test_jwt_create_decode_roundtrip():
    token = create_token(42, "tester")
    data = decode_token(token)
    assert data is not None
    assert data["sub"] == 42
    assert data["usr"] == "tester"
    assert data["exp"] > time.time()


def test_jwt_decode_invalid_token():
    assert decode_token("bad.token.format") is None
    bad = create_token(3, "a") + "tamper"
    assert decode_token(bad) is None


def test_jwt_decode_expired_token():
    header = _b64url(b"{\"alg\":\"HS256\",\"typ\":\"JWT\"}")
    payload = _b64url(b"{\"sub\":1,\"usr\":\"user\",\"iat\":1,\"exp\":1}")
    sig = _sign(f"{header}.{payload}")
    expired = f"{header}.{payload}.{sig}"
    assert decode_token(expired) is None


def test_get_current_user_success():
    token = create_token(99, "unit")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(credentials)
    assert user["id"] == 99
    assert user["username"] == "unit"


def test_get_current_user_missing_credentials():
    with pytest.raises(HTTPException):
        get_current_user(None)
