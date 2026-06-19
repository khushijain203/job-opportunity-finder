"""Outreach email generation using Claude Sonnet 4.5. Scoped per user; persists history."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/outreach", tags=["outreach"])


class GenerateEmailRequest(BaseModel):
    opportunity_id: str
    sender_name: Optional[str] = Field(default=None, max_length=120)
    sender_role: Optional[str] = Field(default=None, max_length=200)
    sender_pitch: Optional[str] = Field(default=None, max_length=1500)
    tone: Optional[str] = Field(default="warm and professional", max_length=80)


class GenerateEmailResponse(BaseModel):
    id: str
    opportunity_id: str
    to: Optional[str] = None
    subject: str
    body: str
    created_at: str


SYSTEM_PROMPT = (
    "You write concise, personalized outreach emails from a candidate to a "
    "company about a specific role. The output MUST be plain text with the "
    "first line being a subject prefixed with 'Subject: ', followed by a blank "
    "line, followed by the email body. Keep the body under 180 words. No "
    "markdown, no headers, no lists, no signature placeholders other than the "
    "sender name supplied. Be specific about the role, the company, and 1-2 "
    "skills relevant to the opportunity. Sound human, not templated."
)


def _build_user_prompt(opp: dict, req: GenerateEmailRequest, profile: Optional[dict]) -> str:
    sender_name = req.sender_name or (profile or {}).get("full_name") or "[Your Name]"
    sender_role = req.sender_role or "candidate"
    sender_pitch = req.sender_pitch or (
        "I have hands-on project experience and I'm eager to contribute and learn."
    )
    skills = ", ".join(opp.get("skills") or []) or "the listed skills"

    profile_block = ""
    if profile:
        my_skills = profile.get("skills") or []
        if my_skills:
            profile_block = f"\nCandidate's own skills: {', '.join(my_skills)}\n"

    return (
        f"Write an outreach email in a {req.tone} tone.\n\n"
        f"Opportunity:\n"
        f"- Company: {opp.get('company_name')}\n"
        f"- Role: {opp.get('role')}\n"
        f"- Location: {opp.get('location') or 'N/A'}\n"
        f"- Employment Type: {opp.get('employment_type')}\n"
        f"- Work Mode: {opp.get('work_mode') or 'N/A'}\n"
        f"- Required skills: {skills}\n"
        f"- Description: {opp.get('description') or 'N/A'}\n\n"
        f"Sender:\n"
        f"- Name: {sender_name}\n"
        f"- Current role / background: {sender_role}\n"
        f"- Pitch / highlights: {sender_pitch}"
        f"{profile_block}\n\n"
        "Now produce the email."
    )


def _parse_subject_body(text: str) -> tuple[str, str]:
    text = (text or "").strip()
    lines = text.splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).lstrip("\n").strip()
    else:
        subject = "Quick note re: opening"
        body = text
    return subject, body


@router.post("/generate", response_model=GenerateEmailResponse)
async def generate_outreach_email(
    payload: GenerateEmailRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = request.app.state.db
    opp = await db.opportunities.find_one(
        {"id": payload.opportunity_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY is not configured.")

    chat = LlmChat(
        api_key=api_key,
        session_id=f"outreach-{uuid.uuid4()}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    user_prompt = _build_user_prompt(opp, payload, profile)

    try:
        raw = await chat.send_message(UserMessage(text=user_prompt))
    except Exception as exc:
        logger.exception("LLM generation failed")
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {exc}") from exc

    text = raw if isinstance(raw, str) else str(raw)
    subject, body = _parse_subject_body(text)

    # Persist into generated_emails (per-user history).
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "opportunity_id": payload.opportunity_id,
        "company_name": opp.get("company_name"),
        "role": opp.get("role"),
        "to": opp.get("contact_email"),
        "subject": subject,
        "body": body,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.generated_emails.insert_one(dict(record))
    record.pop("_id", None)

    return GenerateEmailResponse(**record)
