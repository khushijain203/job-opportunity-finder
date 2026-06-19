"""Authentication & migration routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from core.security import (
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    set_auth_cookies,
    validate_password_policy,
    verify_password,
)
from models.user import User, UserLogin, UserPublic, UserRegister

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Records inserted before auth existed are migrated to the first registered user.
# A flag in `system_state` tracks completion so we only run the claim once.
MIGRATION_KEY = "orphan_migration_v1"


def _public(user_doc: dict) -> UserPublic:
    return UserPublic(
        id=user_doc["id"],
        full_name=user_doc.get("full_name", ""),
        email=user_doc["email"],
        created_at=user_doc.get("created_at", ""),
        is_demo=user_doc.get("is_demo", False),
    )


async def _claim_orphans_for(db, user_id: str) -> dict:
    """Assign all records that have no user_id to this user. Idempotent via system_state flag."""
    state = await db.system_state.find_one({"key": MIGRATION_KEY})
    if state and state.get("done"):
        return {"claimed": False}

    counts = {}
    for coll in ("companies", "opportunities", "generated_emails"):
        result = await db[coll].update_many(
            {"$or": [{"user_id": {"$exists": False}}, {"user_id": None}]},
            {"$set": {"user_id": user_id}},
        )
        counts[coll] = result.modified_count

    await db.system_state.update_one(
        {"key": MIGRATION_KEY},
        {"$set": {"done": True, "user_id": user_id, "done_at": datetime.now(timezone.utc).isoformat(), "counts": counts}},
        upsert=True,
    )
    logger.info("Orphan migration → user %s. Counts: %s", user_id, counts)
    return {"claimed": True, "counts": counts}


# ---------------------------------------------------------------------------- #
# Register
# ---------------------------------------------------------------------------- #
@router.post("/register", response_model=UserPublic, status_code=201)
async def register(payload: UserRegister, request: Request, response: Response):
    db = request.app.state.db
    email = payload.email.lower().strip()

    validate_password_policy(payload.password)

    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=409, detail="A user with that email already exists.")

    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )
    await db.users.insert_one(user.model_dump())

    # Migration: first registered (non-demo) user inherits any orphan records.
    await _claim_orphans_for(db, user.id)

    access = create_access_token(user.id, user.email)
    refresh = create_refresh_token(user.id)
    set_auth_cookies(response, access, refresh)

    logger.info("Registered user id=%s email=%s", user.id, user.email)
    return _public(user.model_dump())


# ---------------------------------------------------------------------------- #
# Login
# ---------------------------------------------------------------------------- #
@router.post("/login", response_model=UserPublic)
async def login(payload: UserLogin, request: Request, response: Response):
    db = request.app.state.db
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    access = create_access_token(user["id"], user["email"])
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    return _public(user)


# ---------------------------------------------------------------------------- #
# Refresh
# ---------------------------------------------------------------------------- #
@router.post("/refresh", response_model=UserPublic)
async def refresh_token(request: Request, response: Response):
    db = request.app.state.db
    token: Optional[str] = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_token(token, expected_type="refresh")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    access = create_access_token(user["id"], user["email"])
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    return _public(user)


# ---------------------------------------------------------------------------- #
# Logout
# ---------------------------------------------------------------------------- #
@router.post("/logout", status_code=204)
async def logout(response: Response):
    clear_auth_cookies(response)
    return None


# ---------------------------------------------------------------------------- #
# Me
# ---------------------------------------------------------------------------- #
@router.get("/me", response_model=UserPublic)
async def me(user: dict = Depends(get_current_user)):
    return _public(user)
