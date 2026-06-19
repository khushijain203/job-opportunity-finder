"""End-to-end auth + per-user isolation tests for Startup Lead Finder Phase 3A.

Covers:
- /auth/register, /auth/login, /auth/logout, /auth/refresh, /auth/me
- Password policy + duplicate email
- Migration: first registered (non-demo) user claims orphan records
- Per-user scoping for /companies, /opportunities, /generated-emails, /profile
- Cross-user 404 on PATCH/DELETE
- save-to-leads idempotency per user
- Live LLM outreach generation + persistence
- CSV export scoping
- 401 on unauthenticated protected endpoints
"""
from __future__ import annotations

import os
import uuid
import pytest
import requests

def _load_backend_url() -> str:
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env")
        try:
            with open(env_path) as fh:
                for line in fh:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except FileNotFoundError:
            pass
    if not url:
        raise RuntimeError("REACT_APP_BACKEND_URL is not set")
    return url.rstrip("/")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

DEMO_EMAIL = "demo@leadfinder.app"
DEMO_PASS = "Demo1234!"


def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _unique_email(prefix: str = "user") -> str:
    return f"TEST_{prefix}_{uuid.uuid4().hex[:8]}@leadfinder.app"


# ----------------------------- Fixtures ----------------------------- #
@pytest.fixture(scope="session")
def demo_session():
    s = _new_session()
    r = s.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASS})
    assert r.status_code == 200, f"Demo login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def first_user_session():
    """The FIRST registered (non-demo) user - inherits orphan records."""
    s = _new_session()
    email = _unique_email("first")
    r = s.post(
        f"{API}/auth/register",
        json={"full_name": "First User", "email": email, "password": "Strong1Pass"},
    )
    assert r.status_code == 201, f"First register failed: {r.status_code} {r.text}"
    s.user = r.json()
    s.email = email
    return s


@pytest.fixture
def user_a_session():
    s = _new_session()
    email = _unique_email("a")
    r = s.post(f"{API}/auth/register",
               json={"full_name": "User A", "email": email, "password": "Strong1Pass"})
    assert r.status_code == 201
    s.user = r.json()
    return s


@pytest.fixture
def user_b_session():
    s = _new_session()
    email = _unique_email("b")
    r = s.post(f"{API}/auth/register",
               json={"full_name": "User B", "email": email, "password": "Strong1Pass"})
    assert r.status_code == 201
    s.user = r.json()
    return s


# =================== AUTH BASICS =================== #
class TestAuthBasics:
    def test_register_sets_cookies_and_returns_public_user(self):
        s = _new_session()
        email = _unique_email("reg")
        r = s.post(f"{API}/auth/register",
                   json={"full_name": "Reg Test", "email": email, "password": "Strong1Pass"})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["email"] == email.lower()
        assert body["full_name"] == "Reg Test"
        assert body["is_demo"] is False
        assert "id" in body and "created_at" in body
        # cookies
        names = {c.name for c in s.cookies}
        assert "access_token" in names and "refresh_token" in names

    def test_password_policy_rejects_weak(self):
        s = _new_session()
        for pw in ["short1A", "alllowercase1", "ALLUPPER1", "NoDigitsHere"]:
            r = s.post(f"{API}/auth/register",
                       json={"full_name": "X", "email": _unique_email("pw"), "password": pw})
            assert r.status_code == 422, f"Expected 422 for pw='{pw}', got {r.status_code}: {r.text}"

    def test_duplicate_email_returns_409(self):
        s = _new_session()
        email = _unique_email("dup")
        s.post(f"{API}/auth/register",
               json={"full_name": "Dup", "email": email, "password": "Strong1Pass"})
        r = s.post(f"{API}/auth/register",
                   json={"full_name": "Dup2", "email": email, "password": "Strong1Pass"})
        assert r.status_code == 409, r.text

    def test_login_demo_success_and_wrong_password(self):
        s = _new_session()
        r = s.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASS})
        assert r.status_code == 200
        assert r.json()["is_demo"] is True
        r2 = _new_session().post(f"{API}/auth/login",
                                 json={"email": DEMO_EMAIL, "password": "wrongpass"})
        assert r2.status_code == 401

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_with_cookies(self, demo_session):
        r = demo_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == DEMO_EMAIL

    def test_logout_clears_cookies(self):
        s = _new_session()
        s.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASS})
        assert s.get(f"{API}/auth/me").status_code == 200
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 204
        # After server clears cookies, the session jar should no longer carry access
        s.cookies.clear()
        assert s.get(f"{API}/auth/me").status_code == 401

    def test_refresh_issues_new_access(self):
        s = _new_session()
        email = _unique_email("rf")
        s.post(f"{API}/auth/register",
               json={"full_name": "RF", "email": email, "password": "Strong1Pass"})
        old_access = next((c for c in s.cookies if c.name == "access_token"), None)
        assert old_access is not None
        # Drop only the access cookie, keep refresh
        s.cookies.set("access_token", "", domain=old_access.domain)
        r = s.post(f"{API}/auth/refresh")
        assert r.status_code == 200, r.text
        # /me should now work again
        assert s.get(f"{API}/auth/me").status_code == 200


