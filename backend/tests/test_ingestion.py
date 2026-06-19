"""Phase 4A - Opportunity Ingestion tests.

Covers:
- GET /api/ingest/sources (auth + shape)
- POST /api/ingest/opportunity (single) for linkedin / manual / unknown / missing
- Duplicate detection by (source, source_id) and by (company+role) fallback
- POST /api/ingest/opportunities (bulk) shape + in-batch dedupe + errors
- Auto-match: no resume vs active resume (sync) vs >25 (scheduled)
- User isolation across ingestion
- Source-specific normalization: linkedin/naukri/indeed
- Phase 3B regression
"""
from __future__ import annotations

import io
import os
import time
import uuid
import pytest
import requests

# ----------------------- BASE URL ----------------------- #
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
        raise RuntimeError("REACT_APP_BACKEND_URL not set")
    return url.rstrip("/")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"


def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _unique_email(prefix: str = "ing") -> str:
    return f"TEST_{prefix}_{uuid.uuid4().hex[:8]}@leadfinder.app"


def _register(prefix: str = "ing") -> requests.Session:
    s = _new_session()
    email = _unique_email(prefix)
    r = s.post(
        f"{API}/auth/register",
        json={"full_name": f"Ingest {prefix}", "email": email, "password": "Strong1Pass"},
    )
    assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"
    s.user = r.json()
    s.email = email
    # Try to capture bearer token too (in case body returns it)
    body = r.json()
    token = body.get("access_token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# ----------------------- Fixtures ----------------------- #
@pytest.fixture(scope="module")
def user_a():
    return _register("a")


@pytest.fixture(scope="module")
def user_b():
    return _register("b")


@pytest.fixture(scope="module")
def user_resume():
    """A user with an active resume so auto-match returns >0."""
    s = _register("res")
    # Upload a simple text resume
    files = {
        "file": (
            "resume.txt",
            io.BytesIO(
                b"Skills: Python, SQL, Pandas, FastAPI, AWS, Docker.\n"
                b"Experience: 4 years building backend services with FastAPI and MongoDB.\n"
                b"Worked on data pipelines using Pandas and SQL.\n"
            ),
            "text/plain",
        )
    }
    upload_session = requests.Session()
    # Copy auth cookies + headers
    upload_session.cookies.update(s.cookies)
    auth = s.headers.get("Authorization")
    if auth:
        upload_session.headers.update({"Authorization": auth})
    r = upload_session.post(f"{API}/resumes/upload", files=files)
    assert r.status_code in (200, 201), f"resume upload failed: {r.status_code} {r.text[:300]}"
    return s


# ============== GET /ingest/sources ============== #
class TestSourcesEndpoint:
    def test_requires_auth(self):
        # Spec says GET /api/ingest/sources should require auth and return 401
        # without a token. Currently the route has no auth dependency. This
        # test flags the deviation.
        r = requests.get(f"{API}/ingest/sources")
        assert r.status_code == 401, (
            f"BUG: GET /ingest/sources is not protected (got {r.status_code}); "
            "missing Depends(get_current_user) on the route"
        )

    def test_lists_six_adapters(self, user_a):
        r = user_a.get(f"{API}/ingest/sources")
        assert r.status_code == 200, r.text
        body = r.json()
        adapters = body.get("adapters", [])
        sources = {a["source"] for a in adapters}
        expected = {"manual", "linkedin", "naukri", "indeed", "career_page", "startup_discovery"}
        assert expected.issubset(sources), f"missing adapters; got {sources}"
        for a in adapters:
            for k in ("source", "label", "description", "required_fields"):
                assert k in a, f"adapter {a.get('source')} missing key {k}"
            assert isinstance(a["required_fields"], list)


# ============== POST /ingest/opportunity (single) ============== #
class TestSingleIngest:
    def test_linkedin_creates_with_normalization(self, user_a):
        ext_id = f"li_{uuid.uuid4().hex[:8]}"
        payload = {
            "id": ext_id,
            "companyName": "TEST_Acme Corp",
            "jobTitle": "Senior Backend Engineer",
            "workplaceType": "remote",
            "skills": ["Python", "FastAPI", "AWS"],
            "type": "full-time",
            "url": "https://linkedin.com/jobs/view/123",
        }
        r = user_a.post(f"{API}/ingest/opportunity",
                        json={"source": "linkedin", "payload": payload})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "created"
        assert body["source"] == "linkedin"
        assert body["source_id"] == ext_id
        assert body["opportunity_id"]

        # Verify persistence + normalization via /opportunities
        opps = user_a.get(f"{API}/opportunities").json()
        opp = next((o for o in opps if o["id"] == body["opportunity_id"]), None)
        assert opp is not None, "ingested opp not found in /opportunities"
        assert opp["company_name"] == "TEST_Acme Corp"
        assert opp["role"] == "Senior Backend Engineer"
        assert opp["work_mode"] == "Remote", f"work_mode not normalized: {opp.get('work_mode')}"
        assert opp["employment_type"] in ("Internship", "Full Time")
        assert opp["source"] == "linkedin"
        assert opp["source_id"] == ext_id
        # New Phase 4A fields exposed
        for k in ("source_url", "ingested_at"):
            assert k in opp, f"missing field {k} in opportunity response"

    def test_manual_no_source_id(self, user_a):
        payload = {
            "company_name": f"TEST_Manual_{uuid.uuid4().hex[:6]}",
            "role": "Data Analyst",
            "employment_type": "Full Time",
        }
        r = user_a.post(f"{API}/ingest/opportunity",
                        json={"source": "manual", "payload": payload})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "created"
        assert body["opportunity_id"]

    def test_unknown_source_422(self, user_a):
        r = user_a.post(f"{API}/ingest/opportunity",
                        json={"source": "unknown_source", "payload": {"company_name": "x", "role": "y"}})
        assert r.status_code == 422, r.text

    def test_missing_required_fields_422(self, user_a):
        # No company_name -> validate() should raise
        r = user_a.post(f"{API}/ingest/opportunity",
                        json={"source": "linkedin", "payload": {"jobTitle": "Engineer"}})
        assert r.status_code == 422, r.text


# ============== Duplicate detection ============== #
class TestDuplicates:
    def test_duplicate_by_source_id(self, user_a):
        ext_id = f"li_dup_{uuid.uuid4().hex[:8]}"
        payload = {
            "id": ext_id,
            "companyName": "TEST_DupCo",
            "jobTitle": "Engineer Dup",
            "workplaceType": "hybrid",
        }
        r1 = user_a.post(f"{API}/ingest/opportunity",
                         json={"source": "linkedin", "payload": payload})
        assert r1.status_code == 200 and r1.json()["status"] == "created"
        created_id = r1.json()["opportunity_id"]

        # Second call - same source_id should be a duplicate
        r2 = user_a.post(f"{API}/ingest/opportunity",
                         json={"source": "linkedin", "payload": payload})
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body["status"] == "duplicate"
        assert body["duplicate_of"] == created_id
        assert body["opportunity_id"] is None

    def test_duplicate_by_company_role_when_no_source_id(self, user_a):
        company = f"TEST_ManDup_{uuid.uuid4().hex[:6]}"
        payload = {
            "company_name": company,
            "role": "Product Manager",
            "employment_type": "Full Time",
        }
        r1 = user_a.post(f"{API}/ingest/opportunity",
                         json={"source": "manual", "payload": payload})
        assert r1.status_code == 200 and r1.json()["status"] == "created"
        first_id = r1.json()["opportunity_id"]
        r2 = user_a.post(f"{API}/ingest/opportunity",
                         json={"source": "manual", "payload": payload})
        assert r2.status_code == 200
        body = r2.json()
        assert body["status"] == "duplicate"
        assert body["duplicate_of"] == first_id


# ============== Bulk ingest ============== #
class TestBulkIngest:
    def test_bulk_shape_with_in_batch_dedupe(self, user_a):
        ext_id = f"nk_{uuid.uuid4().hex[:8]}"
        items = [
            {"id": ext_id, "companyName": "TEST_Naukri1", "designation": "SDE I",
             "keySkills": "Python, SQL", "type": "fulltime"},
            {"id": f"nk_{uuid.uuid4().hex[:8]}", "companyName": "TEST_Naukri2",
             "designation": "SDE II", "keySkills": "Java, Spring", "type": "fulltime"},
            # duplicate of first (same id) -> in-batch dedupe should kick in
            {"id": ext_id, "companyName": "TEST_Naukri1", "designation": "SDE I",
             "keySkills": "Python, SQL", "type": "fulltime"},
        ]
        r = user_a.post(f"{API}/ingest/opportunities",
                        json={"source": "naukri", "items": items})
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("total", "created", "duplicates", "errors", "results",
                  "matches_computed", "matches_scheduled"):
            assert k in body, f"missing key {k} in bulk response"
        assert body["total"] == 3
        assert body["created"] == 2
        assert body["duplicates"] == 1
        assert body["errors"] == 0
        statuses = [r["status"] for r in body["results"]]
        assert statuses.count("created") == 2 and statuses.count("duplicate") == 1

    def test_bulk_error_for_bad_shape(self, user_a):
        items = [
            {"id": f"ix_{uuid.uuid4().hex[:6]}", "company": "TEST_IndeedCo",
             "jobtitle": "QA Lead", "job_type": "full-time"},
            {"id": f"ix_{uuid.uuid4().hex[:6]}", "jobtitle": "Lonely Role"},  # missing company -> error
        ]
        r = user_a.post(f"{API}/ingest/opportunities",
                        json={"source": "indeed", "items": items})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["errors"] >= 1
        err = next((x for x in body["results"] if x["status"] == "error"), None)
        assert err is not None and err.get("error")


# ============== Auto-match ============== #
class TestAutoMatch:
    def test_no_resume_returns_zero(self, user_b):
        items = [
            {"id": f"li_nores_{i}", "companyName": f"TEST_NoResume{i}",
             "jobTitle": "Backend Dev", "workplaceType": "remote"}
            for i in range(2)
        ]
        r = user_b.post(f"{API}/ingest/opportunities",
                        json={"source": "linkedin", "items": items})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["created"] == 2
        assert body["matches_computed"] == 0
        assert body["matches_scheduled"] is False
        # opps still appear in /opportunities
        opps = user_b.get(f"{API}/opportunities").json()
        assert len([o for o in opps if o.get("source") == "linkedin"]) >= 2

    def test_with_active_resume_sync(self, user_resume):
        # Ingest a small batch (≤25) so it computes synchronously
        items = [
            {"id": f"li_res_{uuid.uuid4().hex[:6]}",
             "companyName": f"TEST_ResCo{i}",
             "jobTitle": "Python Backend Engineer",
             "workplaceType": "remote",
             "skills": ["Python", "FastAPI", "SQL"]}
            for i in range(3)
        ]
        r = user_resume.post(f"{API}/ingest/opportunities",
                             json={"source": "linkedin", "items": items})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["created"] == 3
        assert body["matches_scheduled"] is False
        assert body["matches_computed"] == 3, f"expected 3 sync matches, got {body['matches_computed']}"

        # /matches/batch is GET with repeated opportunity_ids query params
        ids = [res["opportunity_id"] for res in body["results"] if res["status"] == "created"]
        rb = user_resume.get(f"{API}/matches/batch",
                             params=[("opportunity_ids", i) for i in ids])
        assert rb.status_code == 200, rb.text
        items_list = rb.json()
        assert isinstance(items_list, list)
        assert len(items_list) >= 3, f"expected >=3 cached matches, got {len(items_list)}"
        # At least one should have a non-zero skill score (resume has Python/FastAPI/SQL)
        nonzero = [m for m in items_list
                   if (m.get("skill_score", 0) or 0) > 0 or (m.get("jaccard_score", 0) or 0) > 0]
        assert nonzero, f"expected nonzero skill_score given overlap; sample={items_list[:1]}"

    def test_background_scheduled_for_large_batch(self, user_resume):
        # 26 items > SYNC_MATCH_BATCH_LIMIT=25 -> scheduled
        items = [
            {"id": f"li_big_{uuid.uuid4().hex[:8]}",
             "companyName": f"TEST_BigCo{i}",
             "jobTitle": "Python Engineer",
             "workplaceType": "remote",
             "skills": ["Python", "SQL"]}
            for i in range(26)
        ]
        r = user_resume.post(f"{API}/ingest/opportunities",
                             json={"source": "linkedin", "items": items})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["created"] == 26
        assert body["matches_scheduled"] is True
        assert body["matches_computed"] == 0
        ids = [res["opportunity_id"] for res in body["results"] if res["status"] == "created"]
        # wait for background task
        deadline = time.time() + 30
        got = 0
        while time.time() < deadline:
            rb = user_resume.get(f"{API}/matches/batch",
                                 params=[("opportunity_ids", i) for i in ids[:5]])
            if rb.status_code == 200:
                items_list = rb.json()
                if items_list and any(
                    (m.get("overall_score") is not None) or (m.get("jaccard_score") is not None)
                    for m in items_list
                ):
                    got = len(items_list)
                    break
            time.sleep(1.5)
        assert got >= 1, "background match computation did not produce results within 30s"


# ============== User isolation ============== #
class TestIsolation:
    def test_userb_does_not_see_usera_ingested(self, user_a, user_b):
        ext_id = f"iso_{uuid.uuid4().hex[:8]}"
        r = user_a.post(f"{API}/ingest/opportunity", json={
            "source": "linkedin",
            "payload": {"id": ext_id, "companyName": "TEST_IsoCo",
                        "jobTitle": "Iso Engineer", "workplaceType": "onsite"},
        })
        assert r.status_code == 200 and r.json()["status"] == "created"
        a_opp_id = r.json()["opportunity_id"]

        b_opps = user_b.get(f"{API}/opportunities").json()
        assert all(o["id"] != a_opp_id for o in b_opps), "userB sees userA's opp!"

    def test_userb_can_ingest_same_external_id_as_new_row(self, user_a, user_b):
        ext_id = f"iso2_{uuid.uuid4().hex[:8]}"
        payload = {"id": ext_id, "companyName": "TEST_IsoCo2",
                   "jobTitle": "Engineer", "workplaceType": "remote"}
        ra = user_a.post(f"{API}/ingest/opportunity",
                         json={"source": "linkedin", "payload": payload})
        assert ra.status_code == 200 and ra.json()["status"] == "created"
        a_id = ra.json()["opportunity_id"]

        rb = user_b.post(f"{API}/ingest/opportunity",
                         json={"source": "linkedin", "payload": payload})
        assert rb.status_code == 200, rb.text
        body = rb.json()
        assert body["status"] == "created", \
            f"expected userB to create new row, got {body}"
        assert body["opportunity_id"] != a_id


# ============== Source-specific normalization ============== #
class TestSourceNormalization:
    def test_linkedin_alt_keys(self, user_a):
        payload = {
            "id": f"li_alt_{uuid.uuid4().hex[:6]}",
            "companyName": "TEST_LIAlt",
            "jobTitle": "Engineer",
            "workplaceType": "Hybrid",
        }
        r = user_a.post(f"{API}/ingest/opportunity",
                        json={"source": "linkedin", "payload": payload})
        assert r.status_code == 200 and r.json()["status"] == "created", r.text
        opp = next((o for o in user_a.get(f"{API}/opportunities").json()
                    if o["id"] == r.json()["opportunity_id"]), None)
        assert opp["company_name"] == "TEST_LIAlt"
        assert opp["role"] == "Engineer"
        assert opp["work_mode"] == "Hybrid"

    def test_naukri_designation_and_keyskills(self, user_a):
        payload = {
            "id": f"nk_alt_{uuid.uuid4().hex[:6]}",
            "companyName": "TEST_NaukriAlt",
            "designation": "Java Developer",
            "keySkills": "Java; Spring; SQL",
        }
        r = user_a.post(f"{API}/ingest/opportunity",
                        json={"source": "naukri", "payload": payload})
        assert r.status_code == 200 and r.json()["status"] == "created", r.text
        opp = next((o for o in user_a.get(f"{API}/opportunities").json()
                    if o["id"] == r.json()["opportunity_id"]), None)
        assert opp["role"] == "Java Developer"
        skills = [s.lower() for s in (opp.get("skills") or [])]
        assert "java" in skills and "spring" in skills and "sql" in skills

    def test_indeed_jobtitle_and_company(self, user_a):
        payload = {
            "id": f"ix_alt_{uuid.uuid4().hex[:6]}",
            "company": "TEST_IndeedAlt",
            "jobtitle": "QA Engineer",
            "job_type": "full-time",
        }
        r = user_a.post(f"{API}/ingest/opportunity",
                        json={"source": "indeed", "payload": payload})
        assert r.status_code == 200 and r.json()["status"] == "created", r.text
        opp = next((o for o in user_a.get(f"{API}/opportunities").json()
                    if o["id"] == r.json()["opportunity_id"]), None)
        assert opp["company_name"] == "TEST_IndeedAlt"
        assert opp["role"] == "QA Engineer"
        assert opp["employment_type"] == "Full Time"


# ============== Regression ============== #
class TestRegression:
    def test_opportunities_seed_still_works(self, user_a):
        r = user_a.post(f"{API}/opportunities/seed")
        assert r.status_code in (200, 201), r.text
        opps = user_a.get(f"{API}/opportunities").json()
        assert len(opps) >= 5

    def test_matches_batch_still_works(self, user_resume):
        opps = user_resume.get(f"{API}/opportunities").json()
        ids = [o["id"] for o in opps[:3]]
        if not ids:
            pytest.skip("no opportunities available")
        r = user_resume.get(f"{API}/matches/batch",
                            params=[("opportunity_ids", i) for i in ids])
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_resumes_active_still_works(self, user_resume):
        r = user_resume.get(f"{API}/resumes/active")
        assert r.status_code == 200, r.text
