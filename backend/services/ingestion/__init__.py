"""Ingestion source adapters."""

from .base import SourceAdapter, ADAPTER_REGISTRY, register_adapter, get_adapter, list_adapters
from . import adapters  # noqa: F401  - registers built-in adapters as a side effect
from .dedupe import find_duplicate, dedupe_key  # noqa: F401

__all__ = [
    "SourceAdapter",
    "ADAPTER_REGISTRY",
    "register_adapter",
    "get_adapter",
    "list_adapters",
    "find_duplicate",
    "dedupe_key",
]
