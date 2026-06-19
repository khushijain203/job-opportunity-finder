"""Opportunity routes - discovery pipeline core.

Endpoints (all under /api/opportunities):
    GET    /                          - list w/ filters, search, sort
    POST   /                          - create
    DELETE /{id}                      - delete
    PATCH  /{id}/status               - update status
    POST   /{id}/save-to-leads        - copy company info into Leads
    POST   /seed                      - one-shot demo data loader (idempotent)
    GET    /meta                      - enums (employment_type, work_mode, status)

Designed to be extended later with sources like:
    /sources/crunchbase, /sources/ycombinator, /sources/jobboard, etc.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

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
# Seed data – used only when collection is empty (idempotent demo loader).
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
    """Case-insensitive partial regex match, with input escaped."""
    return {"$regex": re.escape(value), "$options": "i"}


def _validate_enum(value: Optional[str], allowed: tuple[str, ...], field: str) -> None:
    if value is not None and value not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {field}: '{value}'. Must be one of {list(allowed)}.",
        )


def _build_query(
    search: Optional[str],
    role: Optional[str],
    location: Optional[str],
    skills: Optional[List[str]],
    employment_type: Optional[str],
    work_mode: Optional[str],
    status: Optional[str],
) -> dict:
    q: dict = {}
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
        # Match if any of the requested skills appears in opportunity skills (case-insensitive).
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
):
    _validate_enum(employment_type, EMPLOYMENT_TYPES, "employment_type")
    _validate_enum(work_mode, WORK_MODES, "work_mode")
    _validate_enum(status, STATUSES, "status")
    if sort not in SORT_MAP:
        raise HTTPException(status_code=422, detail=f"Invalid sort. Use one of {list(SORT_MAP)}.")

    db = _db(request)
    q = _build_query(search, role, location, skills, employment_type, work_mode, status)
    cursor = db.opportunities.find(q, {"_id": 0}).sort(SORT_MAP[sort]).limit(1000)
    docs = await cursor.to_list(length=1000)
    return [Opportunity(**d) for d in docs]


@router.post("", response_model=Opportunity, status_code=201)
async def create_opportunity(payload: OpportunityCreate, request: Request):
    _validate_enum(payload.employment_type, EMPLOYMENT_TYPES, "employment_type")
    _validate_enum(payload.work_mode, WORK_MODES, "work_mode")
    db = _db(request)
    opp = Opportunity(**payload.model_dump())
    await db.opportunities.insert_one(opp.model_dump())
    logger.info("Created opportunity id=%s company=%s", opp.id, opp.company_name)
    return opp


@router.delete("/{opp_id}", status_code=204)
async def delete_opportunity(opp_id: str, request: Request):
    db = _db(request)
    result = await db.opportunities.delete_one({"id": opp_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return None


@router.patch("/{opp_id}/status", response_model=Opportunity)
async def update_status(opp_id: str, payload: OpportunityStatusUpdate, request: Request):
    _validate_enum(payload.status, STATUSES, "status")
    db = _db(request)
    result = await db.opportunities.find_one_and_update(
        {"id": opp_id},
        {"$set": {"status": payload.status}},
        projection={"_id": 0},
        return_document=True,  # pymongo.ReturnDocument.AFTER == True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return Opportunity(**result)


@router.post("/{opp_id}/save-to-leads")
async def save_to_leads(opp_id: str, request: Request):
    """Create / upsert a Company in the Leads module using this opportunity's info."""
    db = _db(request)
    opp = await db.opportunities.find_one({"id": opp_id}, {"_id": 0})
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    name = opp["company_name"].strip()
    # Check for existing lead by case-insensitive name match.
    existing = await db.companies.find_one(
        {"company_name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}},
        {"_id": 0},
    )
    if existing:
        return {"created": False, "company": existing, "message": "Lead already exists"}

    company = {
        "id": str(uuid.uuid4()),
        "company_name": name,
        "website": opp.get("company_website"),
        "email": opp.get("contact_email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.companies.insert_one(company)
    logger.info("Saved opportunity %s to Leads as company %s", opp_id, company["id"])
    # Strip ObjectId injected by motor before serializing.
    company.pop("_id", None)
    return {"created": True, "company": company, "message": "Saved to Leads"}


@router.post("/seed")
async def seed(request: Request):
    """Insert demo opportunities only if the collection is empty (idempotent)."""
    db = _db(request)
    existing = await db.opportunities.count_documents({})
    if existing > 0:
        return {"inserted": 0, "message": f"Skipped – collection already has {existing} records."}

    docs = []
    for raw in SEED_OPPORTUNITIES:
        opp = Opportunity(**raw)
        docs.append(opp.model_dump())
    await db.opportunities.insert_many(docs)
    logger.info("Seeded %d opportunities", len(docs))
    return {"inserted": len(docs), "message": "Seeded sample opportunities."}
