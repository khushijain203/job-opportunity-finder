"""Phase 3B - Resume upload + parsing + match score (incl. AI cache).

Tests run against the public REACT_APP_BACKEND_URL. They create TEST_ users
(prefixed for easy cleanup), upload small .txt resumes, seed opportunities,
and verify match-score + caching + user isolation.

Note: enrich + AI score endpoints make REAL Claude calls (~5-15s). Each is
called twice in the same test to verify the cache returns unchanged
ai_enriched_at without a second LLM call.
"""

from __future__ import annotations

import io
import os
import time
import uuid

import pytest
import requests

_url = os.environ.get("REACT_APP_BACKEND_URL")
if not _url:
    # fall back to the frontend env file used by the running app
    try:
        with open("/app/frontend/.env") as _f:
            for _ln in _f:
                if _ln.startswith("REACT_APP_BACKEND_URL="):
                    _url = _ln.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        pass
if not _url:
    raise RuntimeError("REACT_APP_BACKEND_URL not configured")
BASE_URL = _url.rstrip("/")
API = f"{BASE_URL}/api"

RESUME_TXT = (
    "John Tester\nEmail: john.tester@example.com | Phone: +91-98765-43210\n\n"
    "SUMMARY\n"
    "QA automation engineer with 3 years of experience building Python\n"
    "test frameworks for SaaS apps.\n\n"
    "SKILLS\n"
    "Python, SQL, Selenium, Pandas, FastAPI, PyTest, REST APIs, Linux, CI/CD\n\n"
    "EXPERIENCE\n"
    "Senior QA Engineer, Acme Corp (2022-2025) - Built Selenium + PyTest\n"
    "regression suites, integrated with Jenkins CI/CD.\n"
    "QA Engineer, Beta Inc (2021-2022) - Wrote API tests against FastAPI services.\n\n"
    "EDUCATION\nB.E. Computer Science, IIT Madras, 2021\n"
)


def _password():
    return "Tester1234!"


def _register(email: str) -> requests.Session:
    s = requests.Session()
    r = s.post(
        f"{API}/auth/register",
        json={"full_name": "Tester", "email": email, "password": _password()},
        timeout=20,
    )
    assert r.status_code in (200, 201), f"register: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def user_a():
    email = f"TEST_3b_a_{uuid.uuid4().hex[:8]}@leadfinder.app"
    s = _register(email)
    yield s, email
    try:
        s.post(f"{API}/auth/logout", timeout=5)
    except Exception:
        pass


@pytest.fixture(scope="module")
def user_b():
    email = f"TEST_3b_b_{uuid.uuid4().hex[:8]}@leadfinder.app"
    s = _register(email)
    yield s, email
    try:
        s.post(f"{API}/auth/logout", timeout=5)
    except Exception:
        pass


def _upload(session: requests.Session, content: bytes = None, filename="resume.txt", ctype="text/plain"):
    if content is None:
        content = RESUME_TXT.encode()
    files = {"file": (filename, io.BytesIO(content), ctype)}
    return session.post(f"{API}/resumes/upload", files=files, timeout=30)


