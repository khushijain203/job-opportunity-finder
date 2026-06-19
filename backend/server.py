"""Startup Lead Finder - FastAPI entrypoint."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import APIRouter, FastAPI  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from core.security import hash_password  # noqa: E402
from models.user import User  # noqa: E402
from routes.auth import router as auth_router  # noqa: E402
from routes.companies import router as companies_router  # noqa: E402
from routes.generated_emails import router as generated_emails_router  # noqa: E402
from routes.matches import router as matches_router  # noqa: E402
from routes.opportunities import router as opportunities_router  # noqa: E402
from routes.outreach import router as outreach_router  # noqa: E402
from routes.profile import router as profile_router  # noqa: E402
from routes.resumes import router as resumes_router  # noqa: E402
from core.storage import init_storage  # noqa: E402

# --- Mongo --------------------------------------------------------------------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# --- App ----------------------------------------------------------------------
app = FastAPI(title="Startup Lead Finder", version="0.2.0")
app.state.db = db

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Startup Lead Finder API", "status": "ok"}


@api_router.get("/health")
async def health():
    return {"status": "healthy"}


# Feature routers ----------------------------------------------------------------
api_router.include_router(auth_router)
api_router.include_router(profile_router)
api_router.include_router(companies_router)
api_router.include_router(opportunities_router)
api_router.include_router(outreach_router)
api_router.include_router(generated_emails_router)
api_router.include_router(resumes_router)
api_router.include_router(matches_router)

app.include_router(api_router)

# --- CORS ---------------------------------------------------------------------
# `allow_credentials=True` rules out wildcard origins, so build an explicit list.
_raw_origins = os.environ.get("CORS_ORIGINS", "")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allowed_origins or ["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Logging ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _seed_demo_user() -> None:
    """Idempotently create a known test user for the testing agent."""
    email = (os.environ.get("DEMO_EMAIL") or "demo@leadfinder.test").lower()
    password = os.environ.get("DEMO_PASSWORD") or "Demo1234!"
    existing = await db.users.find_one({"email": email})
    if existing:
        return
    demo = User(
        full_name="Demo User",
        email=email,
        password_hash=hash_password(password),
        is_demo=True,
    )
    await db.users.insert_one(demo.model_dump())
    logger.info("Seeded demo user %s", email)


@app.on_event("startup")
async def _startup() -> None:
    # Helpful indexes.
    await db.users.create_index("email", unique=True)
    await db.companies.create_index("id", unique=True)
    await db.companies.create_index("user_id")
    await db.opportunities.create_index("id", unique=True)
    await db.opportunities.create_index("user_id")
    await db.opportunities.create_index("date_found")
    await db.profiles.create_index("user_id", unique=True)
    await db.generated_emails.create_index("user_id")
    await db.generated_emails.create_index("opportunity_id")
    await db.resumes.create_index("user_id")
    await db.resumes.create_index([("user_id", 1), ("is_active", 1)])
    await db.resume_texts.create_index("resume_id", unique=True)
    await db.match_results.create_index(
        [("user_id", 1), ("resume_id", 1), ("opportunity_id", 1)], unique=True
    )

    # Object storage init (non-fatal if it fails — uploads will surface the error).
    try:
        init_storage()
    except Exception as exc:  # pragma: no cover
        logger.warning("Object storage init failed: %s", exc)

    await _seed_demo_user()
    logger.info("Startup Lead Finder API ready")


@app.on_event("shutdown")
async def _shutdown() -> None:
    client.close()
