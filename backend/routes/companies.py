"""Company routes - scoped to the authenticated user (Leads pipeline)."""

from __future__ import annotations

import csv
import io
import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from core.security import get_current_user
from models.company import Company, CompanyCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])


def _db(request: Request):
    return request.app.state.db


@router.get("", response_model=List[Company])
async def list_companies(
    request: Request,
    search: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
):
    db = _db(request)
    query: dict = {"user_id": user["id"]}
    if search:
        query["company_name"] = {"$regex": re.escape(search), "$options": "i"}

    cursor = db.companies.find(query, {"_id": 0}).sort("created_at", -1).limit(1000)
    docs = await cursor.to_list(length=1000)
    return [Company(**doc) for doc in docs]


@router.post("", response_model=Company, status_code=201)
async def create_company(
    payload: CompanyCreate,
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = _db(request)
    company = Company(
        company_name=payload.company_name.strip(),
        website=(payload.website or "").strip() or None,
        email=(payload.email or None),
    )
    doc = company.model_dump()
    doc["user_id"] = user["id"]
    await db.companies.insert_one(doc)
    return company


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = _db(request)
    result = await db.companies.delete_one({"id": company_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    return None


@router.get("/stats")
async def stats(request: Request, user: dict = Depends(get_current_user)):
    db = _db(request)
    base = {"user_id": user["id"]}
    total = await db.companies.count_documents(base)
    with_email = await db.companies.count_documents({**base, "email": {"$nin": [None, ""]}})
    with_website = await db.companies.count_documents({**base, "website": {"$nin": [None, ""]}})
    return {"total": total, "with_email": with_email, "with_website": with_website}


@router.get("/export.csv")
async def export_csv(request: Request, user: dict = Depends(get_current_user)):
    db = _db(request)
    cursor = (
        db.companies.find({"user_id": user["id"]}, {"_id": 0})
        .sort("created_at", -1)
        .limit(10_000)
    )
    docs = await cursor.to_list(length=10_000)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "company_name", "website", "email", "created_at"])
    for d in docs:
        writer.writerow(
            [
                d.get("id", ""),
                d.get("company_name", ""),
                d.get("website") or "",
                d.get("email") or "",
                d.get("created_at", ""),
            ]
        )

    buffer.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="companies.csv"'}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)
