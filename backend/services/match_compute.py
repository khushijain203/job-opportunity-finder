"""Match-score computation service - shared between /matches and /ingest routes.

Extracted from routes/matches.py so ingestion can auto-compute scores without
a circular import.
"""

from __future__ import annotations

import logging
from typing import Optional

from models.match import MatchBreakdown, MatchResult
from services.match_score import compute_breakdown, tfidf_cosine

logger = logging.getLogger(__name__)


async def get_active_resume(db, user_id: str) -> Optional[dict]:
    return await db.resumes.find_one(
        {"user_id": user_id, "is_active": True, "is_deleted": {"$ne": True}},
        {"_id": 0},
    )


async def get_resume_text(db, resume_id: str, user_id: str) -> str:
    doc = await db.resume_texts.find_one(
        {"resume_id": resume_id, "user_id": user_id}, {"_id": 0}
    )
    return (doc or {}).get("text") or ""


async def compute_match(
    db, user: dict, resume: dict, opp: dict, *, with_tfidf: bool = False
) -> MatchResult:
    """Compute (or fetch cached) match between this resume and opportunity."""
    cached = await db.match_results.find_one(
        {
            "user_id": user["id"],
            "resume_id": resume["id"],
            "opportunity_id": opp["id"],
        },
        {"_id": 0},
    )
    if cached and (not with_tfidf or cached.get("tfidf_score", 0) > 0):
        return MatchResult(**cached)

    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    parsed = resume.get("parsed") or {}
    resume_skills = list(
        {
            *(parsed.get("skills") or []),
            *(parsed.get("ai_skills") or []),
            *(profile.get("skills") or []),
        }
    )

    raw_text = await get_resume_text(db, resume["id"], user["id"])

    breakdown = compute_breakdown(
        resume_text=raw_text,
        resume_skills=resume_skills,
        years_experience=parsed.get("years_experience") or profile.get("years_experience"),
        preferred_roles=profile.get("preferred_roles") or [],
        preferred_locations=profile.get("preferred_locations") or [],
        opp_role=opp.get("role") or "",
        opp_skills=opp.get("skills") or [],
        opp_employment_type=opp.get("employment_type") or "",
        opp_location=opp.get("location"),
        opp_work_mode=opp.get("work_mode"),
    )

    tfidf = 0.0
    if with_tfidf:
        opp_text = " ".join(
            filter(
                None,
                [
                    opp.get("role"),
                    opp.get("description"),
                    " ".join(opp.get("skills") or []),
                    opp.get("company_name"),
                ],
            )
        )
        tfidf = tfidf_cosine(raw_text, opp_text)

    result = MatchResult(
        user_id=user["id"],
        resume_id=resume["id"],
        opportunity_id=opp["id"],
        overall_score=breakdown["overall_score"],
        jaccard_score=breakdown["jaccard_score"],
        tfidf_score=tfidf,
        breakdown=MatchBreakdown(**breakdown["breakdown"]),
        ai_score=(cached or {}).get("ai_score"),
        ai_summary=(cached or {}).get("ai_summary"),
        ai_enriched_at=(cached or {}).get("ai_enriched_at"),
    )

    await db.match_results.update_one(
        {
            "user_id": user["id"],
            "resume_id": resume["id"],
            "opportunity_id": opp["id"],
        },
        {"$set": result.model_dump()},
        upsert=True,
    )
    return result


async def compute_matches_for_opportunities(
    db, user: dict, opportunity_ids: list[str]
) -> int:
    """Compute deterministic matches for a list of opp ids. Returns count computed."""
    if not opportunity_ids:
        return 0
    resume = await get_active_resume(db, user["id"])
    if not resume:
        return 0
    cursor = db.opportunities.find(
        {"user_id": user["id"], "id": {"$in": opportunity_ids}}, {"_id": 0}
    )
    count = 0
    async for opp in cursor:
        try:
            await compute_match(db, user, resume, opp, with_tfidf=False)
            count += 1
        except Exception:
            logger.exception("Auto-match failed for opp %s", opp.get("id"))
    return count