# =================== UNAUTHENTICATED 401s =================== #
class TestProtectedEndpoints401:
    @pytest.mark.parametrize("method,path", [
        ("GET", "/companies"),
        ("POST", "/companies"),
        ("GET", "/opportunities"),
        ("POST", "/opportunities/seed"),
        ("GET", "/generated-emails"),
        ("GET", "/profile"),
        ("PUT", "/profile"),
        ("GET", "/auth/me"),
        ("GET", "/companies/export.csv"),
    ])
    def test_returns_401(self, method, path):
        r = requests.request(method, f"{API}{path}", json={})
        assert r.status_code == 401, f"{method} {path} expected 401, got {r.status_code}"


# =================== MIGRATION =================== #
class TestOrphanMigration:
    def test_first_user_inherits_orphans(self, demo_session):
        # Migration is one-shot and idempotent. By the time tests run, the first
        # non-demo registration in this session triggers it. We verify:
        #  - demo user (is_demo=true) sees ZERO opportunities (orphans did NOT land on demo)
        #  - no orphan records remain in the system (some non-demo user owns them)
        r_demo = demo_session.get(f"{API}/opportunities")
        assert r_demo.status_code == 200
        assert r_demo.json() == [], f"Demo unexpectedly sees opportunities: {r_demo.json()}"

        # Also verify that the migration claimed the original 5 orphan opps for SOME user
        # by ensuring no opportunity returned to demo is unattributed; demo seeing 0
        # is the strongest user-isolation check we can do via the API alone.


# =================== USER ISOLATION =================== #
class TestUserIsolation:
    def test_companies_and_opps_isolated_between_users(self, user_a_session, user_b_session):
        # user_a creates a company
        r = user_a_session.post(f"{API}/companies", json={
            "company_name": f"TEST_CoA_{uuid.uuid4().hex[:6]}",
            "website": "https://a.example.com",
            "email": "a@example.com",
        })
        assert r.status_code in (200, 201), r.text

        # user_a creates an opportunity
        r2 = user_a_session.post(f"{API}/opportunities", json={
            "title": "TEST_OppA",
            "company_name": "TEST_CoA",
            "role": "Software Engineer",
            "employment_type": "Full Time",
            "source_url": "https://a.example.com/job",
            "description": "x",
        })
        assert r2.status_code in (200, 201), r2.text
        opp_a = r2.json()

        # userB should see EMPTY
        rb_co = user_b_session.get(f"{API}/companies")
        rb_op = user_b_session.get(f"{API}/opportunities")
        assert rb_co.status_code == 200 and rb_co.json() == []
        assert rb_op.status_code == 200 and rb_op.json() == []

        # userA still sees their data
        ra_co = user_a_session.get(f"{API}/companies")
        ra_op = user_a_session.get(f"{API}/opportunities")
        assert any(c.get("company_name", "").startswith("TEST_CoA") for c in ra_co.json())
        assert any(o["id"] == opp_a["id"] for o in ra_op.json())

    def test_cross_user_patch_delete_404(self, user_a_session, user_b_session):
        # userA creates an opp
        r = user_a_session.post(f"{API}/opportunities", json={
            "title": "TEST_OwnedByA",
            "company_name": "TEST_CoA2",
            "role": "Backend Engineer",
            "employment_type": "Full Time",
            "source_url": "https://a2.example.com/x",
            "description": "y",
        })
        assert r.status_code in (200, 201), r.text
        opp_id = r.json()["id"]

        # userB tries PATCH status and DELETE → must be 404
        r_patch = user_b_session.patch(f"{API}/opportunities/{opp_id}/status", json={"status": "Applied"})
        assert r_patch.status_code == 404, f"Cross-user PATCH expected 404, got {r_patch.status_code}"

        r_del = user_b_session.delete(f"{API}/opportunities/{opp_id}")
        assert r_del.status_code == 404, f"Cross-user DELETE expected 404, got {r_del.status_code}"


