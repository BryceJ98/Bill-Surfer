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

import urllib.parse
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
    return {**doc, "rbs": _score(doc)}


def _build_url(path: str, params: dict) -> str:
    """
    Build a URL keeping bracket characters unencoded (e.g. fields[], conditions[type][]).
    The Federal Register API parses raw brackets; requests encodes them to %5B%5D which
    causes a 400 Bad Request.
    """
    parts = []
    for key, val in params.items():
        enc_key = urllib.parse.quote(str(key), safe="[]")
        if isinstance(val, list):
            for item in val:
                parts.append(f"{enc_key}={urllib.parse.quote(str(item), safe='')}")
        else:
            parts.append(f"{enc_key}={urllib.parse.quote(str(val), safe='')}")
    return f"{path}?{'&'.join(parts)}"


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
    url  = _build_url(f"{BASE}/documents.json", params)
    resp = requests.get(url, timeout=15)
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
    url  = _build_url(f"{BASE}/documents.json", params)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    docs = resp.json().get("results", [])
    return sorted([_enrich(d) for d in docs], key=lambda x: x["rbs"], reverse=True)
