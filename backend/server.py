"""Startup Lead Finder - FastAPI entrypoint.

Modular layout:
    server.py        -> app bootstrap, CORS, lifecycle, router wiring
    models/          -> Pydantic schemas
    routes/          -> feature-scoped APIRouters

Next phases (placeholders for future):
    routes/discovery.py  -> startup discovery
    routes/enrichment.py -> email extraction
    routes/scoring.py    -> AI company scoring
    routes/outreach.py   -> personalized email generation
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

from routes.companies import router as companies_router
from routes.opportunities import router as opportunities_router
from routes.outreach import router as outreach_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# --- Mongo --------------------------------------------------------------------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# --- App ----------------------------------------------------------------------
app = FastAPI(title="Startup Lead Finder", version="0.1.0")
app.state.db = db  # makes the db handle available to routers via request.app.state

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Startup Lead Finder API", "status": "ok"}


@api_router.get("/health")
async def health():
    return {"status": "healthy"}


# Feature routers ----------------------------------------------------------------
api_router.include_router(companies_router)
api_router.include_router(opportunities_router)
api_router.include_router(outreach_router)

app.include_router(api_router)

# --- CORS ---------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Logging ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def _startup() -> None:
    # Helpful indexes for the search & sort patterns we use.
    await db.companies.create_index("id", unique=True)
    await db.companies.create_index("company_name")
    await db.opportunities.create_index("id", unique=True)
    await db.opportunities.create_index("company_name")
    await db.opportunities.create_index("date_found")
    await db.opportunities.create_index("status")
    logger.info("Startup Lead Finder API ready")


@app.on_event("shutdown")
async def _shutdown() -> None:
    client.close()
