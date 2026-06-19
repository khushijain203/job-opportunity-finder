# Startup Lead Finder — PRD

## Original Problem Statement
Build a full-stack web application called Startup Lead Finder.

* Tech: FastAPI backend, React frontend, SQLite database (note: substituted with MongoDB based on environment & user approval).
* Companies table: id, company_name, website, email, created_at.
* Backend APIs: GET /companies, POST /companies, DELETE /companies/{id}.
* Frontend: table of companies, add form, delete button, search by name.
* Responsive UI.
* Setup instructions and project folder structure.

## User Choices (locked-in)
* Database: **MongoDB** (recommended over SQLite)
* Design: **Clean & minimal SaaS-style** (Swiss / High-contrast)
* Extra feature: **CSV export** of companies
* Auth: **Open access** (no auth)
* Architecture: **modular**, ready for next phases

## Architecture
```
backend/
  models/company.py      -> Pydantic schemas
  routes/companies.py    -> CRUD + stats + CSV export
  server.py              -> FastAPI bootstrap + router wiring
frontend/src/
  components/lead/       -> Header, StatsBar, AddCompanyDialog, CompaniesTable, LeadFinder
  lib/api.js             -> axios client
```

## User Persona
* Solo founder / SDR / VC analyst tracking startup leads in early outreach.

## Core Requirements (static)
* List, add, delete companies.
* Search by company name (case-insensitive).
* Export all leads to CSV.
* Responsive UI.

## Implemented (2026-02)
* Backend MongoDB-based CRUD with UUID ids, ISO timestamps, indexed search.
* `/api/companies/stats` and `/api/companies/export.csv`.
* React UI: header, stats bar, search (debounced), add dialog, delete confirm, sortable visible table.
* Manrope + IBM Plex Sans typography, sharp-edge minimal SaaS aesthetic.
* Toaster (sonner) for feedback.
* README.md + folder structure documented.

## Backlog
### P0 (next iteration)
* End-to-end automated tests (already covered by testing_agent_v3).
### P1
* Startup discovery integration (Crunchbase / web scrape).
* Email extraction & enrichment.
* AI company scoring (LLM via Emergent universal key).
### P2
* Personalized cold-email generator.
* Tags / pipeline stages.
* Multi-user auth.

## Next Action Items
1. Run testing_agent_v3 end-to-end.
2. Address any test failures.
3. Surface CSV export & search behavior in UX polish if needed.
