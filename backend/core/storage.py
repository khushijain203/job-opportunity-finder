"""Emergent object storage wrapper.

Initialize once on startup, reuse the storage_key across requests.
All resume bytes flow through this module - we never expose direct storage URLs.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "leadfinder"

_storage_key: Optional[str] = None


def init_storage(force: bool = False) -> Optional[str]:
    """Lazy / idempotent init. Returns the session-scoped storage key (or None on failure)."""
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    emergent_key = os.environ.get("EMERGENT_LLM_KEY")
    if not emergent_key:
        logger.warning("EMERGENT_LLM_KEY missing - object storage disabled")
        return None
    try:
        resp = requests.post(
            f"{STORAGE_URL}/init", json={"emergent_key": emergent_key}, timeout=30
        )
        resp.raise_for_status()
        _storage_key = resp.json()["storage_key"]
        logger.info("Object storage initialized")
        return _storage_key
    except Exception as exc:  # pragma: no cover - network-dependent
        logger.error("Object storage init failed: %s", exc)
        _storage_key = None
        return None


def _key_or_raise() -> str:
    k = init_storage()
    if not k:
        raise RuntimeError("Object storage is not available")
    return k


def make_path(user_id: str, file_uuid: str, ext: str) -> str:
    ext = ext.lower().lstrip(".") or "bin"
    return f"{APP_NAME}/resumes/{user_id}/{file_uuid}.{ext}"


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload bytes to object storage. Returns the storage response dict."""
    key = _key_or_raise()
    # Retry once with a fresh key if the cached one expired.
    for attempt in range(2):
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data,
            timeout=120,
        )
        if resp.status_code == 403 and attempt == 0:
            key = init_storage(force=True) or key
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> Tuple[bytes, str]:
    """Download bytes by storage path. Returns (content, content_type)."""
    key = _key_or_raise()
    for attempt in range(2):
        resp = requests.get(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key},
            timeout=60,
        )
        if resp.status_code == 403 and attempt == 0:
            key = init_storage(force=True) or key
            continue
        resp.raise_for_status()
        return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
    resp.raise_for_status()
    return b"", "application/octet-stream"
