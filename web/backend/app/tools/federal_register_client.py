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

NOTE: The FR API requires raw (unencoded) brackets in query params, e.g.
  fields[]=title   NOT   fields%5B%5D=title
`requests` always re-encodes [ ] via requote_uri(), causing 400 errors.
We use urllib.request instead, which sends the URL as-is.
"""

import json
import urllib.parse
import urllib.request
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
    Build a query string keeping bracket characters unencoded.
    safe='[]' prevents urllib from percent-encoding [ and ].
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


def _get(url: str) -> dict:
    """
    HTTP GET using stdlib urllib.request, which does NOT re-encode the URL.
    Raises urllib.error.HTTPError on 4xx/5xx (compatible with raise_for_status).
    """
    req = urllib.request.Request(url, headers={"User-Agent": "BillSurfer/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
    data = _get(url)
    docs = data.get("results", [])
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
    data = _get(url)
    docs = data.get("results", [])
    return sorted([_enrich(d) for d in docs], key=lambda x: x["rbs"], reverse=True)
