"""Match-score endpoints. Deterministic by default; AI nuance is opt-in & cached."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from core.security import get_current_user
from models.match import MatchBreakdown, MatchResult
from services.match_compute import (
    compute_match as _compute,
    get_active_resume as _get_active_resume,
    get_resume_text as _get_resume_text,
)
from services.match_score import compute_breakdown, tfidf_cosine  # noqa: F401

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches", tags=["matches"])


# ---------------------------------------------------------------------------- #
# GET single match
# ---------------------------------------------------------------------------- #
@router.get("/opportunity/{opp_id}", response_model=MatchResult | None)
async def match_for_opportunity(
    opp_id: str,
    request: Request,
    tfidf: bool = Query(default=False),
    user: dict = Depends(get_current_user),
):
    db = request.app.state.db
    resume = await _get_active_resume(db, user["id"])
    if not resume:
        return None  # frontend treats this as "no resume uploaded"
    opp = await db.opportunities.find_one(
        {"id": opp_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return await _compute(db, user, resume, opp, with_tfidf=tfidf)


# ---------------------------------------------------------------------------- #
# GET batch — used by the opportunities table to render badges in one round-trip.
# ---------------------------------------------------------------------------- #
class BatchMatchItem(BaseModel):
    opportunity_id: str
    overall_score: float
    jaccard_score: float
    skill_score: float
    matched_count: int
    missing_count: int


@router.get("/batch", response_model=List[BatchMatchItem])
async def match_batch(
    request: Request,
    opportunity_ids: List[str] = Query(default=[]),
    user: dict = Depends(get_current_user),
):
    db = request.app.state.db
    if not opportunity_ids:
        return []
    resume = await _get_active_resume(db, user["id"])
    if not resume:
        return []

    out: List[BatchMatchItem] = []
    opps_cursor = db.opportunities.find(
        {"user_id": user["id"], "id": {"$in": opportunity_ids}}, {"_id": 0}
    )
    async for opp in opps_cursor:
        result = await _compute(db, user, resume, opp, with_tfidf=False)
        out.append(
            BatchMatchItem(
                opportunity_id=opp["id"],
                overall_score=result.overall_score,
                jaccard_score=result.jaccard_score,
                skill_score=result.breakdown.skill_score,
                matched_count=len(result.breakdown.matched_skills),
                missing_count=len(result.breakdown.missing_skills),
            )
        )
    return out


# ---------------------------------------------------------------------------- #
# AI nuance (opt-in, cached forever per (resume_id, opp_id))
# ---------------------------------------------------------------------------- #
AI_SYSTEM = (
    "You are a hiring analyst. Given a candidate's resume signals and a job opportunity, "
    "return JSON ONLY with: "
    "ai_score (number 0-100 representing overall fit), "
    "summary (<=60 words explaining strengths and risks). "
    "Do not include any other text."
)


@router.post("/opportunity/{opp_id}/ai", response_model=MatchResult)
async def ai_score(
    opp_id: str, request: Request, user: dict = Depends(get_current_user)
):
    db = request.app.state.db
    resume = await _get_active_resume(db, user["id"])
    if not resume:
        raise HTTPException(status_code=400, detail="Upload an active resume first.")
    opp = await db.opportunities.find_one(
        {"id": opp_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    existing = await db.match_results.find_one(
        {"user_id": user["id"], "resume_id": resume["id"], "opportunity_id": opp_id},
        {"_id": 0},
    )
    # If cached AI exists, return it.
    if existing and existing.get("ai_score") is not None:
        return MatchResult(**existing)

    # Make sure deterministic score exists.
    base = await _compute(db, user, resume, opp, with_tfidf=True)

    raw_text = await _get_resume_text(db, resume["id"], user["id"])
    parsed = resume.get("parsed") or {}

    prompt = (
        f"CANDIDATE SIGNALS:\n"
        f"- Skills: {', '.join(parsed.get('skills') or []) or 'unknown'}\n"
        f"- Years experience: {parsed.get('years_experience') or 'unknown'}\n"
        f"- AI seniority: {parsed.get('ai_seniority') or 'unknown'}\n"
        f"- Resume excerpt:\n{raw_text[:3000]}\n\n"
        f"OPPORTUNITY:\n"
        f"- Company: {opp.get('company_name')}\n"
        f"- Role: {opp.get('role')}\n"
        f"- Type: {opp.get('employment_type')} ({opp.get('work_mode') or 'N/A'})\n"
        f"- Required skills: {', '.join(opp.get('skills') or []) or 'unspecified'}\n"
        f"- Description: {opp.get('description') or 'N/A'}\n\n"
        "Return ONLY JSON with keys ai_score (0-100) and summary."
    )

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY is not configured.")
    chat = LlmChat(
        api_key=api_key,
        session_id=f"match-ai-{uuid.uuid4()}",
        system_message=AI_SYSTEM,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    try:
        raw = await chat.send_message(UserMessage(text=prompt))
    except Exception as exc:
        logger.exception("AI match failed")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    import json
    import re as _re

    body = raw if isinstance(raw, str) else str(raw)
    m = _re.search(r"\{.*\}", body, _re.DOTALL)
    if not m:
        raise HTTPException(status_code=502, detail="LLM did not return JSON.")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Bad LLM JSON: {exc}") from exc

    ai_score_val = max(0.0, min(100.0, float(data.get("ai_score", 0))))
    summary = (data.get("summary") or "")[:600]

    base.ai_score = ai_score_val
    base.ai_summary = summary
    base.ai_enriched_at = datetime.now(timezone.utc).isoformat()
    await db.match_results.update_one(
        {
            "user_id": user["id"],
            "resume_id": resume["id"],
            "opportunity_id": opp_id,
        },
        {"$set": base.model_dump()},
        upsert=True,
    )
    return base
