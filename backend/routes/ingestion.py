"""Opportunity ingestion endpoints.

Endpoints (under /api/ingest):
    GET  /sources                  - list registered adapters
    POST /opportunity              - single ingestion (body: { source, payload })
    POST /opportunities            - bulk ingestion  (body: { source, items: [...] })

All endpoints are user-scoped (Depends get_current_user) and:
  - run the source-specific adapter,
  - check for duplicates (returns the existing record instead of inserting),
  - auto-compute match scores against the user's active resume,
  - leave the existing /api/opportunities CRUD unaffected.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.security import get_current_user
from models.opportunity import EMPLOYMENT_TYPES, Opportunity, WORK_MODES
from services.ingestion import (
    find_duplicate,
    get_adapter,
    list_adapters,
)
from services.match_compute import compute_matches_for_opportunities

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# Above this batch size we move match-score computation to background tasks
# to keep the HTTP response snappy.
SYNC_MATCH_BATCH_LIMIT = 25


# ---------------------------------------------------------------------------- #
# Request / response shapes
# ---------------------------------------------------------------------------- #
class SingleIngestRequest(BaseModel):
    source: str = Field(..., description="Adapter key, e.g. 'linkedin' / 'naukri' / 'manual'")
    payload: Dict[str, Any] = Field(default_factory=dict)


class BulkIngestRequest(BaseModel):
    source: str
    items: List[Dict[str, Any]] = Field(default_factory=list)


class IngestItemResult(BaseModel):
    status: str  # 'created' | 'duplicate' | 'error'
    opportunity_id: Optional[str] = None
    duplicate_of: Optional[str] = None
    error: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class BulkIngestResponse(BaseModel):
    total: int
    created: int
    duplicates: int
    errors: int
    results: List[IngestItemResult]
    matches_computed: int = 0
    matches_scheduled: bool = False


# ---------------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------------- #
def _strip_enums(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """Belt-and-suspenders: ensure employment_type / work_mode are in our allowed set."""
    if normalized.get("employment_type") not in EMPLOYMENT_TYPES:
        normalized["employment_type"] = "Full Time"
    if normalized.get("work_mode") not in WORK_MODES:
        normalized["work_mode"] = None
    return normalized


async def _ingest_one(db, user_id: str, normalized: Dict[str, Any]) -> IngestItemResult:
    dup = await find_duplicate(db, user_id, normalized)
    if dup:
        return IngestItemResult(
            status="duplicate",
            opportunity_id=None,
            duplicate_of=dup.get("id"),
            source=normalized.get("source"),
            source_id=normalized.get("source_id"),
        )
    opp = Opportunity(**normalized)
    doc = opp.model_dump()
    doc["user_id"] = user_id
    await db.opportunities.insert_one(doc)
    return IngestItemResult(
        status="created",
        opportunity_id=opp.id,
        source=normalized.get("source"),
        source_id=normalized.get("source_id"),
    )


# ---------------------------------------------------------------------------- #
# Endpoints
# ---------------------------------------------------------------------------- #
@router.get("/sources")
async def get_sources():
    return {"adapters": list_adapters()}


@router.post("/opportunity", response_model=IngestItemResult)
async def ingest_one(
    body: SingleIngestRequest,
    request: Request,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    db = request.app.state.db
    try:
        adapter = get_adapter(body.source)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        normalized = _strip_enums(adapter.normalize(body.payload))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = await _ingest_one(db, user["id"], normalized)
    if result.status == "created" and result.opportunity_id:
        # Auto-score in the background so the API response stays fast.
        background.add_task(
            compute_matches_for_opportunities, db, user, [result.opportunity_id]
        )
    return result


@router.post("/opportunities", response_model=BulkIngestResponse)
async def ingest_bulk(
    body: BulkIngestRequest,
    request: Request,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    db = request.app.state.db
    try:
        adapter = get_adapter(body.source)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    results: List[IngestItemResult] = []
    in_batch_keys: set = set()
    created_ids: List[str] = []

    for raw in body.items:
        try:
            normalized = _strip_enums(adapter.normalize(raw))
        except ValueError as exc:
            results.append(
                IngestItemResult(status="error", error=str(exc), source=body.source)
            )
            continue

        # In-batch duplicate guard (caller sends the same row twice).
        from services.ingestion.dedupe import dedupe_key

        key = dedupe_key(normalized)
        if key in in_batch_keys:
            results.append(
                IngestItemResult(
                    status="duplicate",
                    source=body.source,
                    source_id=normalized.get("source_id"),
                    duplicate_of=None,
                )
            )
            continue
        in_batch_keys.add(key)

        try:
            res = await _ingest_one(db, user["id"], normalized)
            results.append(res)
            if res.status == "created" and res.opportunity_id:
                created_ids.append(res.opportunity_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Bulk ingest item failed")
            results.append(
                IngestItemResult(status="error", error=str(exc), source=body.source)
            )

    created = sum(1 for r in results if r.status == "created")
    duplicates = sum(1 for r in results if r.status == "duplicate")
    errors = sum(1 for r in results if r.status == "error")

    # Match-score computation: sync for small batches, background for large.
    matches_computed = 0
    matches_scheduled = False
    if created_ids:
        if len(created_ids) <= SYNC_MATCH_BATCH_LIMIT:
            matches_computed = await compute_matches_for_opportunities(db, user, created_ids)
        else:
            background.add_task(
                compute_matches_for_opportunities, db, user, created_ids
            )
            matches_scheduled = True

    return BulkIngestResponse(
        total=len(body.items),
        created=created,
        duplicates=duplicates,
        errors=errors,
        results=results,
        matches_computed=matches_computed,
        matches_scheduled=matches_scheduled,
    )
