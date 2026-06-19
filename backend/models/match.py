"""Match score model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MatchBreakdown(BaseModel):
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    extra_skills: List[str] = Field(default_factory=list)
    skill_score: float = 0.0
    role_relevance: float = 0.0
    role_explanation: str = ""
    experience_relevance: float = 0.0
    experience_explanation: str = ""
    location_relevance: float = 0.0
    location_explanation: str = ""


class MatchResult(BaseModel):
    """Cached per (user_id, resume_id, opportunity_id)."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    resume_id: str
    opportunity_id: str
    overall_score: float = 0.0          # weighted Jaccard-based (0..1)
    jaccard_score: float = 0.0
    tfidf_score: float = 0.0
    breakdown: MatchBreakdown = Field(default_factory=MatchBreakdown)
    ai_score: Optional[float] = None     # populated only after AI enrichment
    ai_summary: Optional[str] = None
    ai_enriched_at: Optional[str] = None
    computed_at: str = Field(default_factory=_now_iso)
