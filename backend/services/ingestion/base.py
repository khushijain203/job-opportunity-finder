"""Base adapter contract + registry for opportunity ingestion sources.

A `SourceAdapter` takes a raw payload (whatever the upstream provider sends us)
and returns a normalized dict that matches the Opportunity model.  Each source
gets its own subclass; new sources are added by subclassing + decorator.

Future adapters (LinkedIn API, Naukri API, web-scraper outputs, etc.) only need
to implement `.normalize()` — the ingestion route handles dedupe, persistence,
and downstream match-score recomputation.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------- #
# Registry
# ---------------------------------------------------------------------------- #
ADAPTER_REGISTRY: Dict[str, Type["SourceAdapter"]] = {}


def register_adapter(cls: Type["SourceAdapter"]) -> Type["SourceAdapter"]:
    """Decorator: register an adapter under its `SOURCE` key."""
    key = cls.SOURCE.lower().strip()
    if not key:
        raise ValueError(f"{cls.__name__} must declare a SOURCE class attribute.")
    ADAPTER_REGISTRY[key] = cls
    return cls


def get_adapter(source: str) -> "SourceAdapter":
    key = (source or "").lower().strip()
    if key not in ADAPTER_REGISTRY:
        raise ValueError(
            f"Unknown source '{source}'. Available: {list(ADAPTER_REGISTRY.keys())}"
        )
    return ADAPTER_REGISTRY[key]()


def list_adapters() -> List[Dict[str, Any]]:
    return [
        {
            "source": cls.SOURCE,
            "label": cls.LABEL,
            "description": cls.DESCRIPTION,
            "required_fields": cls.REQUIRED_FIELDS,
        }
        for cls in ADAPTER_REGISTRY.values()
    ]


# ---------------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------------- #
_SKILL_SPLIT = re.compile(r"[,;|/]+")


def _split_skills(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(s).strip() for s in value if str(s).strip()]
    return [s.strip() for s in _SKILL_SPLIT.split(str(value)) if s.strip()]


def _norm_employment_type(value: Any) -> str:
    s = (str(value or "")).strip().lower()
    if s in {"internship", "intern", "trainee"}:
        return "Internship"
    if s in {"full time", "full-time", "fulltime", "permanent", "fte"}:
        return "Full Time"
    if "intern" in s:
        return "Internship"
    return "Full Time"  # sensible default


def _norm_work_mode(value: Any) -> Optional[str]:
    s = (str(value or "")).strip().lower()
    if not s:
        return None
    if "remote" in s or "wfh" in s:
        return "Remote"
    if "hybrid" in s:
        return "Hybrid"
    if "onsite" in s or "in-office" in s or "in office" in s or "office" in s:
        return "Onsite"
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------- #
# Base class
# ---------------------------------------------------------------------------- #
class SourceAdapter(ABC):
    """Each ingestion source subclasses this."""

    SOURCE: str = ""          # canonical key, e.g. "linkedin"
    LABEL: str = ""           # human-readable label
    DESCRIPTION: str = ""
    REQUIRED_FIELDS: List[str] = ["company_name", "role"]

    @abstractmethod
    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a raw source payload into the Opportunity schema."""

    # ------------------------------------------------------------------ #
    # Default helpers (shared by all adapters)
    # ------------------------------------------------------------------ #
    def _base(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "company_name": (payload.get("company_name") or payload.get("company") or "").strip(),
            "role": (payload.get("role") or payload.get("title") or payload.get("job_title") or "").strip(),
            "location": (payload.get("location") or payload.get("city") or None),
            "employment_type": _norm_employment_type(
                payload.get("employment_type") or payload.get("type") or payload.get("job_type")
            ),
            "work_mode": _norm_work_mode(
                payload.get("work_mode") or payload.get("workplace") or payload.get("remote")
            ),
            "skills": _split_skills(
                payload.get("skills") or payload.get("tags") or payload.get("requirements")
            ),
            "source": self.SOURCE,
            "source_id": (payload.get("source_id") or payload.get("id") or payload.get("external_id")),
            "source_url": (payload.get("source_url") or payload.get("url") or payload.get("link")),
            "apply_link": (payload.get("apply_link") or payload.get("apply_url") or payload.get("url")),
            "company_website": (payload.get("company_website") or payload.get("website")),
            "contact_email": (payload.get("contact_email") or payload.get("email")),
            "description": (payload.get("description") or payload.get("summary")),
            "date_posted": (payload.get("date_posted") or payload.get("posted_at") or payload.get("posted_on")),
            "ingested_at": _now_iso(),
            "raw_payload": payload,
        }

    def validate(self, normalized: Dict[str, Any]) -> None:
        missing = [
            f for f in self.REQUIRED_FIELDS
            if not normalized.get(f) or not str(normalized.get(f)).strip()
        ]
        if missing:
            raise ValueError(f"Missing required fields for {self.SOURCE}: {missing}")
