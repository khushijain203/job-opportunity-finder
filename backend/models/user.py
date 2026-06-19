"""User & Profile models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------- #
# Auth payloads
# ---------------------------------------------------------------------------- #
class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------- #
# Stored user document
# ---------------------------------------------------------------------------- #
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    full_name: str
    email: str
    password_hash: str
    created_at: str = Field(default_factory=_now_iso)
    is_demo: bool = False


class UserPublic(BaseModel):
    """User payload returned to clients (no password)."""

    id: str
    full_name: str
    email: str
    created_at: str
    is_demo: bool = False


# ---------------------------------------------------------------------------- #
# Profile (extended career metadata for future phases)
# ---------------------------------------------------------------------------- #
class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    skills: Optional[List[str]] = None
    years_experience: Optional[float] = Field(default=None, ge=0, le=80)
    preferred_roles: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    bio: Optional[str] = Field(default=None, max_length=2000)


class Profile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: str
    full_name: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    years_experience: Optional[float] = None
    preferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    bio: Optional[str] = None
    updated_at: str = Field(default_factory=_now_iso)
