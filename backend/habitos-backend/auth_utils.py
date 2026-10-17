"""
auth_utils.py — Password hashing + JWT token helpers
"""

import hashlib
import hmac
import os
import json
import base64
import time
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.environ.get("HABITOS_SECRET", "habitos-super-secret-change-in-production")
TOKEN_EXPIRE_HOURS = 24 * 7   # 7 days


# ── Password hashing (SHA-256 + salt, no external deps) ──────────────────────

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    h = hmac.new(SECRET_KEY.encode(), (salt + password).encode(), hashlib.sha256).hexdigest()
    return f"{salt}:{h}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":", 1)
        expected = hmac.new(SECRET_KEY.encode(), (salt + password).encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(h, expected)
    except Exception:
        return False


# ── Simple JWT (header.payload.signature, no PyJWT needed) ──────────────────

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _sign(data: str) -> str:
    return _b64url(hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).digest())

def create_token(user_id: int, username: str) -> str:
    header  = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({
        "sub": user_id,
        "usr": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRE_HOURS * 3600,
    }).encode())
    sig = _sign(f"{header}.{payload}")
    return f"{header}.{payload}.{sig}"

def decode_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, sig = parts
        if not hmac.compare_digest(sig, _sign(f"{header}.{payload}")):
            return None
        pad = "=" * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload + pad))
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None


# ── FastAPI dependency ────────────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """Dependency: validates JWT and returns {id, username}."""
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    data = decode_token(credentials.credentials)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return {"id": data["sub"], "username": data["usr"]}