# ----------------- Upload basic ----------------- #
class TestResumeUpload:
    def test_upload_no_auth_returns_401(self):
        files = {"file": ("r.txt", io.BytesIO(b"hi"), "text/plain")}
        r = requests.post(f"{API}/resumes/upload", files=files, timeout=10)
        assert r.status_code == 401

    def test_upload_unsupported_ext_415(self, user_a):
        s, _ = user_a
        r = _upload(s, content=b"MZ\x00\x00", filename="evil.exe", ctype="application/octet-stream")
        assert r.status_code == 415, r.text

    def test_upload_empty_file_400(self, user_a):
        s, _ = user_a
        r = _upload(s, content=b"", filename="empty.txt")
        assert r.status_code == 400, r.text

    def test_upload_txt_success(self, user_a):
        s, _ = user_a
        r = _upload(s)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["id"]
        assert body["raw_text_chars"] > 100
        assert body["is_active"] is True
        skills = [x.lower() for x in body["parsed"]["skills"]]
        assert len(skills) > 0
        # Should mine at least a few of these
        assert any(sk in skills for sk in ("python", "sql", "selenium", "pandas", "fastapi"))
        # store on the fixture session for downstream tests
        s._first_resume_id = body["id"]

    def test_first_resume_autosaves_profile_skills(self, user_a):
        s, _ = user_a
        r = s.get(f"{API}/profile", timeout=10)
        assert r.status_code == 200
        prof = r.json()
        skills = [str(x).lower() for x in (prof.get("skills") or [])]
        # at least one resume-mined skill should appear
        assert any(sk in skills for sk in ("python", "sql", "selenium", "pandas", "fastapi")), prof

    def test_second_upload_marks_new_active(self, user_a):
        s, _ = user_a
        r = _upload(s, content=(RESUME_TXT + "\nExtra: Docker, AWS\n").encode())
        assert r.status_code == 201, r.text
        new_id = r.json()["id"]
        assert new_id != getattr(s, "_first_resume_id", None)

        lst = s.get(f"{API}/resumes", timeout=10).json()
        assert len(lst) >= 2
        actives = [x for x in lst if x["is_active"]]
        assert len(actives) == 1
        assert actives[0]["id"] == new_id
        s._active_resume_id = new_id
        s._old_resume_id = getattr(s, "_first_resume_id", None)

    def test_get_active(self, user_a):
        s, _ = user_a
        r = s.get(f"{API}/resumes/active", timeout=10)
        assert r.status_code == 200
        assert r.json()["id"] == s._active_resume_id

    def test_activate_old_then_back(self, user_a):
        s, _ = user_a
        old = s._old_resume_id
        r = s.post(f"{API}/resumes/{old}/activate", timeout=10)
        assert r.status_code == 200
        assert r.json()["is_active"] is True
        # restore new active
        r = s.post(f"{API}/resumes/{s._active_resume_id}/activate", timeout=10)
        assert r.status_code == 200

    def test_delete_old_resume_soft_deletes(self, user_a):
        s, _ = user_a
        old = s._old_resume_id
        r = s.delete(f"{API}/resumes/{old}", timeout=10)
        assert r.status_code == 204
        lst = s.get(f"{API}/resumes", timeout=10).json()
        assert all(x["id"] != old for x in lst)


# ----------------- Opportunities meta & freshness ----------------- #
class TestOpportunitiesMeta:
    def test_meta_includes_freshness_windows(self, user_a):
        s, _ = user_a
        r = s.get(f"{API}/opportunities/meta", timeout=10)
        assert r.status_code == 200
        assert r.json().get("freshness_windows") == ["24h", "3d", "7d", "30d"]

    def test_invalid_freshness_422(self, user_a):
        s, _ = user_a
        r = s.get(f"{API}/opportunities", params={"freshness": "99h"}, timeout=10)
        assert r.status_code == 422

    def test_seed_for_user_a(self, user_a):
        s, _ = user_a
        # may already have items from another test class run
        r = s.post(f"{API}/opportunities/seed", timeout=10)
        assert r.status_code == 200
        # then list
        r = s.get(f"{API}/opportunities", timeout=10)
        assert r.status_code == 200
        opps = r.json()
        assert len(opps) >= 5
        # New nullable fields must be present in the schema
        sample = opps[0]
        for key in ("date_posted", "last_verified", "freshness_score", "date_found"):
            assert key in sample, f"missing {key} on opportunity response"
        s._opp_ids = [o["id"] for o in opps][:5]

    def test_freshness_24h_returns_recent_seeded(self, user_a):
        s, _ = user_a
        # seeded date_found is "now" so 24h should include them
        r = s.get(f"{API}/opportunities", params={"freshness": "24h"}, timeout=10)
        assert r.status_code == 200
        assert len(r.json()) >= 5


