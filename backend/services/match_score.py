"""Deterministic match scoring (no LLM calls).

Two scorers:
1. Weighted Jaccard on skills + role/experience/location bonuses  -> overall_score
2. TF-IDF cosine between resume text and opportunity description  -> tfidf_score (advanced)

Both are cheap, transparent, and explainable.  AI scoring is applied separately
and cached in MongoDB per (resume_id, opportunity_id).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable, List, Optional, Sequence


_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "of", "to", "for", "with", "from",
    "by", "at", "as", "is", "are", "was", "were", "be", "been", "being", "this", "that",
    "these", "those", "we", "you", "i", "it", "they", "he", "she", "our", "your", "their",
    "will", "would", "should", "can", "could", "may", "might", "have", "has", "had", "do",
    "does", "did", "not", "no", "yes", "if", "then", "else", "than", "so", "such", "also",
}


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{1,}", (text or "").lower()) if t not in _STOPWORDS]


def _norm_set(items: Iterable[str]) -> set:
    return {_norm(x) for x in items if x and _norm(x)}


# ---------------------------------------------------------------------------- #
# Public scorers
# ---------------------------------------------------------------------------- #
def jaccard_skills(resume_skills: Sequence[str], opp_skills: Sequence[str]) -> dict:
    a = _norm_set(resume_skills)
    b = _norm_set(opp_skills)
    if not a and not b:
        return {"score": 0.0, "matched": [], "missing": [], "extra": []}
    matched = sorted(a & b)
    missing = sorted(b - a)
    extra = sorted(a - b)
    union = a | b
    score = len(matched) / len(union) if union else 0.0
    return {
        "score": round(score, 4),
        "matched": matched,
        "missing": missing,
        "extra": extra,
    }


def role_relevance(resume_text: str, preferred_roles: Sequence[str], opp_role: str) -> dict:
    role = _norm(opp_role)
    if not role:
        return {"score": 0.0, "explanation": "No role specified on opportunity."}

    role_tokens = [t for t in re.findall(r"[a-z]+", role) if t not in _STOPWORDS and len(t) > 2]
    if not role_tokens:
        return {"score": 0.0, "explanation": "Could not extract role keywords."}

    text = (resume_text or "").lower()
    hits = sum(1 for t in role_tokens if re.search(rf"\b{re.escape(t)}\b", text))
    base = hits / len(role_tokens)

    pref_hit = any(_norm(r) and _norm(r) in role for r in (preferred_roles or []))
    if pref_hit:
        base = min(1.0, base + 0.25)

    if base >= 0.75:
        msg = f"Strong match — {hits}/{len(role_tokens)} role keywords found"
    elif base >= 0.4:
        msg = f"Partial match — {hits}/{len(role_tokens)} role keywords found"
    else:
        msg = f"Weak match — only {hits}/{len(role_tokens)} role keywords found"
    if pref_hit:
        msg += " · matches a preferred role"
    return {"score": round(base, 4), "explanation": msg}


def experience_relevance(years_experience: Optional[float], employment_type: str) -> dict:
    yrs = float(years_experience) if years_experience is not None else None
    et = _norm(employment_type)
    if yrs is None:
        return {
            "score": 0.5,
            "explanation": "Experience not detected on resume - using neutral score.",
        }

    if et == "internship":
        if yrs <= 2:
            return {"score": 1.0, "explanation": f"{yrs} yrs fits internship range (0-2 yrs)."}
        if yrs <= 4:
            return {"score": 0.7, "explanation": f"{yrs} yrs is slightly over the internship range."}
        return {"score": 0.4, "explanation": f"{yrs} yrs is over-qualified for an internship."}
    if et == "full time":
        if yrs >= 2:
            return {"score": 1.0, "explanation": f"{yrs} yrs meets full-time expectations."}
        return {"score": 0.5 + yrs * 0.2, "explanation": f"{yrs} yrs is below typical full-time."}
    return {"score": 0.5, "explanation": "Unknown employment type."}


def location_relevance(preferred_locations: Sequence[str], opp_location: Optional[str], work_mode: Optional[str]) -> dict:
    if work_mode and _norm(work_mode) == "remote":
        return {"score": 1.0, "explanation": "Remote — accessible from anywhere."}
    if not preferred_locations:
        return {"score": 0.5, "explanation": "No location preferences set — neutral score."}
    if not opp_location:
        return {"score": 0.5, "explanation": "Opportunity has no location specified."}
    opp = _norm(opp_location)
    prefs = [_norm(p) for p in preferred_locations]
    hit = any(p and (p in opp or opp in p) for p in prefs)
    if hit:
        return {"score": 1.0, "explanation": f"Matches preferred location '{opp_location}'."}
    if "remote" in prefs:
        return {"score": 0.7, "explanation": "You prefer Remote — partial fit."}
    return {"score": 0.2, "explanation": f"'{opp_location}' is not in your preferences."}


def compute_breakdown(
    resume_text: str,
    resume_skills: Sequence[str],
    years_experience: Optional[float],
    preferred_roles: Sequence[str],
    preferred_locations: Sequence[str],
    opp_role: str,
    opp_skills: Sequence[str],
    opp_employment_type: str,
    opp_location: Optional[str],
    opp_work_mode: Optional[str],
) -> dict:
    jacc = jaccard_skills(resume_skills, opp_skills)
    role = role_relevance(resume_text, preferred_roles, opp_role)
    exp = experience_relevance(years_experience, opp_employment_type)
    loc = location_relevance(preferred_locations, opp_location, opp_work_mode)

    # Weights chosen to keep skills dominant while still recognising fit signals.
    overall = (
        0.55 * jacc["score"]
        + 0.20 * role["score"]
        + 0.15 * exp["score"]
        + 0.10 * loc["score"]
    )
    return {
        "overall_score": round(overall, 4),
        "jaccard_score": jacc["score"],
        "breakdown": {
            "matched_skills": jacc["matched"],
            "missing_skills": jacc["missing"],
            "extra_skills": jacc["extra"],
            "skill_score": jacc["score"],
            "role_relevance": role["score"],
            "role_explanation": role["explanation"],
            "experience_relevance": exp["score"],
            "experience_explanation": exp["explanation"],
            "location_relevance": loc["score"],
            "location_explanation": loc["explanation"],
        },
    }


# ---------------------------------------------------------------------------- #
# TF-IDF cosine (advanced view) - implemented without sklearn.
# ---------------------------------------------------------------------------- #
def _tf(counter: Counter) -> dict:
    total = sum(counter.values()) or 1
    return {tok: c / total for tok, c in counter.items()}


def tfidf_cosine(resume_text: str, opp_text: str) -> float:
    a = _tokens(resume_text)
    b = _tokens(opp_text)
    if not a or not b:
        return 0.0
    ca, cb = Counter(a), Counter(b)
    doc_freq: Counter = Counter()
    for tok in set(ca):
        doc_freq[tok] += 1
    for tok in set(cb):
        doc_freq[tok] += 1
    N = 2
    idf = {tok: math.log((N + 1) / (df + 1)) + 1 for tok, df in doc_freq.items()}
    tfa = _tf(ca)
    tfb = _tf(cb)

    vocab = set(tfa) | set(tfb)
    dot = 0.0
    na = 0.0
    nb = 0.0
    for tok in vocab:
        va = tfa.get(tok, 0.0) * idf.get(tok, 1.0)
        vb = tfb.get(tok, 0.0) * idf.get(tok, 1.0)
        dot += va * vb
        na += va * va
        nb += vb * vb
    if na <= 0 or nb <= 0:
        return 0.0
    return round(dot / (math.sqrt(na) * math.sqrt(nb)), 4)
