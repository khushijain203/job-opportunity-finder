"""Opportunity routes - scoped to the authenticated user."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from core.security import get_current_user
from models.opportunity import (
    EMPLOYMENT_TYPES,
    Opportunity,
    OpportunityCreate,
    OpportunityStatusUpdate,
    STATUSES,
    WORK_MODES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _db(request: Request):
    return request.app.state.db


# ---------------------------------------------------------------------------- #
# Seed data (per user, idempotent if user already has opportunities)
# ---------------------------------------------------------------------------- #
SEED_OPPORTUNITIES: List[dict] = [
    {
        "company_name": "Northwind Analytics",
        "role": "Business Analyst Intern",
        "location": "Bengaluru, IN",
        "employment_type": "Internship",
        "work_mode": "Hybrid",
        "skills": ["SQL", "Excel", "Tableau", "Stakeholder Communication"],
        "source": "LinkedIn",
        "apply_link": "https://example.com/apply/northwind-ba-intern",
        "company_website": "https://northwind.example.com",
        "contact_email": "careers@northwind.example.com",
        "description": "Support the analytics team in building dashboards and producing weekly business reviews.",
    },
    {
        "company_name": "Lumen Data Labs",
        "role": "Data Analyst Intern",
        "location": "Remote",
        "employment_type": "Internship",
        "work_mode": "Remote",
        "skills": ["Python", "Pandas", "SQL", "Statistics"],
        "source": "Wellfound",
        "apply_link": "https://example.com/apply/lumen-da-intern",
        "company_website": "https://lumenlabs.example.com",
        "contact_email": "talent@lumenlabs.example.com",
        "description": "Build product analytics pipelines and uncover insights from user behavior data.",
    },
    {
        "company_name": "Quanta QA",
        "role": "QA Automation Intern",
        "location": "Pune, IN",
        "employment_type": "Internship",
        "work_mode": "Onsite",
        "skills": ["Selenium", "Python", "PyTest", "CI/CD"],
        "source": "Indeed",
        "apply_link": "https://example.com/apply/quanta-qa-intern",
        "company_website": "https://quantaqa.example.com",
        "contact_email": "hiring@quantaqa.example.com",
        "description": "Write and maintain regression suites for our flagship SaaS platform.",
    },
    {
        "company_name": "ScriptForge",
        "role": "Python Automation Intern",
        "location": "Remote",
        "employment_type": "Internship",
        "work_mode": "Remote",
        "skills": ["Python", "Playwright", "REST APIs", "Linux"],
        "source": "Internshala",
        "apply_link": "https://example.com/apply/scriptforge-py-intern",
        "company_website": "https://scriptforge.example.com",
        "contact_email": "intern@scriptforge.example.com",
        "description": "Automate internal workflows and integrate third-party APIs end-to-end.",
    },
    {
        "company_name": "Veritest Systems",
        "role": "Software Testing Intern",
        "location": "Hyderabad, IN",
        "employment_type": "Internship",
        "work_mode": "Hybrid",
        "skills": ["Manual Testing", "JIRA", "Test Cases", "API Testing"],
        "source": "Company Website",
        "apply_link": "https://example.com/apply/veritest-st-intern",
        "company_website": "https://veritest.example.com",
        "contact_email": "people@veritest.example.com",
        "description": "Own end-to-end testing for new features in our supply-chain product.",
    },
]


# ---------------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------------- #
def _safe_regex(value: str) -> dict:
    return {"$regex": re.escape(value), "$options": "i"}


def _validate_enum(value: Optional[str], allowed: tuple[str, ...], field: str) -> None:
    if value is not None and value not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {field}: '{value}'. Must be one of {list(allowed)}.",
        )


def _build_query(
    user_id: str,
    search: Optional[str],
    role: Optional[str],
    location: Optional[str],
    skills: Optional[List[str]],
    employment_type: Optional[str],
    work_mode: Optional[str],
    status: Optional[str],
) -> dict:
    q: dict = {"user_id": user_id}
    if search:
        q["company_name"] = _safe_regex(search)
    if role:
        q["role"] = _safe_regex(role)
    if location:
        q["location"] = _safe_regex(location)
    if employment_type:
        q["employment_type"] = employment_type
    if work_mode:
        q["work_mode"] = work_mode
    if status:
        q["status"] = status
    if skills:
        q["skills"] = {"$in": [re.compile(re.escape(s), re.IGNORECASE) for s in skills if s.strip()]}
    return q


SORT_MAP = {
    "newest": [("date_found", -1)],
    "oldest": [("date_found", 1)],
    "company_az": [("company_name", 1)],
    "company_za": [("company_name", -1)],
    "role_az": [("role", 1)],
}


# ---------------------------------------------------------------------------- #
# Endpoints
# ---------------------------------------------------------------------------- #
@router.get("/meta")
async def meta():
    return {
        "employment_types": list(EMPLOYMENT_TYPES),
        "work_modes": list(WORK_MODES),
        "statuses": list(STATUSES),
        "sort_options": list(SORT_MAP.keys()),
    }


@router.get("", response_model=List[Opportunity])
async def list_opportunities(
    request: Request,
    search: Optional[str] = Query(default=None),
    role: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    skills: Optional[List[str]] = Query(default=None),
    employment_type: Optional[str] = Query(default=None),
    work_mode: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    sort: str = Query(default="newest"),
    user: dict = Depends(get_current_user),
):
    _validate_enum(employment_type, EMPLOYMENT_TYPES, "employment_type")
    _validate_enum(work_mode, WORK_MODES, "work_mode")
    _validate_enum(status, STATUSES, "status")
    if sort not in SORT_MAP:
        raise HTTPException(status_code=422, detail=f"Invalid sort. Use one of {list(SORT_MAP)}.")

    db = _db(request)
    q = _build_query(user["id"], search, role, location, skills, employment_type, work_mode, status)
    cursor = db.opportunities.find(q, {"_id": 0}).sort(SORT_MAP[sort]).limit(1000)
    docs = await cursor.to_list(length=1000)
    return [Opportunity(**d) for d in docs]


@router.post("", response_model=Opportunity, status_code=201)
async def create_opportunity(
    payload: OpportunityCreate,
    request: Request,
    user: dict = Depends(get_current_user),
):
    _validate_enum(payload.employment_type, EMPLOYMENT_TYPES, "employment_type")
    _validate_enum(payload.work_mode, WORK_MODES, "work_mode")
    db = _db(request)
    opp = Opportunity(**payload.model_dump())
    doc = opp.model_dump()
    doc["user_id"] = user["id"]
    await db.opportunities.insert_one(doc)
    return opp


@router.delete("/{opp_id}", status_code=204)
async def delete_opportunity(
    opp_id: str, request: Request, user: dict = Depends(get_current_user)
):
    db = _db(request)
    result = await db.opportunities.delete_one({"id": opp_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return None


@router.patch("/{opp_id}/status", response_model=Opportunity)
async def update_status(
    opp_id: str,
    payload: OpportunityStatusUpdate,
    request: Request,
    user: dict = Depends(get_current_user),
):
    _validate_enum(payload.status, STATUSES, "status")
    db = _db(request)
    result = await db.opportunities.find_one_and_update(
        {"id": opp_id, "user_id": user["id"]},
        {"$set": {"status": payload.status}},
        projection={"_id": 0},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return Opportunity(**result)


@router.post("/{opp_id}/save-to-leads")
async def save_to_leads(
    opp_id: str, request: Request, user: dict = Depends(get_current_user)
):
    db = _db(request)
    opp = await db.opportunities.find_one({"id": opp_id, "user_id": user["id"]}, {"_id": 0})
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    name = opp["company_name"].strip()
    existing = await db.companies.find_one(
        {
            "user_id": user["id"],
            "company_name": {"$regex": f"^{re.escape(name)}$", "$options": "i"},
        },
        {"_id": 0},
    )
    if existing:
        return {"created": False, "company": existing, "message": "Lead already exists"}

    company = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "company_name": name,
        "website": opp.get("company_website"),
        "email": opp.get("contact_email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.companies.insert_one(company)
    company.pop("_id", None)
    return {"created": True, "company": company, "message": "Saved to Leads"}


@router.post("/seed")
async def seed(request: Request, user: dict = Depends(get_current_user)):
    """Insert sample opportunities for THIS user (idempotent per user)."""
    db = _db(request)
    existing = await db.opportunities.count_documents({"user_id": user["id"]})
    if existing > 0:
        return {"inserted": 0, "message": f"Skipped – you already have {existing} opportunities."}

    docs = []
    for raw in SEED_OPPORTUNITIES:
        opp = Opportunity(**raw)
        d = opp.model_dump()
        d["user_id"] = user["id"]
        docs.append(d)
    await db.opportunities.insert_many(docs)
    return {"inserted": len(docs), "message": "Seeded sample opportunities."}
