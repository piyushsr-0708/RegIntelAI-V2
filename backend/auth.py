"""
auth.py — RegIntel AI V2
Offline JWT authentication using HS256 + PBKDF2 password hashing.
No external auth provider. Everything runs locally.
"""

import os
import hashlib
import hmac
import base64
import json
import time
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.database.models import User, Role
from backend.permissions import has_permission, Perm

logger = logging.getLogger(__name__)

# ─── JWT-like token (HS256 using stdlib only) ────────────────────────────────────
# Using stdlib-only implementation to avoid adding PyJWT dependency.
SECRET_KEY = os.environ.get("REGINTEL_SECRET", "regintel-ai-offline-secret-key-v2")
TOKEN_TTL = 3600 * 8  # 8 hours

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)

def create_token(payload: dict) -> str:
    payload = {**payload, "iat": int(time.time()), "exp": int(time.time()) + TOKEN_TTL}
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body   = _b64url_encode(json.dumps(payload).encode())
    sig_input = f"{header}.{body}".encode()
    sig = hmac.new(SECRET_KEY.encode(), sig_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"

def verify_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, body, sig = parts
        sig_input = f"{header}.{body}".encode()
        expected_sig = hmac.new(SECRET_KEY.encode(), sig_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_decode(sig), expected_sig):
            return None
        payload = json.loads(_b64url_decode(body))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

# ─── Password hashing (PBKDF2-HMAC-SHA256) ──────────────────────────────────────
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260000)
    return base64.b64encode(salt + dk).decode()

def verify_password(password: str, stored: str) -> bool:
    try:
        raw = base64.b64decode(stored.encode())
        salt, dk = raw[:16], raw[16:]
        test_dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260000)
        return hmac.compare_digest(dk, test_dk)
    except Exception:
        return False

# ─── Bearer token extractor ──────────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)

class CurrentUser:
    """Attached to request state after token verification."""
    def __init__(self, user: User, permissions: list[str]):
        self.user = user
        self.permissions = permissions
        self.id = user.id
        self.username = user.username
        self.role_name: str = user.role.role_name if user.role else "Viewer"
        self.department_id: Optional[str] = user.department_id

    def can(self, perm: str) -> bool:
        return has_permission(self.permissions, perm)

    def require(self, perm: str):
        if not self.can(perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {perm} required"
            )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    perms: list[str] = []
    if user.role:
        perms = user.role.permissions or []

    return CurrentUser(user=user, permissions=perms)


def require_permission(perm: str):
    """Returns a FastAPI dependency that enforces a specific permission."""
    def _check(current: CurrentUser = Depends(get_current_user)):
        current.require(perm)
        return current
    return _check
