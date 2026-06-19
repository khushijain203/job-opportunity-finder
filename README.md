# Startup Lead Finder

A clean, minimal SaaS-style web app for capturing and managing startup leads.
Built as the MVP foundation for a larger lead-intelligence pipeline (discovery,
email extraction, AI scoring, personalized outreach).

## Tech Stack

| Layer    | Tech                                                |
| -------- | --------------------------------------------------- |
| Frontend | React 19, Tailwind CSS, shadcn/ui, framer-motion, sonner, phosphor-icons |
| Backend  | FastAPI, Motor (async MongoDB driver)               |
| Database | MongoDB                                             |

> **Note on the DB.** The problem statement suggested SQLite, but this template
> ships with MongoDB pre-wired in the Kubernetes environment, so we use MongoDB
> with an equivalent schema. The data model is identical conceptually.

## Folder Structure

```
/app
├── backend/
│   ├── models/
│   │   ├── __init__.py
│   │   └── company.py          # Pydantic schemas for Company
│   ├── routes/
│   │   ├── __init__.py
│   │   └── companies.py        # /api/companies CRUD + CSV export + stats
│   ├── server.py               # FastAPI bootstrap + router wiring
│   ├── requirements.txt
│   └── .env                    # MONGO_URL, DB_NAME, CORS_ORIGINS
│
├── frontend/
│   ├── src/
│   │   ├── App.js              # Router + Toaster
│   │   ├── components/
│   │   │   ├── ui/             # shadcn primitives
│   │   │   └── lead/           # Feature components
│   │   │       ├── Header.jsx
│   │   │       ├── StatsBar.jsx
│   │   │       ├── AddCompanyDialog.jsx
│   │   │       ├── CompaniesTable.jsx
│   │   │       └── LeadFinder.jsx
│   │   ├── lib/
│   │   │   └── api.js          # Thin axios client
│   │   ├── index.css
│   │   └── App.css
│   ├── package.json
│   └── .env                    # REACT_APP_BACKEND_URL
│
└── README.md
```

## Data Model

A `Company` is stored in the `companies` MongoDB collection:

| Field        | Type   | Notes                                  |
| ------------ | ------ | -------------------------------------- |
| id           | string | UUID v4, primary identifier            |
| company_name | string | required                               |
| website      | string | optional                               |
| email        | string | optional, validated as email           |
| created_at   | string | ISO-8601 UTC timestamp                 |

## API Reference

Base URL: `${REACT_APP_BACKEND_URL}/api`

| Method | Endpoint                       | Description                          |
| ------ | ------------------------------ | ------------------------------------ |
| GET    | `/companies?search=<query>`    | List companies, optional name filter |
| POST   | `/companies`                   | Create a company                     |
| DELETE | `/companies/{id}`              | Delete a company                     |
| GET    | `/companies/stats`             | Counts: total, with_email, with_website |
| GET    | `/companies/export.csv`        | Download all companies as CSV        |
| GET    | `/health`                      | Health probe                         |

### Example - create a company

```bash
curl -X POST "$REACT_APP_BACKEND_URL/api/companies" \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Acme Robotics","website":"https://acme.com","email":"founder@acme.com"}'
```

## Frontend Features

* Companies table with hover states & staggered row reveals
* Add Lead dialog with inline validation
* Per-row delete with confirmation modal
* Live search by company name (debounced 250 ms)
* CSV export button
* Header stats bar (total / with email / with website)
* Fully responsive layout (mobile ↔ desktop)

## Local / Container Setup

The Emergent container starts everything via supervisor — no manual commands
are required. Hot reload is enabled for both frontend and backend.

To restart manually if needed:

```bash
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
```

Environment variables already configured:

* `backend/.env` -> `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`
* `frontend/.env` -> `REACT_APP_BACKEND_URL`

## Roadmap (Phase 2+)

The codebase is intentionally modular for upcoming features:

* `routes/discovery.py` — auto-discover startups (Crunchbase / ProductHunt / web)
* `routes/enrichment.py` — email & contact extraction
* `routes/scoring.py` — LLM-powered company scoring
* `routes/outreach.py` — personalized cold email generation