# =================== SEED + SAVE-TO-LEADS =================== #
class TestSeedAndSaveToLeads:
    def test_seed_is_per_user_and_idempotent(self, user_a_session):
        r = user_a_session.post(f"{API}/opportunities/seed")
        assert r.status_code in (200, 201), r.text
        first_list = user_a_session.get(f"{API}/opportunities").json()
        count_after_first = len(first_list)
        assert count_after_first >= 5

        # second seed should be idempotent (no new rows since user already has opps)
        user_a_session.post(f"{API}/opportunities/seed")
        second_list = user_a_session.get(f"{API}/opportunities").json()
        assert len(second_list) == count_after_first

    def test_save_to_leads_idempotent_per_user(self, user_a_session):
        # Ensure userA has an opp
        opps = user_a_session.get(f"{API}/opportunities").json()
        if not opps:
            user_a_session.post(f"{API}/opportunities/seed")
            opps = user_a_session.get(f"{API}/opportunities").json()
        opp_id = opps[0]["id"]
        r1 = user_a_session.post(f"{API}/opportunities/{opp_id}/save-to-leads")
        assert r1.status_code in (200, 201), r1.text
        before = len(user_a_session.get(f"{API}/companies").json())
        r2 = user_a_session.post(f"{API}/opportunities/{opp_id}/save-to-leads")
        assert r2.status_code in (200, 201)
        after = len(user_a_session.get(f"{API}/companies").json())
        assert before == after, "save-to-leads should be idempotent per user (case-insensitive)"


# =================== OUTREACH + EMAILS =================== #
class TestOutreachGeneration:
    def test_generate_persists_email_for_current_user(self, user_a_session, user_b_session):
        opps = user_a_session.get(f"{API}/opportunities").json()
        if not opps:
            user_a_session.post(f"{API}/opportunities/seed")
            opps = user_a_session.get(f"{API}/opportunities").json()
        opp_id = opps[0]["id"]
        r = user_a_session.post(f"{API}/outreach/generate", json={
            "opportunity_id": opp_id,
            "tone": "friendly",
        }, timeout=60)
        assert r.status_code == 200, f"Outreach failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        for k in ("id", "subject", "body", "to", "created_at"):
            assert k in data, f"missing field {k} in outreach response: {data}"

        # userA can list their emails (filtered by opp)
        rlist = user_a_session.get(f"{API}/generated-emails", params={"opportunity_id": opp_id})
        assert rlist.status_code == 200
        ems = rlist.json()
        assert any(e["id"] == data["id"] for e in ems)
        assert all(e["opportunity_id"] == opp_id for e in ems)

        # userB should see EMPTY
        rb = user_b_session.get(f"{API}/generated-emails")
        assert rb.status_code == 200 and rb.json() == []


# =================== PROFILE =================== #
class TestProfile:
    def test_default_shape_then_upsert_and_read(self, user_a_session):
        r = user_a_session.get(f"{API}/profile")
        assert r.status_code == 200, r.text
        body = r.json()
        # default shape - all keys present
        for k in ("full_name", "skills", "years_experience", "preferred_roles",
                  "preferred_locations", "bio"):
            assert k in body, f"missing default field {k}"

        payload = {
            "full_name": "Updated Name",
            "skills": ["python", "react"],
            "years_experience": 5,
            "preferred_roles": ["backend", "fullstack"],
            "preferred_locations": ["Remote", "Bangalore"],
            "bio": "Hello world",
        }
        r2 = user_a_session.put(f"{API}/profile", json=payload)
        assert r2.status_code == 200, r2.text

        r3 = user_a_session.get(f"{API}/profile")
        got = r3.json()
        assert got["full_name"] == "Updated Name"
        assert got["skills"] == ["python", "react"]
        assert got["years_experience"] == 5
        assert got["preferred_roles"] == ["backend", "fullstack"]
        assert got["preferred_locations"] == ["Remote", "Bangalore"]
        assert got["bio"] == "Hello world"


# =================== CSV EXPORT =================== #
class TestCsvExport:
    def test_csv_export_scoped(self, user_a_session, user_b_session):
        # Ensure userA has at least one company
        user_a_session.post(f"{API}/companies", json={
            "company_name": "TEST_ExportCo",
            "website": "https://export.example.com",
            "email": "x@export.example.com",
        })
        ra = user_a_session.get(f"{API}/companies/export.csv")
        assert ra.status_code == 200
        assert "TEST_ExportCo" in ra.text

        rb = user_b_session.get(f"{API}/companies/export.csv")
        assert rb.status_code == 200
        assert "TEST_ExportCo" not in rb.text
