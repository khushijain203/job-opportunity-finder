"""Opportunity domain models.

Represents a discovered role / internship that can later be saved into Leads.
Designed to extend cleanly for future ingestion sources (job boards, scrapers, etc.).
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Allowed values – kept as plain Literals at the route layer to keep the model
# permissive enough for new sources/statuses in future phases.
EMPLOYMENT_TYPES = ("Internship", "Full Time")
WORK_MODES = ("Remote", "Hybrid", "Onsite")
STATUSES = ("New", "Applied", "Rejected", "Interview")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OpportunityCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = Field(default=None, max_length=200)
    employment_type: str = Field(..., description="Internship | Full Time")
    work_mode: Optional[str] = Field(default=None, description="Remote | Hybrid | Onsite")
    skills: List[str] = Field(default_factory=list)
    source: Optional[str] = Field(default=None, max_length=200)
    apply_link: Optional[str] = Field(default=None, max_length=1000)
    company_website: Optional[str] = Field(default=None, max_length=500)
    contact_email: Optional[EmailStr] = None
    description: Optional[str] = Field(default=None, max_length=4000)


class OpportunityStatusUpdate(BaseModel):
    status: str  # one of STATUSES


class Opportunity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    role: str
    location: Optional[str] = None
    employment_type: str
    work_mode: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    apply_link: Optional[str] = None
    company_website: Optional[str] = None
    contact_email: Optional[str] = None
    description: Optional[str] = None
    date_found: str = Field(default_factory=_now_iso)
    status: str = "New"
