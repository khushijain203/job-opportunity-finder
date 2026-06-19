"""User profile endpoints – extended career metadata for future Resume / Match phases."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from core.security import get_current_user
from models.user import Profile, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=Profile)
async def get_profile(request: Request, user: dict = Depends(get_current_user)):
    db = request.app.state.db
    doc = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not doc:
        # return a default-shaped profile so the UI can render without 404s
        return Profile(user_id=user["id"], full_name=user.get("full_name"))
    return Profile(**doc)


@router.put("", response_model=Profile)
async def upsert_profile(
    payload: ProfileUpdate,
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = request.app.state.db
    update: dict = {"updated_at": _now_iso(), "user_id": user["id"]}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        update[k] = v
    await db.profiles.update_one(
        {"user_id": user["id"]}, {"$set": update}, upsert=True
    )
    doc = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    return Profile(**doc)
