# Startup Lead Finder — PRD

## Original Problem Statement
Build a Startup Lead Finder; iteratively upgrade to an **Opportunity Discovery Platform** with multi-user auth, resume parsing, and AI-assisted match scoring + outreach.

## User Choices (locked-in across phases)
* DB: MongoDB
* UI: Clean & minimal SaaS-style — kept unchanged across phases
* Leads CSV export
* LLM: Claude Sonnet 4.5 via emergentintegrations + EMERGENT_LLM_KEY
* Auth: JWT in HTTP-only cookie (samesite=lax, secure=true), bcrypt + policy
* Resume parsing: **local PDF/DOCX extraction** by default; AI enrichment opt-in & cached
* Match scoring: **Weighted Jaccard** default + **TF-IDF** advanced view; **AI nuance** opt-in & cached per (resume, opportunity)
* Migration: orphan records assigned to FIRST registered (non-demo) user

## Architecture
```
backend/
  core/security.py         -> bcrypt, JWT, get_current_user
  core/storage.py          -> Emergent object-storage wrapper (resumes)
  services/resume_parser.py-> pypdf + python-docx + regex section parser
  services/match_score.py  -> Jaccard + TF-IDF + breakdown w/ explanations
  models/                  -> user, company, opportunity (incl. freshness), resume, match
  routes/                  -> auth, profile, companies, opportunities (w/ freshness), outreach, generated_emails, resumes, matches
  server.py                -> FastAPI bootstrap, indexes, demo seed, object-storage init

frontend/src/
  contexts/AuthContext.jsx
  components/auth/         -> AuthPage + AuthGate
  components/lead/
    Header.jsx                -> user name + Profile + Logout
    ProfileDialog.jsx          -> profile + embedded ResumeSection
    ResumeSection.jsx          -> drag/drop, list, activate, delete, AI enhance
    MatchBadge.jsx             -> score badge + breakdown popover + TF-IDF + AI insight
    OpportunityFilters.jsx     -> + new "Freshness" filter (24h/3d/7d/30d)
    OpportunitiesTable.jsx     -> + new Match column
    OpportunitiesView.jsx      -> calls matchesApi.batch, listens 'resume-changed' window event
    LeadFinder.jsx             -> Leads / Find Opportunities tabs
  lib/api.js                 -> all API namespaces incl. resumesApi + matchesApi
```

## Implemented Phases
- **Phase 1 (2026-02)**: Leads CRUD + CSV export + Swiss/SaaS UI
- **Phase 2 (2026-02)**: Opportunity Discovery + filters + AI outreach (Claude Sonnet 4.5)
- **Phase 3A (2026-02)**: JWT cookie auth + bcrypt policy + per-user isolation + Profile model + generated_emails history + orphan migration ✅
- **Phase 3B (2026-02)**: Resume Upload + Local Parsing + Match Score + Freshness Filters ✅
  - 47/47 backend tests pass; 100% frontend e2e pass
  - Object storage via Emergent for resume bytes
  - Raw text stored in `resume_texts` collection (SEPARATE from parsed fields)
  - Weighted Jaccard (default) + TF-IDF (advanced, opt-in) match scoring
  - Match breakdown: matched/missing skills + role/experience/location relevance with explanations
  - AI enrichment per resume — one Claude call, cached forever in `parsed.ai_*`
  - AI match nuance per (resume, opp) — one Claude call, cached forever in `match_results.ai_*`
  - Future-ready opp fields: `date_posted`, `last_verified`, `freshness_score`
  - Freshness filters (Last 24h / 3d / 7d / 30d) ready to be activated by future ingestion

## Backlog
### P1 (next phases per user roadmap)
* Startup discovery / opportunity ingestion (career pages, job boards) populating `date_posted` + `freshness_score`
* Gmail / Outlook integrations → send generated outreach directly
* Resume re-parsing job (re-run section parser on existing raw_text without re-upload)

### P2 (polish + perf)
* Application tracking dashboard
* Invalidate cached matches when profile.preferred_roles/locations change
* Migrate `@app.on_event` to FastAPI lifespan
* Tighter LLM JSON extraction (strip ```json fences)
* Per-user "Outreach Stats" widget

## Next Action Items
1. **Phase 4**: Job-discovery ingestion (career-page crawler + LinkedIn/Indeed scrape) to populate date_posted + freshness_score.
2. Implement Gmail OAuth for sending outreach emails directly.
3. Auto-refresh access token via axios refresh interceptor (currently re-login after 12h).
