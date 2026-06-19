"""Duplicate detection for ingested opportunities.

Strategy (per user_id - data isolation is preserved):
1. Strong key: (source, source_id) — exact match wins.
2. Fallback: normalized (company_name, role, location) — case-insensitive
   substring/equality match. Used when source_id is unavailable
   (e.g. manual entry, scrapers without IDs).
"""

from __future__ import annotations

import re
from typing import Optional


def _norm(s: Optional[str]) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s).strip().lower())


def dedupe_key(normalized: dict) -> str:
    """A deterministic string key useful for in-batch dedupe before persistence."""
    src = _norm(normalized.get("source")) or "manual"
    sid = _norm(normalized.get("source_id"))
    if sid:
        return f"{src}:{sid}"
    return f"name:{_norm(normalized.get('company_name'))}|role:{_norm(normalized.get('role'))}|loc:{_norm(normalized.get('location'))}"


async def find_duplicate(db, user_id: str, normalized: dict) -> Optional[dict]:
    """Return an existing opportunity that duplicates `normalized`, or None."""
    src = (normalized.get("source") or "").strip()
    sid = (normalized.get("source_id") or "").strip()

    if src and sid:
        existing = await db.opportunities.find_one(
            {"user_id": user_id, "source": src, "source_id": sid},
            {"_id": 0},
        )
        if existing:
            return existing

    # Fallback: company + role (+ location) case-insensitive equality.
    name = (normalized.get("company_name") or "").strip()
    role = (normalized.get("role") or "").strip()
    if not name or not role:
        return None
    query = {
        "user_id": user_id,
        "company_name": {"$regex": f"^{re.escape(name)}$", "$options": "i"},
        "role": {"$regex": f"^{re.escape(role)}$", "$options": "i"},
    }
    location = (normalized.get("location") or "").strip()
    if location:
        query["location"] = {"$regex": f"^{re.escape(location)}$", "$options": "i"}
    return await db.opportunities.find_one(query, {"_id": 0})
