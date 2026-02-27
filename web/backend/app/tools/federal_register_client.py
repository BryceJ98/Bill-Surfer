"""
federal_register_client.py — Federal Register API client.

No API key required — fully public.
Base URL: https://www.federalregister.gov/api/v1/

Implements the Regulatory Burden Score (RBS) from the BillSurfer burden engine:
  - Baseline:         10 pts (any govt action)
  - Economically significant rule: +40
  - CFR references:   +5 per ref (max 20)
  - Friction keywords: +3 each (compliance, penalty, mandatory, etc.)
  - Document type:    RULE +15 | PRORULE +10 | PRESDOCU +10 | NOTICE 0
  - Cap: 100
"""

import requests
from datetime import datetime

BASE = "https://www.federalregister.gov/api/v1"

_FIELDS = [
    "document_number", "title", "type", "abstract",
    "agency_names", "publication_date", "html_url",
    "significant", "cfr_references", "comment_url",
    "effective_on", "comment_date",
]

_FRICTION_TERMS = [
    "mandatory", "compliance", "penalty", "fines", "reporting",
    "deadline", "prohibited", "requirement", "audit", "enforcement",
]

_TYPE_WEIGHTS = {"RULE": 15, "PRORULE": 10, "PRESDOCU": 10, "NOTICE": 0}


def _score(doc: dict) -> int:
    score = 10
    if doc.get("significant"):
        score += 40
    score += min(len(doc.get("cfr_references") or []) * 5, 20)
    text = (doc.get("abstract") or "").lower()
    score += sum(3 for t in _FRICTION_TERMS if t in text)
    score += _TYPE_WEIGHTS.get(doc.get("type", ""), 0)
    return min(score, 100)


def _enrich(doc: dict) -> dict:
    rbs = _score(doc)
    return {
        **doc,
        "rbs":    rbs,
        "impact": "HIGH" if rbs > 60 else "MED" if rbs > 30 else "LOW",
    }


def get_daily_digest(date: str | None = None, limit: int = 20) -> list[dict]:
    """
    Fetch Rules, Proposed Rules, and Executive Orders published on `date`
    (defaults to today), enriched with RBS scores, sorted highest first.
    """
    target = date or datetime.now().strftime("%Y-%m-%d")
    params = {
        "conditions[publication_date][is]": target,
        "conditions[type][]":               ["RULE", "PRORULE", "PRESDOCU"],
        "per_page":                          limit,
        "fields[]":                          _FIELDS,
    }
    resp = requests.get(f"{BASE}/documents.json", params=params, timeout=15)
    resp.raise_for_status()
    docs = resp.json().get("results", [])
    return sorted([_enrich(d) for d in docs], key=lambda x: x["rbs"], reverse=True)


def search_documents(keyword: str, doc_types: list[str] | None = None, limit: int = 20) -> list[dict]:
    """
    Search FR documents by keyword, newest first, with RBS scores.
    doc_types defaults to Rules, Proposed Rules, Executive Orders.
    """
    params = {
        "conditions[term]":   keyword,
        "conditions[type][]": doc_types or ["RULE", "PRORULE", "PRESDOCU"],
        "sort":               "newest",
        "per_page":           limit,
        "fields[]":           _FIELDS,
    }
    resp = requests.get(f"{BASE}/documents.json", params=params, timeout=15)
    resp.raise_for_status()
    docs = resp.json().get("results", [])
    return sorted([_enrich(d) for d in docs], key=lambda x: x["rbs"], reverse=True)
