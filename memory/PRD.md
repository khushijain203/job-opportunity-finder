# Startup Lead Finder — PRD

## Original Problem Statement
Build a full-stack web application called Startup Lead Finder, with a follow-up upgrade to an **Opportunity Discovery Platform**.

## User Choices (locked-in)
* Database: MongoDB (recommended over SQLite)
* Design: Clean & minimal SaaS-style (Swiss / high-contrast)
* Extra: CSV export of companies
* Auth: Open access (no auth)
* LLM for outreach emails: **Claude Sonnet 4.5** via emergentintegrations + EMERGENT_LLM_KEY
* Seed 5 sample opportunities for the Opportunities view

## Architecture
```
backend/
  models/company.py            -> Company schemas
  models/opportunity.py        -> Opportunity schemas + enum tuples
  routes/companies.py          -> Leads CRUD + stats + CSV export
  routes/opportunities.py      -> Opportunities CRUD, filters, sort, save-to-leads, seed
  routes/outreach.py           -> LLM-generated email endpoint (Claude Sonnet 4.5)
  server.py                    -> FastAPI bootstrap + router wiring (companies, opportunities, outreach)
frontend/src/
  components/lead/
    Header.jsx
    StatsBar.jsx
    AddCompanyDialog.jsx
    CompaniesTable.jsx
    LeadsView.jsx              -> Leads tab content
    OpportunityFilters.jsx
    OpportunitiesTable.jsx
    AddOpportunityDialog.jsx
    GenerateEmailDialog.jsx    -> form -> loading -> result with Edit/Copy/Mailto
    OpportunitiesView.jsx
    LeadFinder.jsx             -> top-level tabs (Leads / Find Opportunities)
  lib/api.js                   -> axios client (companies, opportunities, outreach)
```

## User Personas
* Job seekers / interns tracking opportunities across job boards & company websites
* SDRs / founders managing outbound startup leads & outreach pipeline

## Core Requirements (static)
* Leads: list, add, delete, search, CSV export, stats summary
* Opportunities: list/filter/sort by skills, role, location, employment type, work mode, status
* Convert opportunity → Lead via "Save to Leads"
* AI-generated personalized outreach email (Edit/Copy/Mailto)
* Responsive UI

## Implemented (2026-02)
**Phase 1 — Leads MVP**
* MongoDB Companies CRUD, UUID ids, ISO timestamps
* `/api/companies/stats`, `/api/companies/export.csv`
* React UI: stats bar, search, add dialog, delete confirm, table
* Manrope + IBM Plex Sans typography, Swiss/SaaS aesthetic
* Mobile-responsive header

**Phase 2 — Opportunity Discovery**
* Opportunity model: company_name, role, location, employment_type, work_mode, skills[], source, apply_link, company_website, contact_email, description, date_found, status
* GET `/api/opportunities` with filters (search, role, location, skills[], employment_type, work_mode, status) + sort options
* POST `/api/opportunities`, DELETE `/api/opportunities/{id}`, PATCH `/api/opportunities/{id}/status`
* POST `/api/opportunities/seed` (idempotent demo data: 5 sample roles)
* POST `/api/opportunities/{id}/save-to-leads` (case-insensitive name dedupe)
* POST `/api/outreach/generate` (Claude Sonnet 4.5 via emergentintegrations) → JSON `{subject, body, to}`
* Tabbed UI: Leads / Find Opportunities
* Filter bar (search, skills, role, location, type, work mode, status, sort)
* Opportunities table with per-row status dropdown, Save-to-Leads, Generate Email, Delete
* Generate Email dialog: form → loading → result with Edit / Copy / Open-in-Mail (mailto)

## Backlog
### P1 (next phases per user)
* Startup discovery from company websites
* Internship and job aggregation (board ingestion)
* Resume upload & parsing
* AI match scoring (resume × opportunity)
* Founder/recruiter email discovery
* Gmail / Outlook integrations & automated sending

### P2
* Application tracking dashboard
* Tags / pipeline stages on leads
* Multi-user auth

## Next Action Items
1. Begin Phase 3: resume upload + parsing + AI match scoring.
2. Add Gmail OAuth for sending generated outreach emails directly.
3. Build a startup discovery ingestion job (Crunchbase / job boards).