# ----------------- Matches: deterministic ----------------- #
class TestMatchesDeterministic:
    def test_match_returns_breakdown(self, user_a):
        s, _ = user_a
        # Pick a Python-heavy opp from seed (Lumen Data Labs or ScriptForge)
        opps = s.get(f"{API}/opportunities", timeout=10).json()
        target = next(
            (o for o in opps if "Python" in (o.get("skills") or [])), opps[0]
        )
        s._target_opp = target["id"]
        r = s.get(f"{API}/matches/opportunity/{target['id']}", timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body is not None
        assert 0.0 <= body["overall_score"] <= 1.0
        assert body["jaccard_score"] >= 0.0
        b = body["breakdown"]
        for key in (
            "matched_skills",
            "missing_skills",
            "extra_skills",
            "skill_score",
            "role_relevance",
            "role_explanation",
            "experience_relevance",
            "experience_explanation",
            "location_relevance",
            "location_explanation",
        ):
            assert key in b, f"breakdown missing {key}"
        # Should have matched at least one skill since resume has Python/SQL
        assert len(b["matched_skills"]) > 0

    def test_tfidf_query_populates_score(self, user_a):
        s, _ = user_a
        opp_id = s._target_opp
        r = s.get(
            f"{API}/matches/opportunity/{opp_id}", params={"tfidf": "true"}, timeout=20
        )
        assert r.status_code == 200
        body = r.json()
        assert body["tfidf_score"] >= 0.0
        # second call returns same
        r2 = s.get(
            f"{API}/matches/opportunity/{opp_id}", params={"tfidf": "true"}, timeout=20
        )
        assert r2.json()["tfidf_score"] == body["tfidf_score"]

    def test_batch_returns_rows(self, user_a):
        s, _ = user_a
        params = [("opportunity_ids", x) for x in s._opp_ids]
        r = s.get(f"{API}/matches/batch", params=params, timeout=30)
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == len(s._opp_ids)
        for row in rows:
            assert "matched_count" in row and "missing_count" in row
            assert row["overall_score"] >= 0.0


# ----------------- Matches: no resume case ----------------- #
class TestMatchesNoResume:
    def test_no_resume_returns_null(self, user_b):
        s, _ = user_b
        # user_b has no resume + no opps yet -> seed and try
        s.post(f"{API}/opportunities/seed", timeout=10)
        opps = s.get(f"{API}/opportunities", timeout=10).json()
        assert opps, "user_b should have seeded opps"
        r = s.get(f"{API}/matches/opportunity/{opps[0]['id']}", timeout=10)
        assert r.status_code == 200
        assert r.json() is None


# ----------------- User isolation ----------------- #
class TestUserIsolation:
    def test_user_b_cannot_see_user_a_opp_match(self, user_a, user_b):
        sa, _ = user_a
        sb, _ = user_b
        a_opp = sa._target_opp
        r = sb.get(f"{API}/matches/opportunity/{a_opp}", timeout=10)
        # b has resume? no — but opp also doesn't belong to b -> 404 expected
        # Actually b currently has NO resume so route returns None before checking opp.
        # Upload a resume for b to force the opp lookup branch.
        if r.status_code == 200 and r.json() is None:
            up = _upload(sb)
            assert up.status_code == 201, up.text
            r = sb.get(f"{API}/matches/opportunity/{a_opp}", timeout=10)
        assert r.status_code == 404, r.text

    def test_user_b_resumes_isolated(self, user_a, user_b):
        sa, _ = user_a
        sb, _ = user_b
        list_a = sa.get(f"{API}/resumes", timeout=10).json()
        list_b = sb.get(f"{API}/resumes", timeout=10).json()
        ids_a = {r["id"] for r in list_a}
        ids_b = {r["id"] for r in list_b}
        assert ids_a.isdisjoint(ids_b)


# ----------------- AI cache (resume enrich + match AI) ----------------- #
class TestAICache:
    def test_resume_enrich_cached(self, user_a):
        s, _ = user_a
        resume_id = s._active_resume_id
        t0 = time.time()
        r1 = s.post(f"{API}/resumes/{resume_id}/enrich", timeout=60)
        elapsed1 = time.time() - t0
        assert r1.status_code == 200, r1.text
        first = r1.json()
        assert first["ai_enriched_at"], first
        # second call - must be cached (timestamp unchanged)
        r2 = s.post(f"{API}/resumes/{resume_id}/enrich", timeout=20)
        assert r2.status_code == 200
        second = r2.json()
        assert second["ai_enriched_at"] == first["ai_enriched_at"], (first, second)
        # cached call should be fast — sanity tolerance
        # (not asserted strictly to avoid flakiness)
        print(f"enrich first={elapsed1:.1f}s cached path returned")

    def test_match_ai_cached(self, user_a):
        s, _ = user_a
        opp_id = s._target_opp
        r1 = s.post(f"{API}/matches/opportunity/{opp_id}/ai", timeout=60)
        assert r1.status_code == 200, r1.text
        first = r1.json()
        assert first["ai_score"] is not None
        assert 0 <= first["ai_score"] <= 100
        assert first["ai_summary"]
        assert first["ai_enriched_at"]
        # second call cached
        r2 = s.post(f"{API}/matches/opportunity/{opp_id}/ai", timeout=15)
        assert r2.status_code == 200
        second = r2.json()
        assert second["ai_enriched_at"] == first["ai_enriched_at"]
        assert second["ai_score"] == first["ai_score"]


# ----------------- Resume delete clears cached matches ----------------- #
class TestCacheInvalidation:
    def test_delete_active_resume_clears_match_cache(self, user_a):
        s, _ = user_a
        # ensure a cached match exists for current active resume
        opp_id = s._target_opp
        r = s.get(f"{API}/matches/opportunity/{opp_id}", timeout=10)
        assert r.status_code == 200
        # delete active resume
        active_id = s._active_resume_id
        r = s.delete(f"{API}/resumes/{active_id}", timeout=10)
        assert r.status_code == 204
        # now no active resume -> match endpoint returns None
        r = s.get(f"{API}/matches/opportunity/{opp_id}", timeout=10)
        assert r.status_code == 200
        assert r.json() is None
