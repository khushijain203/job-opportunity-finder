"""Generated outreach email history – per user."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generated-emails", tags=["generated_emails"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class GeneratedEmail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    opportunity_id: Optional[str] = None
    company_name: Optional[str] = None
    role: Optional[str] = None
    to: Optional[str] = None
    subject: str
    body: str
    created_at: str = Field(default_factory=_now_iso)


@router.get("", response_model=List[GeneratedEmail])
async def list_emails(
    request: Request,
    opportunity_id: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
):
    db = request.app.state.db
    q: dict = {"user_id": user["id"]}
    if opportunity_id:
        q["opportunity_id"] = opportunity_id
    cursor = db.generated_emails.find(q, {"_id": 0}).sort("created_at", -1).limit(200)
    docs = await cursor.to_list(length=200)
    return [GeneratedEmail(**d) for d in docs]


@router.delete("/{email_id}", status_code=204)
async def delete_email(email_id: str, request: Request, user: dict = Depends(get_current_user)):
    db = request.app.state.db
    res = await db.generated_emails.delete_one({"id": email_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Email not found")
    return None
