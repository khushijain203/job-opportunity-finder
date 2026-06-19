"""Company domain models.

Pydantic models used by the API & persisted into MongoDB.
Designed to be easily extended in later phases (scoring, enrichment, etc.).
"""

from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


def _now_iso() -> str:
    """Return an ISO-8601 UTC timestamp string (Mongo-friendly)."""
    return datetime.now(timezone.utc).isoformat()


class CompanyCreate(BaseModel):
    """Payload accepted from the client when creating a lead."""

    company_name: str = Field(..., min_length=1, max_length=200)
    website: Optional[str] = Field(default=None, max_length=500)
    email: Optional[EmailStr] = None


class Company(BaseModel):
    """Full company record returned by the API."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    website: Optional[str] = None
    email: Optional[str] = None
    created_at: str = Field(default_factory=_now_iso)
