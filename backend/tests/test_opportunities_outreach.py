"""Backend API tests for Opportunities + Outreach modules.

Covers:
    - GET    /api/opportunities/meta
    - POST   /api/opportunities/seed (idempotent)
    - GET    /api/opportunities (default sort, filters, sort options, invalid enum)
    - POST   /api/opportunities (create with validation)
    - PATCH  /api/opportunities/{id}/status (valid / invalid / 404)
    - POST   /api/opportunities/{id}/save-to-leads (creates + idempotent)
    - DELETE /api/opportunities/{id} (204 + 404 + persistence)
    - POST   /api/outreach/generate (live LLM call + 404)
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    yield s
    # cleanup TEST_ prefixed opportunities + companies
    try:
        for opp in s.get(f"{API}/opportunities").json():
            if opp.get("company_name", "").startswith("TEST_"):
                s.delete(f"{API}/opportunities/{opp['id']}")
        for c in s.get(f"{API}/companies").json():
            if c.get("company_name", "").startswith("TEST_"):
                s.delete(f"{API}/companies/{c['id']}")
    except Exception:
        pass


# --- Meta ---------------------------------------------------------------------
def test_meta_returns_expected_enums(session):
    r = session.get(f"{API}/opportunities/meta")
    assert r.status_code == 200
    data = r.json()
    assert data["employment_types"] == ["Internship", "Full Time"]
    assert data["work_modes"] == ["Remote", "Hybrid", "Onsite"]
    assert data["statuses"] == ["New", "Applied", "Rejected", "Interview"]
    assert "newest" in data["sort_options"]
    assert "company_az" in data["sort_options"]


# --- Seed ---------------------------------------------------------------------
def test_seed_idempotent(session):
    # 1st call: either inserts 5 or already populated -> 0
    r = session.post(f"{API}/opportunities/seed")
    assert r.status_code == 200
    first = r.json()
    assert "inserted" in first

    # 2nd call must return 0 inserted (collection now populated)
    r2 = session.post(f"{API}/opportunities/seed")
    assert r2.status_code == 200
    assert r2.json()["inserted"] == 0


def test_seed_collection_has_at_least_5(session):
    r = session.get(f"{API}/opportunities")
    assert r.status_code == 200
    assert len(r.json()) >= 5


# --- List + sort --------------------------------------------------------------
def test_list_default_sort_desc_by_date_found(session):
    r = session.get(f"{API}/opportunities")
    assert r.status_code == 200
    dates = [o["date_found"] for o in r.json()]
    assert dates == sorted(dates, reverse=True)


def test_sort_company_az(session):
    r = session.get(f"{API}/opportunities", params={"sort": "company_az"})
    assert r.status_code == 200
    names = [o["company_name"] for o in r.json()]
    assert names == sorted(names, key=str.lower) or names == sorted(names)


def test_invalid_sort_422(session):
    r = session.get(f"{API}/opportunities", params={"sort": "bogus"})
    assert r.status_code == 422


# --- Filters ------------------------------------------------------------------
def test_filter_employment_type_and_work_mode(session):
    r = session.get(
        f"{API}/opportunities",
        params={"employment_type": "Internship", "work_mode": "Remote"},
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    for o in rows:
        assert o["employment_type"] == "Internship"
        assert o["work_mode"] == "Remote"


def test_filter_skills_python_case_insensitive(session):
    r = session.get(f"{API}/opportunities", params={"skills": "Python"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    for o in rows:
        joined = ",".join(o.get("skills") or []).lower()
        assert "python" in joined


def test_filter_role_partial_case_insensitive(session):
    # Seed includes "Business Analyst Intern", "Data Analyst Intern"
    r = session.get(f"{API}/opportunities", params={"role": "Analyst"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    for o in rows:
        assert "analyst" in o["role"].lower()


def test_invalid_employment_type_422(session):
    r = session.get(f"{API}/opportunities", params={"employment_type": "Invalid"})
    assert r.status_code == 422


# --- Create -------------------------------------------------------------------
def test_create_opportunity_success(session):
    payload = {
        "company_name": "TEST_OppCo",
        "role": "TEST Role",
        "employment_type": "Full Time",
        "work_mode": "Remote",
        "skills": ["Python", "FastAPI"],
        "contact_email": "hr@testopp.example",
        "company_website": "https://testopp.example",
    }
    r = session.post(f"{API}/opportunities", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["company_name"] == "TEST_OppCo"
    assert data["status"] == "New"
    assert "id" in data
    # Persistence
    r2 = session.get(f"{API}/opportunities")
    assert any(o["id"] == data["id"] for o in r2.json())


def test_create_missing_required_field_422(session):
    # missing role + employment_type
    r = session.post(f"{API}/opportunities", json={"company_name": "TEST_Bad"})
    assert r.status_code == 422


def test_create_invalid_employment_type_422(session):
    r = session.post(
        f"{API}/opportunities",
        json={"company_name": "TEST_Bad2", "role": "x", "employment_type": "Bogus"},
    )
    assert r.status_code == 422


# --- Status update ------------------------------------------------------------
def test_patch_status_valid(session):
    # create then patch
    created = session.post(
        f"{API}/opportunities",
        json={"company_name": "TEST_StatusCo", "role": "Dev", "employment_type": "Internship"},
    ).json()
    r = session.patch(f"{API}/opportunities/{created['id']}/status", json={"status": "Applied"})
    assert r.status_code == 200
    assert r.json()["status"] == "Applied"
    # verify persistence via list
    listing = session.get(f"{API}/opportunities").json()
    match = next(o for o in listing if o["id"] == created["id"])
    assert match["status"] == "Applied"


def test_patch_status_invalid_422(session):
    created = session.post(
        f"{API}/opportunities",
        json={"company_name": "TEST_StatusCo2", "role": "Dev", "employment_type": "Internship"},
    ).json()
    r = session.patch(f"{API}/opportunities/{created['id']}/status", json={"status": "WrongVal"})
    assert r.status_code == 422


def test_patch_status_unknown_id_404(session):
    r = session.patch(f"{API}/opportunities/nonexistent-id-xyz/status", json={"status": "Applied"})
    assert r.status_code == 404


# --- Save to leads ------------------------------------------------------------
def test_save_to_leads_creates_then_idempotent(session):
    created = session.post(
        f"{API}/opportunities",
        json={
            "company_name": "TEST_SaveToLead",
            "role": "PM",
            "employment_type": "Full Time",
            "contact_email": "p@stl.example",
            "company_website": "https://stl.example",
        },
    ).json()
    # 1st save → creates lead
    r = session.post(f"{API}/opportunities/{created['id']}/save-to-leads")
    assert r.status_code == 200
    body = r.json()
    assert body["created"] is True
    assert body["company"]["company_name"].lower() == "test_savetolead"
    # 2nd save → idempotent, no dupes
    r2 = session.post(f"{API}/opportunities/{created['id']}/save-to-leads")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["created"] is False
    # GET companies → only one row with that name
    cs = session.get(f"{API}/companies", params={"search": "TEST_SaveToLead"}).json()
    matches = [c for c in cs if c["company_name"].lower() == "test_savetolead"]
    assert len(matches) == 1


def test_save_to_leads_unknown_id_404(session):
    r = session.post(f"{API}/opportunities/nonexistent-id-xyz/save-to-leads")
    assert r.status_code == 404


# --- Delete -------------------------------------------------------------------
def test_delete_opportunity_204(session):
    created = session.post(
        f"{API}/opportunities",
        json={"company_name": "TEST_DelOpp", "role": "x", "employment_type": "Internship"},
    ).json()
    r = session.delete(f"{API}/opportunities/{created['id']}")
    assert r.status_code == 204
    # subsequent list excludes
    rows = session.get(f"{API}/opportunities").json()
    assert not any(o["id"] == created["id"] for o in rows)


def test_delete_opportunity_unknown_404(session):
    r = session.delete(f"{API}/opportunities/nonexistent-id-xyz")
    assert r.status_code == 404


# --- Outreach generate (live LLM) --------------------------------------------
def test_outreach_generate_success(session):
    # use a seeded opportunity
    rows = session.get(f"{API}/opportunities").json()
    opp = next((o for o in rows if not o["company_name"].startswith("TEST_")), rows[0])

    payload = {
        "opportunity_id": opp["id"],
        "sender_name": "Aarav Mehta",
        "sender_role": "Final-year CS student at IIT Bombay",
        "sender_pitch": "Built a SQL-powered dashboard analyzing 1M rows in a class project.",
    }
    r = session.post(f"{API}/outreach/generate", json=payload, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["opportunity_id"] == opp["id"]
    assert isinstance(data["subject"], str) and len(data["subject"]) > 0
    assert isinstance(data["body"], str) and len(data["body"]) > 20


def test_outreach_generate_unknown_opp_404(session):
    payload = {
        "opportunity_id": "nonexistent-id-xyz",
        "sender_name": "Test",
        "sender_role": "Test",
        "sender_pitch": "Test",
    }
    r = session.post(f"{API}/outreach/generate", json=payload, timeout=30)
    assert r.status_code == 404
