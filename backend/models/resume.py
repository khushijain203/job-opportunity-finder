"""Resume domain models.

Raw text and structured (parsed) fields are stored separately so future re-parsing
or AI enrichment can run without re-extracting bytes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ParsedResume(BaseModel):
    """Deterministic, regex-based extraction. AI enrichment populates `ai_*` fields."""

    skills: List[str] = Field(default_factory=list)
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    experiences: List[str] = Field(default_factory=list)
    years_experience: Optional[float] = None
    # AI-enriched (one-shot per resume, cached forever):
    ai_summary: Optional[str] = None
    ai_skills: List[str] = Field(default_factory=list)
    ai_seniority: Optional[str] = None
    ai_top_roles: List[str] = Field(default_factory=list)
    ai_enriched_at: Optional[str] = None


class Resume(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    original_filename: str
    storage_path: str
    content_type: str
    size: int
    uploaded_at: str = Field(default_factory=_now_iso)
    is_active: bool = True  # newest active = the "current" resume
    is_deleted: bool = False
    parsed: ParsedResume = Field(default_factory=ParsedResume)
    raw_text_chars: int = 0  # quick sanity stat - full text stored separately


class ResumeRawText(BaseModel):
    """Stored in a SEPARATE collection so we can refactor parsing without re-uploading."""

    resume_id: str
    user_id: str
    text: str
    stored_at: str = Field(default_factory=_now_iso)


class ResumePublic(BaseModel):
    """Shape returned to the frontend (no raw text, no storage path)."""

    id: str
    original_filename: str
    content_type: str
    size: int
    uploaded_at: str
    is_active: bool
    raw_text_chars: int
    parsed: ParsedResume
