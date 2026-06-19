"""Security primitives: password hashing, JWT encoding/decoding, FastAPI dependency.

Keeps all auth-related crypto in one module so other features stay clean.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import HTTPException, Request, status

JWT_ALGORITHM = "HS256"
ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
ACCESS_TTL = timedelta(hours=12)
REFRESH_TTL = timedelta(days=14)

# ---------------------------------------------------------------------------- #
# Password hashing
# ---------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------- #
# Password policy
# ---------------------------------------------------------------------------- #
_PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


def validate_password_policy(password: str) -> None:
    if not _PASSWORD_RE.match(password or ""):
        raise HTTPException(
            status_code=422,
            detail=(
                "Password must be at least 8 characters and include "
                "an uppercase letter, a lowercase letter, and a number."
            ),
        )


# ---------------------------------------------------------------------------- #
# JWT helpers
# ---------------------------------------------------------------------------- #
def _secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not configured")
    return secret


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + ACCESS_TTL,
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + REFRESH_TTL,
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str, expected_type: Optional[str] = None) -> dict:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    if expected_type and payload.get("type") != expected_type:
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload


# ---------------------------------------------------------------------------- #
# Cookie helpers
# ---------------------------------------------------------------------------- #
def _is_secure() -> bool:
    """Use Secure flag when not in plain-localhost dev (preview & prod are HTTPS)."""
    return os.environ.get("COOKIE_SECURE", "true").lower() != "false"


def set_auth_cookies(response, access: str, refresh: str) -> None:
    secure = _is_secure()
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=int(ACCESS_TTL.total_seconds()),
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=int(REFRESH_TTL.total_seconds()),
        path="/",
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")


# ---------------------------------------------------------------------------- #
# FastAPI dependency
# ---------------------------------------------------------------------------- #
async def get_current_user(request: Request) -> dict:
    """Read the access token from cookie (or Bearer header) and resolve the user."""
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(token, expected_type="access")
    db = request.app.state.db
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
