"""Resume upload / list / parse / enrich routes.  All scoped to current_user."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel

from core.security import get_current_user
from core.storage import get_object, make_path, put_object
from models.resume import ParsedResume, Resume, ResumePublic, ResumeRawText
from services.resume_parser import extract_text, parse_resume_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])

MAX_RESUME_SIZE = 6 * 1024 * 1024  # 6 MB hard cap
SUPPORTED_EXTS = {"pdf", "docx", "txt"}


def _ext_of(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _public(resume: dict) -> ResumePublic:
    parsed = resume.get("parsed") or {}
    return ResumePublic(
        id=resume["id"],
        original_filename=resume.get("original_filename", ""),
        content_type=resume.get("content_type", ""),
        size=resume.get("size", 0),
        uploaded_at=resume.get("uploaded_at", ""),
        is_active=resume.get("is_active", True),
        raw_text_chars=resume.get("raw_text_chars", 0),
        parsed=ParsedResume(**parsed),
    )


# ---------------------------------------------------------------------------- #
# Upload
# ---------------------------------------------------------------------------- #
@router.post("/upload", response_model=ResumePublic, status_code=201)
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    db = request.app.state.db
    ext = _ext_of(file.filename or "")
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(status_code=415, detail="Upload a PDF, DOCX, or TXT resume.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="File is empty.")
    if len(data) > MAX_RESUME_SIZE:
        raise HTTPException(
            status_code=413, detail=f"File too large. Max {MAX_RESUME_SIZE // 1024 // 1024} MB."
        )

    # 1. Extract text locally (fast, no LLM).
    try:
        text = extract_text(file.filename, file.content_type or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    # 2. Store the raw file in object storage.
    file_uuid = str(uuid.uuid4())
    storage_path = make_path(user["id"], file_uuid, ext)
    try:
        put_object(storage_path, data, file.content_type or "application/octet-stream")
    except Exception as exc:
        logger.exception("Storage upload failed")
        raise HTTPException(status_code=502, detail=f"Storage upload failed: {exc}") from exc

    # 3. Parse deterministically and persist (raw text in its own collection).
    parsed_dict = parse_resume_text(text)
    parsed = ParsedResume(**parsed_dict)

    resume = Resume(
        user_id=user["id"],
        original_filename=file.filename or f"resume.{ext}",
        storage_path=storage_path,
        content_type=file.content_type or "application/octet-stream",
        size=len(data),
        parsed=parsed,
        raw_text_chars=len(text),
    )

    # Mark this as the active resume; deactivate any previous.
    await db.resumes.update_many({"user_id": user["id"]}, {"$set": {"is_active": False}})
    await db.resumes.insert_one(resume.model_dump())
    await db.resume_texts.insert_one(
        ResumeRawText(resume_id=resume.id, user_id=user["id"], text=text).model_dump()
    )

    # Invalidate any cached match scores tied to a previous resume for this user.
    await db.match_results.delete_many({"user_id": user["id"]})

    # Auto-update the Profile with newly mined skills if it's empty.
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if profile is None or not (profile.get("skills") or []):
        skills_to_save = parsed.skills[:30]
        update_doc = {
            "user_id": user["id"],
            "skills": skills_to_save,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if parsed.years_experience is not None and not (profile or {}).get("years_experience"):
            update_doc["years_experience"] = parsed.years_experience
        await db.profiles.update_one(
            {"user_id": user["id"]}, {"$set": update_doc}, upsert=True
        )

    return _public(resume.model_dump())


# ---------------------------------------------------------------------------- #
# List / get / activate / delete
# ---------------------------------------------------------------------------- #
@router.get("", response_model=List[ResumePublic])
async def list_resumes(request: Request, user: dict = Depends(get_current_user)):
    db = request.app.state.db
    docs = await db.resumes.find(
        {"user_id": user["id"], "is_deleted": {"$ne": True}}, {"_id": 0}
    ).sort("uploaded_at", -1).to_list(length=50)
    return [_public(d) for d in docs]


@router.get("/active", response_model=ResumePublic | None)
async def get_active(request: Request, user: dict = Depends(get_current_user)):
    db = request.app.state.db
    doc = await db.resumes.find_one(
        {"user_id": user["id"], "is_active": True, "is_deleted": {"$ne": True}},
        {"_id": 0},
    )
    return _public(doc) if doc else None


@router.post("/{resume_id}/activate", response_model=ResumePublic)
async def set_active(
    resume_id: str, request: Request, user: dict = Depends(get_current_user)
):
    db = request.app.state.db
    target = await db.resumes.find_one(
        {"id": resume_id, "user_id": user["id"], "is_deleted": {"$ne": True}},
        {"_id": 0},
    )
    if not target:
        raise HTTPException(status_code=404, detail="Resume not found")
    await db.resumes.update_many(
        {"user_id": user["id"]}, {"$set": {"is_active": False}}
    )
    await db.resumes.update_one({"id": resume_id}, {"$set": {"is_active": True}})
    await db.match_results.delete_many({"user_id": user["id"]})
    target["is_active"] = True
    return _public(target)


@router.delete("/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: str, request: Request, user: dict = Depends(get_current_user)
):
    db = request.app.state.db
    res = await db.resumes.update_one(
        {"id": resume_id, "user_id": user["id"]},
        {"$set": {"is_deleted": True, "is_active": False}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Resume not found")
    # Drop cached matches tied to this resume.
    await db.match_results.delete_many({"resume_id": resume_id, "user_id": user["id"]})
    return None


@router.get("/{resume_id}/download")
async def download_resume(
    resume_id: str, request: Request, user: dict = Depends(get_current_user)
):
    db = request.app.state.db
    doc = await db.resumes.find_one(
        {"id": resume_id, "user_id": user["id"], "is_deleted": {"$ne": True}},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    try:
        content, ct = get_object(doc["storage_path"])
    except Exception as exc:
        logger.exception("Resume download failed")
        raise HTTPException(status_code=502, detail="Storage download failed") from exc
    headers = {
        "Content-Disposition": f'attachment; filename="{doc.get("original_filename", "resume")}"'
    }
    return Response(content=content, media_type=ct or doc.get("content_type", "application/octet-stream"), headers=headers)


# ---------------------------------------------------------------------------- #
# AI enrichment - one-shot per resume, cached forever.
# ---------------------------------------------------------------------------- #
ENRICH_SYSTEM = (
    "You convert raw resume text into compact structured signals for a job-matching app. "
    "Return JSON ONLY with these keys: "
    "summary (<=60 words), seniority (one of intern/junior/mid/senior/lead), "
    "skills (array of <=25 lowercase strings), top_roles (array of <=5 strings). "
    "Never include any other text."
)


class EnrichResumeResponse(BaseModel):
    id: str
    ai_summary: str | None = None
    ai_seniority: str | None = None
    ai_skills: list[str] = []
    ai_top_roles: list[str] = []
    ai_enriched_at: str | None = None


@router.post("/{resume_id}/enrich", response_model=EnrichResumeResponse)
async def enrich_resume(
    resume_id: str, request: Request, user: dict = Depends(get_current_user)
):
    db = request.app.state.db
    doc = await db.resumes.find_one(
        {"id": resume_id, "user_id": user["id"], "is_deleted": {"$ne": True}},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Cache: if already enriched, return cached result.
    parsed = doc.get("parsed") or {}
    if parsed.get("ai_enriched_at"):
        return EnrichResumeResponse(
            id=resume_id,
            ai_summary=parsed.get("ai_summary"),
            ai_seniority=parsed.get("ai_seniority"),
            ai_skills=parsed.get("ai_skills", []),
            ai_top_roles=parsed.get("ai_top_roles", []),
            ai_enriched_at=parsed.get("ai_enriched_at"),
        )

    raw = await db.resume_texts.find_one({"resume_id": resume_id, "user_id": user["id"]}, {"_id": 0})
    if not raw or not raw.get("text"):
        raise HTTPException(status_code=400, detail="No raw text available for enrichment.")

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY is not configured.")
    chat = LlmChat(
        api_key=api_key,
        session_id=f"resume-enrich-{resume_id}",
        system_message=ENRICH_SYSTEM,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    text = raw["text"][:8000]
    try:
        response = await chat.send_message(UserMessage(text=text))
    except Exception as exc:
        logger.exception("Resume enrichment failed")
        raise HTTPException(status_code=502, detail=f"LLM enrichment failed: {exc}") from exc

    import json
    import re as _re

    body = response if isinstance(response, str) else str(response)
    json_match = _re.search(r"\{.*\}", body, _re.DOTALL)
    if not json_match:
        raise HTTPException(status_code=502, detail="LLM did not return JSON.")
    try:
        data = json.loads(json_match.group(0))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Bad LLM JSON: {exc}") from exc

    enriched = {
        "parsed.ai_summary": (data.get("summary") or "")[:600],
        "parsed.ai_seniority": data.get("seniority"),
        "parsed.ai_skills": [str(s).lower().strip() for s in (data.get("skills") or [])][:25],
        "parsed.ai_top_roles": [str(r) for r in (data.get("top_roles") or [])][:5],
        "parsed.ai_enriched_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.resumes.update_one({"id": resume_id, "user_id": user["id"]}, {"$set": enriched})

    return EnrichResumeResponse(
        id=resume_id,
        ai_summary=enriched["parsed.ai_summary"],
        ai_seniority=enriched["parsed.ai_seniority"],
        ai_skills=enriched["parsed.ai_skills"],
        ai_top_roles=enriched["parsed.ai_top_roles"],
        ai_enriched_at=enriched["parsed.ai_enriched_at"],
    )
