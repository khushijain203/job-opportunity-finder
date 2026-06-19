"""Concrete source adapters. Each is registered on import."""

from __future__ import annotations

from typing import Any, Dict

from .base import SourceAdapter, register_adapter


# ---------------------------------------------------------------------------- #
# Manual entry (existing UI form). Pass-through with light normalization.
# ---------------------------------------------------------------------------- #
@register_adapter
class ManualAdapter(SourceAdapter):
    SOURCE = "manual"
    LABEL = "Manual entry"
    DESCRIPTION = "Opportunities added by hand through the UI form."
    REQUIRED_FIELDS = ["company_name", "role"]

    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._base(payload)
        # Manual entries usually omit source_id - that's fine; dedupe falls back to company+role.
        self.validate(normalized)
        return normalized


# ---------------------------------------------------------------------------- #
# LinkedIn Jobs (expects standard LinkedIn job posting payload).
# ---------------------------------------------------------------------------- #
@register_adapter
class LinkedInAdapter(SourceAdapter):
    SOURCE = "linkedin"
    LABEL = "LinkedIn Jobs"
    DESCRIPTION = "Job listings ingested from LinkedIn (API or scraped postings)."
    REQUIRED_FIELDS = ["company_name", "role"]

    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._base(payload)
        # LinkedIn often uses 'jobTitle' / 'companyName' / 'workplaceType'.
        if not normalized["role"]:
            normalized["role"] = (payload.get("jobTitle") or "").strip()
        if not normalized["company_name"]:
            normalized["company_name"] = (payload.get("companyName") or "").strip()
        if not normalized["work_mode"] and payload.get("workplaceType"):
            from .base import _norm_work_mode

            normalized["work_mode"] = _norm_work_mode(payload.get("workplaceType"))
        self.validate(normalized)
        return normalized


# ---------------------------------------------------------------------------- #
# Naukri (India-focused).
# ---------------------------------------------------------------------------- #
@register_adapter
class NaukriAdapter(SourceAdapter):
    SOURCE = "naukri"
    LABEL = "Naukri"
    DESCRIPTION = "Indian job-board listings ingested from Naukri.com."
    REQUIRED_FIELDS = ["company_name", "role"]

    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._base(payload)
        if not normalized["role"]:
            normalized["role"] = (payload.get("designation") or "").strip()
        if not normalized["company_name"]:
            normalized["company_name"] = (payload.get("companyName") or "").strip()
        if not normalized["skills"]:
            from .base import _split_skills

            normalized["skills"] = _split_skills(payload.get("keySkills"))
        self.validate(normalized)
        return normalized


# ---------------------------------------------------------------------------- #
# Indeed.
# ---------------------------------------------------------------------------- #
@register_adapter
class IndeedAdapter(SourceAdapter):
    SOURCE = "indeed"
    LABEL = "Indeed"
    DESCRIPTION = "Job listings ingested from Indeed."
    REQUIRED_FIELDS = ["company_name", "role"]

    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._base(payload)
        if not normalized["role"]:
            normalized["role"] = (payload.get("jobtitle") or payload.get("position") or "").strip()
        if not normalized["company_name"]:
            normalized["company_name"] = (payload.get("company") or "").strip()
        self.validate(normalized)
        return normalized


# ---------------------------------------------------------------------------- #
# Company career pages (generic scraper output).
# ---------------------------------------------------------------------------- #
@register_adapter
class CareerPageAdapter(SourceAdapter):
    SOURCE = "career_page"
    LABEL = "Company career page"
    DESCRIPTION = "Roles scraped from a company's careers/jobs page."
    REQUIRED_FIELDS = ["company_name", "role"]

    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._base(payload)
        # Career-page scrapers usually know the company already.
        if not normalized["company_website"]:
            normalized["company_website"] = payload.get("careers_page") or payload.get("base_url")
        self.validate(normalized)
        return normalized


# ---------------------------------------------------------------------------- #
# Startup discovery (Crunchbase / ProductHunt / Wellfound).
# ---------------------------------------------------------------------------- #
@register_adapter
class StartupDiscoveryAdapter(SourceAdapter):
    SOURCE = "startup_discovery"
    LABEL = "Startup discovery"
    DESCRIPTION = "Roles discovered through startup directories (Crunchbase, Wellfound, ProductHunt)."
    REQUIRED_FIELDS = ["company_name", "role"]

    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._base(payload)
        if not normalized["company_website"]:
            normalized["company_website"] = payload.get("homepage_url") or payload.get("website")
        self.validate(normalized)
        return normalized
