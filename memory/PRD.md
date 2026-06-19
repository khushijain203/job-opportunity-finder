# Startup Lead Finder — PRD

## Original Problem Statement
Build a full-stack web application called Startup Lead Finder; iteratively upgrade to an **Opportunity Discovery Platform** with **multi-user auth + per-user data isolation**.

## User Choices (locked-in)
* DB: MongoDB
* UI: Clean & minimal SaaS-style (kept across phases; not redesigned in 3A)
* Leads CSV export
* LLM: Claude Sonnet 4.5 via emergentintegrations + EMERGENT_LLM_KEY
* Auth: JWT in HTTP-only cookie (samesite=lax, secure=true), bcrypt + policy (≥8 chars, 1 upper + 1 lower + 1 digit)
* Migration: orphan records assigned to FIRST registered (non-demo) user
* Generated emails: persisted automatically + per-opportunity History view
* Demo user seeded for testing: `demo@leadfinder.app / Demo1234!`

## Architecture
```
backend/
  core/security.py             -> bcrypt, JWT, cookies, get_current_user dep
  models/user.py               -> User, UserRegister, UserLogin, UserPublic, Profile, ProfileUpdate
  models/company.py            -> Company schemas
  models/opportunity.py        -> Opportunity schemas + enum tuples
  routes/auth.py               -> register/login/logout/refresh/me + orphan migration
  routes/profile.py            -> GET/PUT /api/profile
  routes/companies.py          -> Leads CRUD scoped by user_id + stats + CSV export
  routes/opportunities.py      -> Opportunities CRUD/filters/sort/save-to-leads/per-user seed
  routes/outreach.py           -> Claude Sonnet 4.5 email gen, persists to generated_emails
  routes/generated_emails.py   -> list/delete generated emails for current user
  server.py                    -> FastAPI app, CORS w/ credentials, demo user seed, indexes
frontend/src/
  contexts/AuthContext.jsx
  components/auth/AuthPage.jsx           -> login + register tabbed form
  components/auth/AuthGate.jsx           -> wraps the app
  components/lead/Header.jsx             -> user name + Log out + Profile button
  components/lead/ProfileDialog.jsx      -> skills / years / roles / locations / bio
  components/lead/EmailHistoryDialog.jsx -> per-opportunity outreach history
  components/lead/LeadsView.jsx
  components/lead/OpportunitiesView.jsx
  components/lead/OpportunitiesTable.jsx -> per-row Email + History + Save + Delete
  components/lead/AddOpportunityDialog.jsx
  components/lead/AddCompanyDialog.jsx
  components/lead/GenerateEmailDialog.jsx
  components/lead/LeadFinder.jsx         -> Leads / Find Opportunities tabs
  lib/api.js                             -> axios w/ withCredentials, all API namespaces
```

## User Personas
* Job seekers tracking opportunities + generating personalized outreach
* SDRs / founders managing private startup-lead pipelines, isolated per user

## Implemented Phases

### Phase 1 (2026-02): Leads MVP
Companies CRUD, search, CSV export, stats summary, Swiss/SaaS UI.

### Phase 2 (2026-02): Opportunity Discovery
Opportunity model + filters/sort, save-to-leads, AI outreach generation (Claude Sonnet 4.5), tabbed UI.

### Phase 3A (2026-02): Auth + User Isolation ✅
* JWT in HTTP-only cookies (12h access + 14d refresh)
* bcrypt + policy
* `/api/auth/register|login|logout|refresh|me`
* User model: full_name, email, password_hash, created_at, is_demo
* Profile model (full_name, skills[], years_experience, preferred_roles[], preferred_locations[], bio) for upcoming resume-matching
* Every Lead, Opportunity, GeneratedEmail scoped to its `user_id`
* Cross-user PATCH/DELETE returns 404
* Orphan migration: first registered (non-demo) user claims all pre-existing records (one-shot via `system_state.orphan_migration_v1`)
* Demo user seeded on startup
* Generated emails auto-persisted; per-opportunity history dialog with copy + delete
* Tests: 25/25 backend pytest pass (auth, isolation, migration, LLM, profile)

## Backlog
### P1 (next phases per user)
* Resume upload + parsing
* AI match scoring (resume × opportunity)
* Founder/recruiter email discovery
* Gmail / Outlook integrations & automated sending

### P2
* Application tracking dashboard
* Tags / pipeline stages on leads
* Forgot-password flow
* Email verification on signup
* Multi-tenant admin dashboard

## Next Action Items
1. Phase 3B: Resume upload + parsing (PDF → structured profile data).
2. Build a "Match Score" column on opportunities (resume × opportunity skills).
3. Add Gmail OAuth for sending generated outreach emails directly.
