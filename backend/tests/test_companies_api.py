"""Backend API tests for Startup Lead Finder."""
import os
import csv
import io
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    yield s
    # Cleanup TEST_ prefixed companies
    try:
        r = s.get(f"{API}/companies")
        for c in r.json():
            if c.get("company_name", "").startswith("TEST_"):
                s.delete(f"{API}/companies/{c['id']}")
    except Exception:
        pass


# --- Health ---
def test_health(session):
    r = session.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


# --- Create ---
def test_create_company_success(session):
    payload = {"company_name": "TEST_Acme", "website": "https://acme.example", "email": "founder@acme.example"}
    r = session.post(f"{API}/companies", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert "id" in data and isinstance(data["id"], str) and len(data["id"]) > 0
    assert "created_at" in data and isinstance(data["created_at"], str)
    assert data["company_name"] == "TEST_Acme"
    assert data["website"] == "https://acme.example"
    assert data["email"] == "founder@acme.example"

    # Verify persistence
    r2 = session.get(f"{API}/companies")
    assert r2.status_code == 200
    assert any(c["id"] == data["id"] for c in r2.json())


def test_create_missing_company_name_422(session):
    r = session.post(f"{API}/companies", json={"website": "https://x.com"})
    assert r.status_code == 422


def test_create_invalid_email_422(session):
    r = session.post(f"{API}/companies", json={"company_name": "TEST_BadEmail", "email": "not-an-email"})
    assert r.status_code == 422


# --- List ordering ---
def test_list_sorted_desc(session):
    a = session.post(f"{API}/companies", json={"company_name": "TEST_Alpha"}).json()
    b = session.post(f"{API}/companies", json={"company_name": "TEST_Bravo"}).json()
    r = session.get(f"{API}/companies")
    assert r.status_code == 200
    ids = [c["id"] for c in r.json()]
    # b created after a -> b should appear before a
    assert ids.index(b["id"]) < ids.index(a["id"])


# --- Search ---
def test_search_case_insensitive_partial(session):
    name = "TEST_UniqueSearchableZZZ"
    created = session.post(f"{API}/companies", json={"company_name": name}).json()
    r = session.get(f"{API}/companies", params={"search": "uniquesearchablezzz"})
    assert r.status_code == 200
    results = r.json()
    assert any(c["id"] == created["id"] for c in results)
    # all results contain the substring (case-insensitive)
    for c in results:
        assert "uniquesearchablezzz" in c["company_name"].lower()


# --- Delete ---
def test_delete_204_then_not_found(session):
    created = session.post(f"{API}/companies", json={"company_name": "TEST_ToDelete"}).json()
    cid = created["id"]
    r = session.delete(f"{API}/companies/{cid}")
    assert r.status_code == 204
    # Subsequent GET list should not contain it
    r2 = session.get(f"{API}/companies")
    assert not any(c["id"] == cid for c in r2.json())


def test_delete_nonexistent_404(session):
    r = session.delete(f"{API}/companies/nonexistent-uuid-xyz")
    assert r.status_code == 404


# --- Stats ---
def test_stats_counts(session):
    # Create known-state test items
    session.post(f"{API}/companies", json={"company_name": "TEST_StatsA", "email": "a@b.com", "website": "https://a.com"})
    session.post(f"{API}/companies", json={"company_name": "TEST_StatsB", "email": "b@c.com"})
    session.post(f"{API}/companies", json={"company_name": "TEST_StatsC", "website": "https://c.com"})
    r = session.get(f"{API}/companies/stats")
    assert r.status_code == 200
    s = r.json()
    assert "total" in s and "with_email" in s and "with_website" in s
    assert isinstance(s["total"], int)
    assert s["with_email"] >= 2
    assert s["with_website"] >= 2
    assert s["total"] >= s["with_email"]
    assert s["total"] >= s["with_website"]


# --- CSV Export ---
def test_export_csv(session):
    session.post(f"{API}/companies", json={"company_name": "TEST_CsvCo", "email": "x@y.com"})
    r = session.get(f"{API}/companies/export.csv")
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "text/csv" in ct
    reader = csv.reader(io.StringIO(r.text))
    rows = list(reader)
    assert rows[0] == ["id", "company_name", "website", "email", "created_at"]
    assert len(rows) >= 2  # header + at least one row
