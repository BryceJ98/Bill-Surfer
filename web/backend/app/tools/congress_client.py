"""
congress_client.py — Congress.gov API v3 client for Bill-Surfer

Mirrors the functional, dict-based patterns of legiscan_client.py.

Setup:
    export CONGRESS_API_KEY=your_key_here
    Get a free key at: https://api.congress.gov/sign-up/

Usage:
    import congress_client as cc

    # Bills
    results = cc.search_bills("infrastructure")
    bill    = cc.get_bill(119, "hr", 1)
    text    = cc.get_bill_text(119, "hr", 1)
    actions = cc.get_bill_actions(119, "hr", 1)
    cosps   = cc.get_bill_cosponsors(119, "hr", 1)
    summary = cc.get_bill_summaries(119, "hr", 1)

    # Amendments
    amdts   = cc.search_amendments(119, "hamdt")
    amdt    = cc.get_amendment(119, "hamdt", 1)

    # Treaties
    treats  = cc.search_treaties(119)
    treaty  = cc.get_treaty(119, 1)
    t_acts  = cc.get_treaty_actions(119, 1)

    # Nominations
    noms    = cc.search_nominations(119, query="secretary")
    nom     = cc.get_nomination(119, 42)
    noms_n  = cc.get_nomination_nominees(119, 42)

    # Congressional Record
    issues  = cc.search_congressional_record(year=2025, month=1)
    arts    = cc.get_congressional_record_articles(volume=171, issue=1)

    # CRS Reports
    reports = cc.search_crs_reports("healthcare")
    report  = cc.get_crs_report("R40000")

    # Communications
    h_comms = cc.search_house_communications(119, "ec")
    s_comms = cc.search_senate_communications(119, "pm")

    # House Roll Call Votes (BETA — 118th Congress onward)
    votes   = cc.search_house_votes(119, session=1)
    vote    = cc.get_house_vote(119, 1, 42)

    # Committee Reports
    rpts    = cc.search_committee_reports(119, "hrpt")
    rpt     = cc.get_committee_report(119, "hrpt", 100)

    # Hearings
    hrgs    = cc.search_hearings(119, "house")

    # Members
    members = cc.search_members(name="Sanders", state="VT")
    member  = cc.get_member("S000033")
    votes   = cc.get_member_votes("S000033")
    spons   = cc.get_member_sponsored("S000033")
    cospons = cc.get_member_cosponsored("S000033")
    all_m   = cc.get_members_by_congress(119, "Senate")

    # Historical range search (new)
    nom_hist = cc.search_nominations_range("secretary", from_congress=115, to_congress=119)
    trt_hist = cc.search_treaties_range("extradition", from_congress=100, to_congress=119)
    crs_hist = cc.search_crs_reports("healthcare", from_date="2015-01-01", to_date="2020-12-31")
    cr_kw    = cc.search_congressional_record_by_keyword("budget", month=1, year=2025)
"""

import hashlib
import html as _html_mod
import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests

# Load .env file from the repo root (two levels up from this file) if present.
# This lets the key work without restarting VS Code after setx.
def _load_dotenv() -> None:
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

_load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY  = os.getenv("CONGRESS_API_KEY")
BASE_URL = "https://api.congress.gov/v3"

CACHE_DIR = Path.home() / ".congress_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Endpoints whose responses are safe to cache
CACHEABLE_PATHS = {
    "/member/",
    "/bill/",
    "/treaty/",
    "/nomination/",
    "/crsReport/",
    "/committee-report/",
    "/hearing/",
    "/house-communication/",
    "/senate-communication/",
    "/amendment/",
}

# ---------------------------------------------------------------------------
# Bill-type normalisation
# ---------------------------------------------------------------------------

_TYPE_ALIASES: dict[str, str] = {
    "hr": "hr", "h.r.": "hr", "h.r": "hr", "hb": "hr",
    "s": "s", "s.": "s", "sb": "s",
    "hres": "hres", "h.res.": "hres", "h.res": "hres",
    "sres": "sres", "s.res.": "sres", "s.res": "sres",
    "hjres": "hjres", "h.j.res.": "hjres", "h.j.res": "hjres",
    "sjres": "sjres", "s.j.res.": "sjres", "s.j.res": "sjres",
    "hconres": "hconres", "h.con.res.": "hconres", "h.con.res": "hconres",
    "sconres": "sconres", "s.con.res.": "sconres", "s.con.res": "sconres",
}

FEDERAL_PREFIXES = set(_TYPE_ALIASES.keys())

CHAMBER_LABEL: dict[str, str] = {
    "hr": "House", "hres": "House", "hjres": "House", "hconres": "House",
    "s":  "Senate", "sres": "Senate", "sjres": "Senate", "sconres": "Senate",
}

BILL_TYPE_LABEL: dict[str, str] = {
    "hr": "H.R.", "hres": "H.Res.", "hjres": "H.J.Res.", "hconres": "H.Con.Res.",
    "s":  "S.",   "sres": "S.Res.", "sjres": "S.J.Res.", "sconres": "S.Con.Res.",
}


def _normalise_type(raw: str) -> str | None:
    return _TYPE_ALIASES.get(raw.lower().strip())


# ---------------------------------------------------------------------------
# Current-congress calculation
# ---------------------------------------------------------------------------

def current_congress() -> int:
    """Return the current U.S. Congress number (119th begins Jan 2025)."""
    year = datetime.now().year
    if year % 2 == 1:
        return (year - 1789) // 2 + 1
    return (year - 1790) // 2 + 1


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_BILL_RE = re.compile(
    r"""
    (?:(\d{2,3})[-\s])?
    (h\.?r\.?|h\.?j\.?res\.?|h\.?con\.?res\.?|h\.?res\.?|
     s\.?j\.?res\.?|s\.?con\.?res\.?|s\.?res\.?|s\.?)
    \s*(\d+)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def parse_bill_identifier(identifier: str) -> dict:
    """
    Parse a federal bill string into structured components.

    Examples:
        "HR 1234"     -> {"bill_type": "hr", "bill_number": 1234, "congress": 119}
        "S.456"       -> {"bill_type": "s",  "bill_number": 456,  "congress": 119}
        "119-HR 1"    -> {"bill_type": "hr", "bill_number": 1,    "congress": 119}
        "H.J.Res. 22" -> {"bill_type": "hjres", "bill_number": 22, "congress": 119}
    """
    m = _BILL_RE.search(identifier.strip())
    if not m:
        return {"error": f"Could not parse federal bill identifier: '{identifier}'"}

    congress_str, type_raw, number_str = m.groups()
    bill_type = _normalise_type(type_raw)
    if not bill_type:
        return {"error": f"Unrecognised bill type: '{type_raw}'"}

    return {
        "bill_type":   bill_type,
        "bill_number": int(number_str),
        "congress":    int(congress_str) if congress_str else current_congress(),
    }


def is_federal_identifier(text: str) -> bool:
    """Return True if text looks like a federal bill number."""
    return bool(_BILL_RE.search(text.strip()))


def is_federal_state(state: str) -> bool:
    """Return True if the state code refers to federal/Congress."""
    return state.strip().lower() in {"us", "federal", "congress", "dc", "usa"}


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

def _cache_path(path: str, params: dict) -> Path:
    key = json.dumps({"path": path, "params": params}, sort_keys=True)
    return CACHE_DIR / (hashlib.md5(key.encode()).hexdigest() + ".json")


def _load_cache(path: str, params: dict):
    cp = _cache_path(path, params)
    try:
        if cp.exists():
            return json.loads(cp.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _save_cache(path: str, params: dict, data: dict) -> None:
    try:
        _cache_path(path, params).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def _is_cacheable(path: str) -> bool:
    return any(seg in path for seg in CACHEABLE_PATHS)


# ---------------------------------------------------------------------------
# Core request
# ---------------------------------------------------------------------------

def _request(path: str, params: dict | None = None, use_cache: bool = True, api_key: str | None = None) -> dict:
    """
    Make a GET request to the Congress.gov API.

    Args:
        path:      URL path relative to BASE_URL (e.g. "/bill/119/hr/1")
        params:    Extra query parameters (api_key and format are added automatically)
        use_cache: Whether to check/save the cache
        api_key:   Override the global API_KEY (used for per-user keys in the web app)

    Returns:
        Parsed JSON dict, or {"error": str} on failure.
    """
    resolved_key = api_key or API_KEY
    if not resolved_key:
        return {"error": "CONGRESS_API_KEY environment variable is not set. "
                         "Get a free key at https://api.congress.gov/sign-up/"}

    params = params or {}
    cache_params = dict(params)

    if use_cache and _is_cacheable(path):
        cached = _load_cache(path, cache_params)
        if cached is not None:
            return cached

    full_params = {**params, "api_key": resolved_key, "format": "json"}
    url = BASE_URL.rstrip("/") + path

    try:
        resp = requests.get(url, params=full_params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.ConnectionError:
        return {"error": "Network error: could not connect to Congress.gov API"}
    except requests.Timeout:
        return {"error": "Request timed out"}
    except requests.HTTPError as e:
        return {"error": f"HTTP error: {e}"}
    except requests.RequestException as e:
        return {"error": f"Request failed: {e}"}

    if use_cache and _is_cacheable(path):
        _save_cache(path, cache_params, data)

    return data


def _fetch_text_url(url: str) -> str | None:
    """Fetch plain-text content from a Congress.gov or GovInfo URL."""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def _strip_html(text: str) -> str:
    """Strip HTML tags and unescape entities from a string."""
    text = _html_mod.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Bills — search
# ---------------------------------------------------------------------------

def search_bills(
    query: str,
    congress: int | None = None,
    bill_type: str | None = None,
    offset: int = 0,
    limit: int = 20,
    api_key: str | None = None,
) -> dict:
    """
    Search federal bills by keyword.

    Args:
        query:     Search keywords
        congress:  Congress number (default: current)
        bill_type: Filter by type ("hr", "s", etc.) — optional
        offset:    Pagination offset
        limit:     Results per page (max 250)

    Returns:
        {"bills": [...], "total": int, "offset": int, "congress": int}
    """
    congress = congress or current_congress()

    if bill_type:
        bt = _normalise_type(bill_type)
        if not bt:
            return {"error": f"Unknown bill type: '{bill_type}'"}
        path = f"/bill/{congress}/{bt}"
    else:
        path = f"/bill/{congress}"

    params: dict = {"offset": offset, "limit": limit}
    data = _request(path, params, use_cache=False, api_key=api_key)
    if "error" in data:
        return data

    bills_raw = data.get("bills", [])

    if query:
        q_lower = query.lower()
        filtered = []
        for b in bills_raw:
            title    = (b.get("title") or "").lower()
            number   = (b.get("number") or "").lower()
            subjects = (b.get("policyArea", {}).get("name") or "").lower()
            if q_lower in title or q_lower in number or q_lower in subjects:
                filtered.append(b)
        bills_raw = filtered

    return {
        "bills":    [_normalise_bill_summary(b) for b in bills_raw],
        "total":    data.get("pagination", {}).get("count", len(bills_raw)),
        "offset":   offset,
        "congress": congress,
        "query":    query,
    }


def _normalise_bill_summary(raw: dict) -> dict:
    bt = (raw.get("type") or "").lower()
    return {
        "bill_id":         f"{raw.get('congress', '')}-{bt}-{raw.get('number', '')}",
        "congress":        raw.get("congress"),
        "bill_type":       bt,
        "bill_number":     raw.get("number"),
        "title":           raw.get("title", ""),
        "chamber":         CHAMBER_LABEL.get(bt, ""),
        "bill_label":      f"{BILL_TYPE_LABEL.get(bt, bt.upper())} {raw.get('number', '')}",
        "status":          raw.get("latestAction", {}).get("text", ""),
        "status_date":     raw.get("latestAction", {}).get("actionDate", ""),
        "url":             raw.get("url", ""),
        "origin_chamber":  raw.get("originChamber", ""),
        "policy_area":     raw.get("policyArea", {}).get("name", ""),
        "introduced_date": raw.get("introducedDate", ""),
        "sponsors":        raw.get("sponsors", []),
    }


# ---------------------------------------------------------------------------
# Bills — detail, text, actions, cosponsors, summaries
# ---------------------------------------------------------------------------

def get_bill(congress: int, bill_type: str, bill_number: int, api_key: str | None = None) -> dict:
    """Retrieve full bill details from Congress.gov."""
    bt = _normalise_type(str(bill_type))
    if not bt:
        return {"error": f"Unknown bill type: '{bill_type}'"}

    path = f"/bill/{congress}/{bt}/{bill_number}"
    data = _request(path, api_key=api_key)
    if "error" in data:
        return data

    return _normalise_bill_detail(data.get("bill", data), congress, bt, bill_number)


def _normalise_bill_detail(raw: dict, congress: int, bt: str, number: int) -> dict:
    sponsors = raw.get("sponsors", [])
    primary_sponsor = sponsors[0] if sponsors else {}
    latest_action   = raw.get("latestAction", {})
    policy_area     = raw.get("policyArea", {})
    subjects        = raw.get("subjects", {})
    label           = f"{BILL_TYPE_LABEL.get(bt, bt.upper())} {number}"

    return {
        "bill_id":         f"{congress}-{bt}-{number}",
        "congress":        congress,
        "bill_type":       bt,
        "bill_number":     number,
        "bill_label":      label,
        "chamber":         CHAMBER_LABEL.get(bt, ""),
        "title":           raw.get("title", ""),
        "short_title":     raw.get("shortTitle", [{}])[-1].get("title", "") if raw.get("shortTitle") else "",
        "policy_area":     policy_area.get("name", ""),
        "subjects":        [s.get("name", "") for s in subjects.get("legislativeSubjects", [])],
        "status":          latest_action.get("text", ""),
        "status_date":     latest_action.get("actionDate", ""),
        "introduced_date": raw.get("introducedDate", ""),
        "primary_sponsor": {
            "name":        primary_sponsor.get("fullName", ""),
            "party":       primary_sponsor.get("party", ""),
            "state":       primary_sponsor.get("state", ""),
            "bioguide_id": primary_sponsor.get("bioguideId", ""),
            "district":    primary_sponsor.get("district", ""),
        },
        "cosponsor_count":  raw.get("cosponsors", {}).get("count", 0),
        "action_count":     raw.get("actions", {}).get("count", 0),
        "text_count":       raw.get("textVersions", {}).get("count", 0),
        "amendment_count":  raw.get("amendments", {}).get("count", 0),
        "url":              raw.get("url", ""),
        "govtrack_url":     f"https://www.govtrack.us/congress/bills/{congress}/{bt}{number}",
        "congress_url":     f"https://www.congress.gov/bill/{congress}th-congress/{_chamber_path(bt)}/{number}",
    }


def _chamber_path(bt: str) -> str:
    return "house-bill" if bt in {"hr", "hres", "hjres", "hconres"} else "senate-bill"


def get_bill_text(congress: int, bill_type: str, bill_number: int) -> dict:
    """Retrieve and return the text of a federal bill (downloads Formatted Text when available)."""
    bt = _normalise_type(str(bill_type))
    if not bt:
        return {"error": f"Unknown bill type: '{bill_type}'"}

    path = f"/bill/{congress}/{bt}/{bill_number}/text"
    data = _request(path)
    if "error" in data:
        return data

    versions = data.get("textVersions", [])
    if not versions:
        return {"error": f"No text versions available for {BILL_TYPE_LABEL.get(bt, bt)} {bill_number}"}

    priority_order = [
        "enrolled bill", "engrossed amendment senate", "engrossed amendment house",
        "engrossed in senate", "engrossed in house",
        "reported in senate", "reported in house",
        "placed on calendar senate", "placed on calendar house",
        "referred in senate", "referred in house",
        "introduced in senate", "introduced in house",
    ]

    def _rank(v: dict) -> int:
        vtype = v.get("type", "").lower()
        for i, p in enumerate(priority_order):
            if p in vtype:
                return i
        return len(priority_order)

    best     = sorted(versions, key=_rank)[0]
    formats  = {f["type"]: f["url"] for f in best.get("formats", [])}
    text_url = formats.get("Formatted Text") or formats.get("Formatted XML")
    pdf_url  = formats.get("PDF", "")

    result = {
        "version":    best.get("type", ""),
        "date":       best.get("date", ""),
        "bill_label": f"{BILL_TYPE_LABEL.get(bt, bt.upper())} {bill_number}",
        "url":        text_url or pdf_url,
        "pdf_url":    pdf_url,
        "text":       "",
    }

    if text_url:
        content = _fetch_text_url(text_url)
        if content:
            result["text"]      = content
            result["text_size"] = len(content)
        else:
            result["note"] = f"Could not fetch text content. Access directly: {text_url}"
    else:
        result["note"] = f"Only PDF available. Access at: {pdf_url}"

    return result


def get_bill_actions(congress: int, bill_type: str, bill_number: int, limit: int = 50, api_key: str | None = None) -> dict:
    """Retrieve the full action history for a federal bill."""
    bt = _normalise_type(str(bill_type))
    if not bt:
        return {"error": f"Unknown bill type: '{bill_type}'"}

    path = f"/bill/{congress}/{bt}/{bill_number}/actions"
    data = _request(path, {"limit": limit}, api_key=api_key)
    if "error" in data:
        return data

    actions = data.get("actions", [])
    return {
        "actions": [
            {
                "date":        a.get("actionDate", ""),
                "text":        a.get("text", ""),
                "action_code": a.get("actionCode", ""),
                "type":        a.get("type", ""),
                "chamber":     a.get("sourceSystem", {}).get("name", ""),
            }
            for a in actions
        ],
        "count": data.get("pagination", {}).get("count", len(actions)),
    }


def get_bill_cosponsors(congress: int, bill_type: str, bill_number: int, limit: int = 100) -> dict:
    """Retrieve cosponsors for a federal bill."""
    bt = _normalise_type(str(bill_type))
    if not bt:
        return {"error": f"Unknown bill type: '{bill_type}'"}

    path = f"/bill/{congress}/{bt}/{bill_number}/cosponsors"
    data = _request(path, {"limit": limit})
    if "error" in data:
        return data

    cosponsors = data.get("cosponsors", [])
    return {
        "cosponsors": [
            {
                "name":           c.get("fullName", ""),
                "party":          c.get("party", ""),
                "state":          c.get("state", ""),
                "district":       c.get("district", ""),
                "bioguide_id":    c.get("bioguideId", ""),
                "sponsored_date": c.get("sponsorshipDate", ""),
            }
            for c in cosponsors
        ],
        "count": data.get("pagination", {}).get("count", len(cosponsors)),
    }


def get_bill_summaries(congress: int, bill_type: str, bill_number: int, api_key: str | None = None) -> dict:
    """Retrieve Congressional Research Service (CRS) summaries for a bill."""
    bt = _normalise_type(str(bill_type))
    if not bt:
        return {"error": f"Unknown bill type: '{bill_type}'"}

    path = f"/bill/{congress}/{bt}/{bill_number}/summaries"
    data = _request(path, api_key=api_key)
    if "error" in data:
        return data

    summaries = data.get("summaries", [])
    if not summaries:
        return {"summaries": [], "latest": ""}

    latest = sorted(summaries, key=lambda s: s.get("actionDate", ""), reverse=True)[0]
    return {
        "summaries":    summaries,
        "latest":       _strip_html(latest.get("text", "")),
        "latest_date":  latest.get("actionDate", ""),
        "latest_type":  latest.get("actionDesc", ""),
    }


# ---------------------------------------------------------------------------
# Amendments
# ---------------------------------------------------------------------------

AMENDMENT_TYPES = {"hamdt": "House Amendment", "samdt": "Senate Amendment", "suamdt": "Senate Unprinted Amendment"}


def search_amendments(
    congress: int | None = None,
    amendment_type: str = "hamdt",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    List amendments for a given congress and type.

    Args:
        congress:       Congress number (default: current)
        amendment_type: "hamdt" (House), "samdt" (Senate), or "suamdt" (Senate unprinted)
        limit:          Results per page
        offset:         Pagination offset
    """
    congress = congress or current_congress()
    at = amendment_type.lower()
    if at not in AMENDMENT_TYPES:
        return {"error": f"Unknown amendment type: '{amendment_type}'. Use: {', '.join(AMENDMENT_TYPES)}"}

    path = f"/amendment/{congress}/{at}"
    data = _request(path, {"limit": limit, "offset": offset}, use_cache=False)
    if "error" in data:
        return data

    amendments = data.get("amendments", [])
    return {
        "amendments":     [_normalise_amendment(a) for a in amendments],
        "type_label":     AMENDMENT_TYPES[at],
        "count":          data.get("pagination", {}).get("count", len(amendments)),
        "congress":       congress,
    }


def get_amendment(congress: int, amendment_type: str, amendment_number: int) -> dict:
    """Retrieve a specific amendment."""
    at = amendment_type.lower()
    if at not in AMENDMENT_TYPES:
        return {"error": f"Unknown amendment type: '{amendment_type}'"}

    path = f"/amendment/{congress}/{at}/{amendment_number}"
    data = _request(path)
    if "error" in data:
        return data

    return _normalise_amendment(data.get("amendment", data))


def _normalise_amendment(raw: dict) -> dict:
    return {
        "congress":          raw.get("congress"),
        "number":            raw.get("number"),
        "type":              raw.get("type", "").lower(),
        "type_label":        AMENDMENT_TYPES.get(raw.get("type", "").lower(), raw.get("type", "")),
        "purpose":           raw.get("purpose", ""),
        "description":       raw.get("description", ""),
        "sponsor":           raw.get("sponsor", {}).get("fullName", ""),
        "sponsor_party":     raw.get("sponsor", {}).get("party", ""),
        "sponsor_state":     raw.get("sponsor", {}).get("state", ""),
        "latest_action":     raw.get("latestAction", {}).get("text", ""),
        "latest_action_date": raw.get("latestAction", {}).get("actionDate", ""),
        "submitted_date":    raw.get("submittedDate", ""),
        "proposed_date":     raw.get("proposedDate", ""),
        "url":               raw.get("url", ""),
    }


# ---------------------------------------------------------------------------
# Treaties
# ---------------------------------------------------------------------------

def search_treaties(congress: int | None = None, limit: int = 20, offset: int = 0, api_key: str | None = None) -> dict:
    """
    List treaties received by a given Congress.

    Returns:
        {"treaties": [...], "count": int, "congress": int}
    """
    congress = congress or current_congress()
    path = f"/treaty/{congress}"
    data = _request(path, {"limit": limit, "offset": offset}, use_cache=False, api_key=api_key)
    if "error" in data:
        return data

    treaties = data.get("treaties", [])
    return {
        "treaties": [_normalise_treaty_summary(t) for t in treaties],
        "count":    data.get("pagination", {}).get("count", len(treaties)),
        "congress": congress,
    }


def get_treaty(congress: int, treaty_number: int, suffix: str | None = None) -> dict:
    """
    Retrieve full details for a specific treaty.

    Args:
        congress:      Congress number
        treaty_number: Treaty document number
        suffix:        Letter suffix for multi-part treaties (e.g., "A", "B")
    """
    path = f"/treaty/{congress}/{treaty_number}"
    if suffix:
        path += f"/{suffix.upper()}"

    data = _request(path)
    if "error" in data:
        return data

    return _normalise_treaty_detail(data.get("treaty", data))


def get_treaty_actions(congress: int, treaty_number: int) -> dict:
    """Retrieve the action history for a treaty."""
    path = f"/treaty/{congress}/{treaty_number}/actions"
    data = _request(path)
    if "error" in data:
        return data

    actions = data.get("actions", [])
    return {
        "actions": [
            {"date": a.get("actionDate", ""), "text": a.get("text", ""), "type": a.get("type", "")}
            for a in actions
        ],
        "count": len(actions),
    }


def _normalise_treaty_summary(raw: dict) -> dict:
    congress = raw.get("congress")
    number   = raw.get("number", raw.get("treatyNum", ""))
    return {
        "congress":         congress,
        "number":           number,
        "suffix":           raw.get("suffix"),
        "topic":            raw.get("topic", raw.get("treatySubject", "")),
        "transmitted_date": raw.get("transmittedDate", ""),
        "in_force_date":    raw.get("inForceDate", ""),
        "status":           raw.get("latestAction", {}).get("text", ""),
        "status_date":      raw.get("latestAction", {}).get("actionDate", ""),
        "parts_count":      raw.get("parts", {}).get("count", 0) if isinstance(raw.get("parts"), dict) else 0,
        "url":              raw.get("url", ""),
        "congress_url":     f"https://www.congress.gov/treaty-document/{congress}th-congress/treaty-doc-{number}",
    }


def _normalise_treaty_detail(raw: dict) -> dict:
    base = _normalise_treaty_summary(raw)
    base.update({
        "countries":   [c.get("name", "") for c in raw.get("countriesAffected", [])],
        "index_terms": [t.get("term", "") for t in raw.get("indexTerms", [])],
        "old_number":  raw.get("oldNumber", ""),
        "update_date": raw.get("updateDate", ""),
    })
    return base


# ---------------------------------------------------------------------------
# Nominations
# ---------------------------------------------------------------------------

def search_nominations(
    congress: int | None = None,
    query: str | None = None,
    limit: int = 20,
    offset: int = 0,
    api_key: str | None = None,
) -> dict:
    """
    List presidential nominations for a given Congress with optional keyword filter.

    Args:
        congress: Congress number (default: current)
        query:    Keyword to filter by description, organization, or position title
        limit:    Results per page
        offset:   Pagination offset

    Returns:
        {"nominations": [...], "count": int, "congress": int}
    """
    congress = congress or current_congress()
    path = f"/nomination/{congress}"
    data = _request(path, {"limit": limit, "offset": offset}, use_cache=False, api_key=api_key)
    if "error" in data:
        return data

    nominations = data.get("nominations", [])

    if query:
        q = query.lower()
        nominations = [
            n for n in nominations
            if q in (n.get("description") or "").lower()
            or q in (n.get("organization") or "").lower()
            or any(q in (pos.get("positionTitle") or "").lower() for pos in n.get("positions", []))
        ]

    return {
        "nominations": [_normalise_nomination_summary(n) for n in nominations],
        "count":       data.get("pagination", {}).get("count", len(nominations)),
        "congress":    congress,
        "query":       query,
    }


def get_nomination(congress: int, nomination_number: int) -> dict:
    """Retrieve full details for a specific presidential nomination."""
    path = f"/nomination/{congress}/{nomination_number}"
    data = _request(path)
    if "error" in data:
        return data

    return _normalise_nomination_detail(data.get("nomination", data))


def get_nomination_nominees(congress: int, nomination_number: int) -> dict:
    """Retrieve the list of nominees for a nomination."""
    path = f"/nomination/{congress}/{nomination_number}/nominees"
    data = _request(path)
    if "error" in data:
        return data

    nominees = []
    for ordinal_group in data.get("nominees", []):
        for n in ordinal_group.get("nominees", [ordinal_group]) if isinstance(ordinal_group, dict) else []:
            nominees.append({
                "name":          n.get("name", ""),
                "state":         n.get("state", ""),
                "position":      n.get("positionTitle", ""),
                "organization":  n.get("organization", ""),
                "introduced_date": n.get("introducedDate", ""),
            })

    return {"nominees": nominees, "count": len(nominees)}


def get_nomination_actions(congress: int, nomination_number: int) -> dict:
    """Retrieve the action history for a nomination."""
    path = f"/nomination/{congress}/{nomination_number}/actions"
    data = _request(path)
    if "error" in data:
        return data

    actions = data.get("actions", [])
    return {
        "actions": [
            {"date": a.get("actionDate", ""), "text": a.get("text", ""), "type": a.get("type", "")}
            for a in actions
        ],
        "count": len(actions),
    }


def _normalise_nomination_summary(raw: dict) -> dict:
    return {
        "congress":       raw.get("congress"),
        "number":         raw.get("number", raw.get("nominationNumber", "")),
        "citation":       raw.get("citation", ""),
        "description":    raw.get("description", ""),
        "organization":   raw.get("organization", ""),
        "received_date":  raw.get("receivedDate", ""),
        "status":         raw.get("latestAction", {}).get("text", ""),
        "status_date":    raw.get("latestAction", {}).get("actionDate", ""),
        "is_civilian":    raw.get("isCivilian", True),
        "part_number":    raw.get("partNumber", ""),
        "url":            raw.get("url", ""),
    }


def _normalise_nomination_detail(raw: dict) -> dict:
    base = _normalise_nomination_summary(raw)
    nominees_raw = raw.get("nominees", {})
    base.update({
        "nominees_count": nominees_raw.get("count", 0) if isinstance(nominees_raw, dict) else len(nominees_raw),
        "committees":     [c.get("name", "") for c in raw.get("committees", {}).get("item", [])],
        "positions":      raw.get("positions", []),
        "update_date":    raw.get("updateDate", ""),
    })
    return base


# ---------------------------------------------------------------------------
# Congressional Record
# ---------------------------------------------------------------------------

def search_congressional_record(
    year: int | None = None,
    month: int | None = None,
    day: int | None = None,
    limit: int = 20,
) -> dict:
    """
    Search the daily Congressional Record by date.

    Args:
        year:  Filter by year (e.g., 2025)
        month: Filter by month (1–12)
        day:   Filter by day (1–31)
        limit: Max results

    Returns:
        {"issues": [...], "count": int}
        Each issue has volume, issue number, date, congress, and section links.
    """
    params: dict = {"limit": limit}
    if year:
        params["y"] = year
    if month:
        params["m"] = month
    if day:
        params["d"] = day

    data = _request("/daily-congressional-record", params, use_cache=False)
    if "error" in data:
        return data

    issues = data.get("dailyCongressionalRecord", [])
    return {
        "issues": [
            {
                "volume":     i.get("volumeNumber"),
                "issue":      i.get("issueNumber"),
                "congress":   i.get("congress"),
                "session":    i.get("sessionNumber"),
                "issue_date": i.get("issueDate", ""),
                "url":        i.get("url", ""),
                "sections":   list(i.get("fullIssue", {}).keys()),
            }
            for i in issues
        ],
        "count": data.get("pagination", {}).get("count", len(issues)),
    }


def get_congressional_record_articles(volume: int, issue: int) -> dict:
    """
    Get all articles/items from a specific Congressional Record issue.

    Args:
        volume: Congressional Record volume number
        issue:  Issue number within the volume

    Returns:
        {"articles": [...], "volume": int, "issue": int}
        Each article has title, section (House/Senate/Extensions), page range, and URL.
    """
    path = f"/daily-congressional-record/{volume}/{issue}/articles"
    data = _request(path)
    if "error" in data:
        return data

    articles_raw = data.get("articles", {})
    all_articles = []

    # Response is a dict keyed by section name (e.g. "senateSection", "houseSection")
    for section_name, section_items in articles_raw.items():
        if not isinstance(section_items, list):
            continue
        for a in section_items:
            pdf_url  = next((f["url"] for f in a.get("formats", []) if "pdf" in (f.get("type") or "").lower()), "")
            text_url = next((f["url"] for f in a.get("formats", []) if "htm" in (f.get("url") or "").lower()), "")
            all_articles.append({
                "title":      a.get("title", ""),
                "section":    section_name.replace("Section", "").replace("section", "").strip(),
                "start_page": a.get("startPage", ""),
                "end_page":   a.get("endPage", ""),
                "url":        text_url or pdf_url,
                "pdf_url":    pdf_url,
            })

    return {"articles": all_articles, "volume": volume, "issue": issue, "count": len(all_articles)}


# ---------------------------------------------------------------------------
# CRS Reports
# ---------------------------------------------------------------------------
# NOTE: The Congress.gov API v3 does not expose a standalone /crsReport endpoint.
# CRS reports can be discovered via:
#   1. Bill summaries (/bill/{congress}/{type}/{number}/summaries) — CRS writes these
#   2. everycrsreport.com — third-party mirror with full text and search
#   3. The official CRS website at crsreports.congress.gov (no public API)
# The functions below search summaries as the practical proxy for CRS content.

def search_crs_reports(
    query: str | None = None,
    limit: int = 20,
    offset: int = 0,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    """
    Search for CRS-authored bill summaries via the /summaries endpoint.

    CRS (Congressional Research Service) writes nonpartisan summaries for most
    major federal bills. This is the closest available proxy via Congress.gov API.

    Args:
        query:     Keyword to filter summary text (client-side)
        limit:     Results per page
        offset:    Pagination offset
        from_date: Start date for summaries in "YYYY-MM-DD" format (e.g. "2010-01-01")
        to_date:   End date for summaries in "YYYY-MM-DD" format (e.g. "2020-12-31")

    Returns:
        {"reports": [...], "count": int, "note": str}
        Each entry has bill info, CRS summary text, and a link.
        Also includes a reference to everycrsreport.com for standalone reports.
    """
    params: dict = {"limit": limit, "offset": offset}
    if from_date:
        dt = from_date.strip()
        params["fromDateTime"] = f"{dt}T00:00:00Z" if "T" not in dt else dt
    if to_date:
        dt = to_date.strip()
        params["toDateTime"] = f"{dt}T23:59:59Z" if "T" not in dt else dt
    data = _request("/summaries", params, use_cache=False)
    if "error" in data:
        return data

    summaries = data.get("summaries", [])

    if query:
        q = query.lower()
        summaries = [
            s for s in summaries
            if q in (s.get("text") or "").lower()
            or q in (s.get("bill", {}).get("title") or "").lower()
        ]

    reports = []
    for s in summaries:
        bill = s.get("bill", {})
        bt   = (bill.get("type") or "").lower()
        reports.append({
            "bill_label":   f"{BILL_TYPE_LABEL.get(bt, bt.upper())} {bill.get('number', '')}",
            "congress":     bill.get("congress"),
            "bill_type":    bt,
            "bill_number":  bill.get("number"),
            "title":        bill.get("title", ""),
            "summary_date": s.get("actionDate", ""),
            "summary_type": s.get("actionDesc", ""),
            "summary_text": _strip_html(s.get("text", ""))[:500] + "…",
            "url":          bill.get("url", ""),
        })

    return {
        "reports": reports,
        "count":   data.get("pagination", {}).get("count", len(reports)),
        "query":   query,
        "note":    "For standalone CRS reports (R-series, IF-series, etc.) see https://crsreports.congress.gov or https://everycrsreport.com",
    }


def get_crs_report(report_number: str) -> dict:
    """
    Return a direct link to a CRS report by number (e.g., "R40000", "IF10244").

    The Congress.gov API v3 does not host CRS reports directly.
    This function returns the correct URL to retrieve it from crsreports.congress.gov.
    """
    return {
        "report_number": report_number,
        "url":           f"https://crsreports.congress.gov/product/pdf/{report_number[:1]}/{report_number}",
        "search_url":    f"https://crsreports.congress.gov/search/#/?terms={report_number}",
        "note":          "CRS reports are not in the Congress.gov API v3. Use crsreports.congress.gov directly.",
    }


# ---------------------------------------------------------------------------
# House & Senate Communications
# ---------------------------------------------------------------------------

HOUSE_COMM_TYPES = {
    "ec":  "Executive Communication",
    "ml":  "Mail",
    "pm":  "Presidential Message",
    "pt":  "Petition or Memorial",
}

SENATE_COMM_TYPES = {
    "ec":  "Executive Communication",
    "pm":  "Presidential Message",
    "pom": "Petition or Memorial",
}


def search_house_communications(
    congress: int | None = None,
    comm_type: str = "ec",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    Search House communications (executive communications, presidential messages, etc.).

    Args:
        congress:  Congress number (default: current)
        comm_type: "ec" (Executive Communication), "ml" (Mail), "pm" (Presidential Message), "pt" (Petition)
        limit:     Results per page
        offset:    Pagination offset
    """
    congress = congress or current_congress()
    ct = comm_type.lower()
    if ct not in HOUSE_COMM_TYPES:
        return {"error": f"Unknown House communication type: '{comm_type}'. Use: {', '.join(HOUSE_COMM_TYPES)}"}

    path = f"/house-communication/{congress}/{ct}"
    data = _request(path, {"limit": limit, "offset": offset}, use_cache=False)
    if "error" in data:
        return data

    comms = data.get("houseCommunications", [])
    return {
        "communications": [_normalise_communication(c, "House") for c in comms],
        "type":           HOUSE_COMM_TYPES[ct],
        "count":          data.get("pagination", {}).get("count", len(comms)),
        "congress":       congress,
    }


def get_house_communication(congress: int, comm_type: str, number: int) -> dict:
    """Retrieve a specific House communication."""
    ct = comm_type.lower()
    if ct not in HOUSE_COMM_TYPES:
        return {"error": f"Unknown House communication type: '{comm_type}'"}

    path = f"/house-communication/{congress}/{ct}/{number}"
    data = _request(path)
    if "error" in data:
        return data

    return _normalise_communication(data.get("houseCommunication", data), "House")


def search_senate_communications(
    congress: int | None = None,
    comm_type: str = "ec",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    Search Senate communications.

    Args:
        congress:  Congress number (default: current)
        comm_type: "ec" (Executive Communication), "pm" (Presidential Message), "pom" (Petition or Memorial)
        limit:     Results per page
        offset:    Pagination offset
    """
    congress = congress or current_congress()
    ct = comm_type.lower()
    if ct not in SENATE_COMM_TYPES:
        return {"error": f"Unknown Senate communication type: '{comm_type}'. Use: {', '.join(SENATE_COMM_TYPES)}"}

    path = f"/senate-communication/{congress}/{ct}"
    data = _request(path, {"limit": limit, "offset": offset}, use_cache=False)
    if "error" in data:
        return data

    comms = data.get("senateCommunications", [])
    return {
        "communications": [_normalise_communication(c, "Senate") for c in comms],
        "type":           SENATE_COMM_TYPES[ct],
        "count":          data.get("pagination", {}).get("count", len(comms)),
        "congress":       congress,
    }


def get_senate_communication(congress: int, comm_type: str, number: int) -> dict:
    """Retrieve a specific Senate communication."""
    ct = comm_type.lower()
    if ct not in SENATE_COMM_TYPES:
        return {"error": f"Unknown Senate communication type: '{comm_type}'"}

    path = f"/senate-communication/{congress}/{ct}/{number}"
    data = _request(path)
    if "error" in data:
        return data

    return _normalise_communication(data.get("senateCommunication", data), "Senate")


def _normalise_communication(raw: dict, chamber: str) -> dict:
    comm_type = raw.get("communicationType", raw.get("type", {}))
    type_name = comm_type.get("name", "") if isinstance(comm_type, dict) else str(comm_type)
    type_code = comm_type.get("code", "").lower() if isinstance(comm_type, dict) else ""
    return {
        "congress":            raw.get("congress"),
        "number":              raw.get("number"),
        "type":                type_name,
        "type_code":           type_code,
        "chamber":             chamber,
        "referral_date":       raw.get("referralDate", ""),
        "abstract":            raw.get("abstract", ""),
        "submitting_agency":   raw.get("submittingAgency", ""),
        "submitting_official": raw.get("submittingOfficial", ""),
        "report_nature":       raw.get("reportNature", ""),
        "legal_authority":     raw.get("legalAuthority", ""),
        "committees":          [c.get("name", "") for c in raw.get("committees", [])],
        "url":                 raw.get("url", ""),
    }


# ---------------------------------------------------------------------------
# House Roll Call Votes  (BETA — 118th Congress / 2023 onward)
# ---------------------------------------------------------------------------
# Path:    /house-vote  (list) | /house-vote/{congress}/{session}/{rollCallNumber} (detail)
# Note:    Individual member votes are NOT in the API response. They are available
#          via the Clerk's XML at the sourceDataURL field. Use get_house_vote_members()
#          to fetch and parse those.

def search_house_votes(
    congress: int | None = None,
    session: int = 1,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    List House roll call votes.

    Note: BETA endpoint — covers 118th Congress (2023) onward.

    Args:
        congress: Congress number (default: current)
        session:  Session number — 1 (odd year) or 2 (even year)
        limit:    Results per page (max 250)
        offset:   Pagination offset

    Returns:
        {"votes": [...], "count": int, "congress": int, "session": int}
    """
    congress = congress or current_congress()
    params: dict = {"limit": limit, "offset": offset}
    if congress or session:
        params["congress"] = congress
        params["session"]  = session

    data = _request("/house-vote", params, use_cache=False)
    if "error" in data:
        return data

    votes_raw = data.get("houseRollCallVotes", [])
    return {
        "votes":    [_normalise_roll_call_summary(v) for v in votes_raw],
        "count":    data.get("pagination", {}).get("count", len(votes_raw)),
        "congress": congress,
        "session":  session,
    }


def get_house_vote(congress: int, session: int, roll_call_number: int) -> dict:
    """
    Retrieve a specific House roll call vote with party-level totals.

    Note: BETA endpoint — covers 118th Congress (2023) onward.
    Member-level votes require a separate call to get_house_vote_members().

    Returns:
        {
            "roll_call":     int,
            "congress":      int,
            "session":       int,
            "chamber":       "House",
            "date":          str,
            "question":      str,
            "vote_type":     str,
            "legislation":   str,   # e.g. "HR 3424"
            "result":        str,
            "party_totals":  [{"party": str, "yea": int, "nay": int, "not_voting": int}, ...],
            "source_data_url": str, # Clerk XML — use get_house_vote_members() to parse
            "url":           str,
        }
    """
    path = f"/house-vote/{congress}/{session}/{roll_call_number}"
    data = _request(path)
    if "error" in data:
        return data

    v = data.get("houseRollCallVote", data)

    party_totals = [
        {
            "party":      pt.get("voteParty", ""),
            "party_name": pt.get("party", {}).get("name", ""),
            "yea":        pt.get("yeaTotal", 0),
            "nay":        pt.get("nayTotal", 0),
            "present":    pt.get("presentTotal", 0),
            "not_voting": pt.get("notVotingTotal", 0),
        }
        for pt in v.get("votePartyTotal", [])
    ]

    leg_type   = (v.get("legislationType") or "").upper()
    leg_number = v.get("legislationNumber", "")
    leg_label  = f"{BILL_TYPE_LABEL.get(leg_type.lower(), leg_type)} {leg_number}".strip()

    return {
        "roll_call":       roll_call_number,
        "congress":        congress,
        "session":         session,
        "chamber":         "House",
        "date":            v.get("startDate", ""),
        "question":        v.get("voteQuestion", ""),
        "vote_type":       v.get("voteType", ""),
        "legislation":     leg_label,
        "legislation_url": v.get("legislationUrl", ""),
        "result":          v.get("result", ""),
        "party_totals":    party_totals,
        "source_data_url": v.get("sourceDataURL", ""),
        "url":             v.get("url", f"https://api.congress.gov/v3/house-vote/{congress}/{session}/{roll_call_number}"),
    }


def get_house_vote_members(congress: int, session: int, roll_call_number: int) -> dict:
    """
    Retrieve individual member votes for a House roll call by parsing the Clerk's XML.

    Fetches the sourceDataURL from the vote record, then downloads and parses
    the House Clerk's XML to extract member-level vote positions.

    Returns:
        {
            "roll_call": int,
            "member_votes": [{"name", "bioguide_id", "party", "state", "district", "vote"}, ...],
            "count": int,
        }
        or {"error": str}
    """
    # First get the vote to find the sourceDataURL
    vote = get_house_vote(congress, session, roll_call_number)
    if "error" in vote:
        return vote

    xml_url = vote.get("source_data_url", "")
    if not xml_url:
        return {"error": "No source XML URL available for this vote"}

    try:
        import xml.etree.ElementTree as ET
        resp = requests.get(xml_url, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as e:
        return {"error": f"Could not fetch or parse Clerk XML: {e}"}

    member_votes = []
    for voter in root.iter("recorded-vote"):
        legislator = voter.find("legislator")
        vote_elem  = voter.find("vote")
        if legislator is None or vote_elem is None:
            continue
        member_votes.append({
            "name":        legislator.text or "",
            "bioguide_id": legislator.get("name-id", ""),
            "party":       legislator.get("party", ""),
            "state":       legislator.get("state", ""),
            "district":    legislator.get("district", ""),
            "vote":        vote_elem.text or "",
        })

    return {
        "roll_call":    roll_call_number,
        "congress":     congress,
        "session":      session,
        "member_votes": member_votes,
        "count":        len(member_votes),
        "xml_url":      xml_url,
    }


def _normalise_roll_call_summary(raw: dict) -> dict:
    leg_type   = (raw.get("legislationType") or "").lower()
    leg_number = raw.get("legislationNumber", "")
    leg_label  = f"{BILL_TYPE_LABEL.get(leg_type, leg_type.upper())} {leg_number}".strip()
    return {
        "roll_call":   raw.get("rollCallNumber", ""),
        "session":     raw.get("sessionNumber", ""),
        "congress":    raw.get("congress", ""),
        "date":        raw.get("startDate", ""),
        "question":    raw.get("voteQuestion", ""),
        "vote_type":   raw.get("voteType", ""),
        "legislation": leg_label,
        "result":      raw.get("result", ""),
        "url":         raw.get("url", ""),
    }


# ---------------------------------------------------------------------------
# Committee Reports
# ---------------------------------------------------------------------------

COMMITTEE_REPORT_TYPES = {
    "hrpt": "House Report",
    "srpt": "Senate Report",
    "erpt": "Executive Report",
}


def search_committee_reports(
    congress: int | None = None,
    report_type: str = "hrpt",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    List committee reports for a given congress and type.

    Args:
        congress:    Congress number (default: current)
        report_type: "hrpt" (House), "srpt" (Senate), or "erpt" (Executive)
        limit:       Results per page
        offset:      Pagination offset
    """
    congress = congress or current_congress()
    rt = report_type.lower()
    if rt not in COMMITTEE_REPORT_TYPES:
        return {"error": f"Unknown report type: '{report_type}'. Use: {', '.join(COMMITTEE_REPORT_TYPES)}"}

    path = f"/committee-report/{congress}/{rt}"
    data = _request(path, {"limit": limit, "offset": offset}, use_cache=False)
    if "error" in data:
        return data

    reports = data.get("reports", [])
    return {
        "reports":    [_normalise_committee_report(r) for r in reports],
        "type_label": COMMITTEE_REPORT_TYPES[rt],
        "count":      data.get("pagination", {}).get("count", len(reports)),
        "congress":   congress,
    }


def get_committee_report(congress: int, report_type: str, report_number: int) -> dict:
    """
    Retrieve a specific committee report, including text links if available.

    Args:
        congress:      Congress number
        report_type:   "hrpt", "srpt", or "erpt"
        report_number: Report number
    """
    rt = report_type.lower()
    if rt not in COMMITTEE_REPORT_TYPES:
        return {"error": f"Unknown report type: '{report_type}'"}

    path = f"/committee-report/{congress}/{rt}/{report_number}"
    data = _request(path)
    if "error" in data:
        return data

    result = _normalise_committee_report(data.get("committeeReport", data))

    # Attempt to fetch text versions
    text_data = _request(f"{path}/text")
    if "error" not in text_data:
        text_versions = text_data.get("text", [])
        if text_versions:
            result["text_versions"] = text_versions
            for version in text_versions:
                for fmt in version.get("formats", []):
                    if "formatted" in (fmt.get("type") or "").lower():
                        result["text_url"] = fmt.get("url", "")
                        break

    return result


def _normalise_committee_report(raw: dict) -> dict:
    congress = raw.get("congress")
    number   = raw.get("number")
    rt       = (raw.get("type") or "").lower()
    return {
        "congress":         congress,
        "number":           number,
        "type":             raw.get("type", ""),
        "type_label":       COMMITTEE_REPORT_TYPES.get(rt, raw.get("type", "")),
        "citation":         raw.get("citation", ""),
        "title":            raw.get("title", ""),
        "issued_date":      raw.get("issueDate", ""),
        "is_conference":    raw.get("isConferenceReport", False),
        "committees":       [c.get("name", "") for c in raw.get("committees", [])],
        "associated_bills": [f"{b.get('type', '')} {b.get('number', '')}" for b in raw.get("associatedBill", [])],
        "url":              raw.get("url", ""),
        "congress_url":     f"https://www.congress.gov/congressional-report/{congress}th-congress/{rt}/{number}",
    }


# ---------------------------------------------------------------------------
# Hearings
# ---------------------------------------------------------------------------

def search_hearings(
    congress: int | None = None,
    chamber: str = "house",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    List committee hearings for a congress and chamber.

    Args:
        congress: Congress number (default: current)
        chamber:  "house", "senate", or "nochamber"
        limit:    Results per page
        offset:   Pagination offset
    """
    congress = congress or current_congress()
    ch = chamber.lower()
    if ch not in {"house", "senate", "nochamber"}:
        return {"error": "Chamber must be 'house', 'senate', or 'nochamber'"}

    path = f"/hearing/{congress}/{ch}"
    data = _request(path, {"limit": limit, "offset": offset}, use_cache=False)
    if "error" in data:
        return data

    hearings = data.get("hearings", [])
    return {
        "hearings": [_normalise_hearing(h) for h in hearings],
        "count":    data.get("pagination", {}).get("count", len(hearings)),
        "congress": congress,
        "chamber":  chamber,
    }


def _normalise_hearing(raw: dict) -> dict:
    meetings = raw.get("hearingMeetings", [])
    location = meetings[0].get("roomNumber", "") if meetings else ""
    return {
        "congress":         raw.get("congress"),
        "chamber":          raw.get("chamber", ""),
        "number":           raw.get("number", ""),
        "date":             raw.get("date", ""),
        "title":            raw.get("title", ""),
        "location":         location,
        "committees":       [c.get("name", "") for c in raw.get("committees", [])],
        "associated_bills": [f"{b.get('type', '')} {b.get('number', '')}" for b in raw.get("associatedBill", [])],
        "jacket_number":    raw.get("jacketNumber", ""),
        "url":              raw.get("url", ""),
    }


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

def search_members(name: str | None = None, state: str | None = None, limit: int = 20) -> dict:
    """
    Search for current Congress members by name and/or state.

    Args:
        name:  Full or partial name (e.g., "Sanders", "Elizabeth Warren")
        state: Two-letter state code (e.g., "VT", "MA")
        limit: Max results

    Returns:
        {"members": [...], "count": int}
    """
    params: dict = {"limit": limit, "currentMember": "true"}
    if name:
        params["name"] = name
    if state:
        params["stateCode"] = state.upper()

    data = _request("/member", params, use_cache=False)
    if "error" in data:
        return data

    members = data.get("members", [])
    return {
        "members": [_normalise_member_summary(m) for m in members],
        "count":   data.get("pagination", {}).get("count", len(members)),
    }


def get_members_by_congress(
    congress: int | None = None,
    chamber: str | None = None,
    limit: int = 250,
    offset: int = 0,
    api_key: str | None = None,
) -> dict:
    """
    Get all members of a specific Congress, optionally filtered by chamber.

    Args:
        congress: Congress number (default: current)
        chamber:  "House" or "Senate" (optional — returns both if omitted)
        limit:    Results per page (up to 250)
        offset:   Pagination offset

    Returns:
        {"members": [...], "count": int, "congress": int}
    """
    congress = congress or current_congress()

    if chamber:
        ch = chamber.lower()
        if ch not in {"house", "senate"}:
            return {"error": "Chamber must be 'House' or 'Senate'"}
        path = f"/member/congress/{congress}/{ch}"
    else:
        path = f"/member/congress/{congress}"

    data = _request(path, {"limit": limit, "offset": offset}, api_key=api_key)
    if "error" in data:
        return data

    members = data.get("members", [])
    return {
        "members": [_normalise_member_summary(m) for m in members],
        "count":   data.get("pagination", {}).get("count", len(members)),
        "congress": congress,
        "chamber":  chamber,
    }


def _normalise_member_summary(raw: dict) -> dict:
    terms = raw.get("terms", [])
    latest_term = terms[-1] if isinstance(terms, list) and terms else {}
    return {
        "name":        raw.get("name", ""),
        "bioguide_id": raw.get("bioguideId", ""),
        "party":       raw.get("partyName", ""),
        "state":       raw.get("state", ""),
        "district":    raw.get("district", latest_term.get("district", "")),
        "chamber":     latest_term.get("chamber", ""),
        "url":         raw.get("url", ""),
    }


def get_member(bioguide_id: str) -> dict:
    """
    Retrieve full profile for a Congress member by their Bioguide ID.

    Returns name, party, state, district, chamber, contact info, and term history.
    """
    path = f"/member/{bioguide_id}"
    data = _request(path)
    if "error" in data:
        return data

    m = data.get("member", data)
    terms = m.get("terms", {}).get("item", []) if isinstance(m.get("terms"), dict) else m.get("terms", [])
    latest_term = terms[-1] if terms else {}

    return {
        "name":           m.get("directOrderName", m.get("invertedOrderName", "")),
        "bioguide_id":    bioguide_id,
        "birth_year":     m.get("birthYear", ""),
        "party":          m.get("partyName", ""),
        "state":          m.get("state", ""),
        "district":       latest_term.get("district", ""),
        "chamber":        latest_term.get("chamber", ""),
        "office_address": m.get("addressInformation", {}).get("officeAddress", ""),
        "phone":          m.get("addressInformation", {}).get("phoneNumber", ""),
        "website":        m.get("officialWebsiteUrl", ""),
        "depiction_url":  m.get("depiction", {}).get("imageUrl", ""),
        "terms":          terms,
    }


def get_member_votes(bioguide_id: str, limit: int = 100, offset: int = 0) -> dict:
    """
    Retrieve recent votes cast by a Congress member.

    Returns each vote with date, chamber, roll call number, question, their vote, and the result.
    """
    path = f"/member/{bioguide_id}/votes"
    data = _request(path, {"limit": limit, "offset": offset}, use_cache=False)
    if "error" in data:
        return data

    votes = data.get("votes", [])
    return {
        "votes": [
            {
                "congress":    v.get("congress", ""),
                "session":     v.get("sessionNumber", ""),
                "chamber":     v.get("chamber", ""),
                "roll_call":   v.get("rollNumber", ""),
                "date":        v.get("voteDate", ""),
                "question":    v.get("voteQuestion", ""),
                "description": v.get("description", ""),
                "member_vote": v.get("memberVote", ""),
                "result":      v.get("voteResult", ""),
            }
            for v in votes
        ],
        "count":       data.get("pagination", {}).get("count", len(votes)),
        "bioguide_id": bioguide_id,
    }


def get_member_sponsored(bioguide_id: str, limit: int = 50) -> dict:
    """Retrieve legislation sponsored by a Congress member."""
    path = f"/member/{bioguide_id}/sponsored-legislation"
    data = _request(path, {"limit": limit})
    if "error" in data:
        return data

    bills = data.get("sponsoredLegislation", [])
    return {
        "bills": [_normalise_bill_summary(b) for b in bills],
        "count": data.get("pagination", {}).get("count", len(bills)),
    }


def get_member_cosponsored(bioguide_id: str, limit: int = 50) -> dict:
    """Retrieve legislation cosponsored by a Congress member."""
    path = f"/member/{bioguide_id}/cosponsored-legislation"
    data = _request(path, {"limit": limit})
    if "error" in data:
        return data

    bills = data.get("cosponsoredLegislation", [])
    return {
        "bills": [_normalise_bill_summary(b) for b in bills],
        "count": data.get("pagination", {}).get("count", len(bills)),
    }


# ---------------------------------------------------------------------------
# Historical range search helpers
# ---------------------------------------------------------------------------
# Historical data availability (Congress.gov API v3):
#   Nominations  : ~100th Congress (1987) onward
#   Treaties     : ~90th Congress (1967) onward
#   Summaries    : support fromDateTime / toDateTime filters (confirmed)
#   Daily CR     : year filter is ignored by the API (same result regardless of y=)


def search_nominations_range(
    query: str | None = None,
    from_congress: int = 100,
    to_congress: int | None = None,
    limit_per_congress: int = 250,
) -> dict:
    """
    Search presidential nominations across a range of Congresses with keyword filtering.

    Historical data is available from approximately the 100th Congress (1987) onward.

    Args:
        query:              Keyword to filter by description, organization, or position title
        from_congress:      Starting Congress number (default: 100)
        to_congress:        Ending Congress number (default: current)
        limit_per_congress: Max nominations fetched per Congress (up to 250)

    Returns:
        {"nominations": [...], "total_found": int, "congresses_searched": [int, ...],
         "query": str, "from_congress": int, "to_congress": int}
    """
    to_congress = to_congress or current_congress()
    from_congress = max(100, from_congress)  # reliable data starts ~100th Congress

    all_nominations: list[dict] = []
    congresses_searched: list[int] = []

    for cn in range(from_congress, to_congress + 1):
        result = _request(f"/nomination/{cn}", {"limit": limit_per_congress, "offset": 0}, use_cache=False)
        if "error" in result:
            continue
        noms = result.get("nominations", [])
        if query:
            q = query.lower()
            noms = [
                n for n in noms
                if q in (n.get("description") or "").lower()
                or q in (n.get("organization") or "").lower()
                or q in (n.get("citation") or "").lower()
                or any(q in (pos.get("positionTitle") or "").lower() for pos in n.get("positions", []))
            ]
        for n in noms:
            all_nominations.append(_normalise_nomination_summary(n))
        congresses_searched.append(cn)

    all_nominations.sort(key=lambda n: n.get("received_date", ""), reverse=True)

    return {
        "nominations":         all_nominations,
        "total_found":         len(all_nominations),
        "congresses_searched": congresses_searched,
        "query":               query,
        "from_congress":       from_congress,
        "to_congress":         to_congress,
        "note":                "Max 250 nominations fetched per Congress. Bulk military promotions counted as single entries.",
    }


def search_treaties_range(
    query: str | None = None,
    from_congress: int = 90,
    to_congress: int | None = None,
    limit_per_congress: int = 250,
) -> dict:
    """
    Search treaties across a range of Congresses with keyword filtering.

    Historical data is available from approximately the 90th Congress (1967) onward.

    Args:
        query:              Keyword to filter by topic or country (client-side)
        from_congress:      Starting Congress number (default: 90)
        to_congress:        Ending Congress number (default: current)
        limit_per_congress: Max treaties fetched per Congress (up to 250)

    Returns:
        {"treaties": [...], "total_found": int, "congresses_searched": [int, ...],
         "query": str, "from_congress": int, "to_congress": int}
    """
    to_congress = to_congress or current_congress()
    from_congress = max(90, from_congress)  # reliable data starts ~90th Congress

    all_treaties: list[dict] = []
    congresses_searched: list[int] = []

    for cn in range(from_congress, to_congress + 1):
        result = _request(f"/treaty/{cn}", {"limit": limit_per_congress, "offset": 0}, use_cache=False)
        if "error" in result:
            continue
        treaties = [_normalise_treaty_summary(t) for t in result.get("treaties", [])]
        if query:
            q = query.lower()
            treaties = [
                t for t in treaties
                if q in (t.get("topic") or "").lower()
                or q in (t.get("status") or "").lower()
            ]
        all_treaties.extend(treaties)
        congresses_searched.append(cn)

    all_treaties.sort(key=lambda t: t.get("transmitted_date", ""), reverse=True)

    return {
        "treaties":            all_treaties,
        "total_found":         len(all_treaties),
        "congresses_searched": congresses_searched,
        "query":               query,
        "from_congress":       from_congress,
        "to_congress":         to_congress,
    }


def search_congressional_record_by_keyword(
    keyword: str,
    year: int | None = None,
    month: int | None = None,
    max_issues: int = 10,
) -> dict:
    """
    Search Congressional Record articles by keyword in article titles.

    Fetches recent issues (or issues near a given month/year) and scans article
    titles for the keyword. The year filter in the Congress.gov API is unreliable
    (appears to be ignored), so this works best for recent or month-scoped searches.

    Args:
        keyword:    Topic to search for in article titles
        year:       Optional year hint (passed to API)
        month:      Optional month to narrow the issue list
        max_issues: Number of CR issues to scan (each issue = one day in session)

    Returns:
        {"matches": [...], "issues_scanned": int, "total_matches": int, "keyword": str}
        Each match has: title, section, start_page, end_page, url, issue_date, volume, issue.
    """
    issues_result = search_congressional_record(year=year, month=month, limit=max_issues)
    if "error" in issues_result:
        return issues_result

    issues = issues_result.get("issues", [])
    matches: list[dict] = []
    kw = keyword.lower()

    for issue in issues:
        vol = issue.get("volume")
        iss = issue.get("issue")
        if not vol or not iss:
            continue
        articles_result = get_congressional_record_articles(vol, iss)
        if "error" in articles_result:
            continue
        for article in articles_result.get("articles", []):
            if kw in (article.get("title") or "").lower():
                matches.append({
                    **article,
                    "issue_date": issue.get("issue_date", ""),
                    "volume":     vol,
                    "issue_num":  iss,
                    "congress":   issue.get("congress"),
                })

    return {
        "matches":       matches,
        "issues_scanned": len(issues),
        "total_matches": len(matches),
        "keyword":       keyword,
        "note":          "API year filter is unreliable; use month+year for best date scoping.",
    }


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def format_date(d: str) -> str:
    """Convert 'YYYY-MM-DD' to 'Month D, YYYY'."""
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%B %-d, %Y")
    except Exception:
        try:
            return datetime.strptime(d, "%Y-%m-%d").strftime("%B %d, %Y")
        except Exception:
            return d


def bill_url(congress: int, bill_type: str, bill_number: int) -> str:
    """Return the Congress.gov canonical URL for a bill."""
    bt = _normalise_type(str(bill_type)) or bill_type.lower()
    return f"https://www.congress.gov/bill/{congress}th-congress/{_chamber_path(bt)}/{bill_number}"


# ---------------------------------------------------------------------------
# Self-test (run directly to verify your API key works)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=== Congress.gov API Client - Self-Test ===\n")

    if not API_KEY:
        print("ERROR: CONGRESS_API_KEY is not set.")
        print("Get a free key at https://api.congress.gov/sign-up/")
        sys.exit(1)

    cn = current_congress()
    print(f"Current Congress: {cn}th\n")

    # Bill identifier parsing
    tests = ["HR 1", "S. 100", "H.J.Res. 7", "119-HR 1234", "SRes 50"]
    print("--- Bill identifier parsing ---")
    for t in tests:
        print(f"  '{t}' -> {parse_bill_identifier(t)}")

    # Bills
    print(f"\n--- Bills: HR 1 / {cn}th Congress ---")
    bill = get_bill(cn, "hr", 1)
    if "error" in bill:
        print(f"  ERROR: {bill['error']}")
    else:
        print(f"  {bill['bill_label']}: {bill['title'][:70]}")
        print(f"  Status: {bill['status']}")
        print(f"  Sponsor: {bill['primary_sponsor'].get('name')} ({bill['primary_sponsor'].get('party')})")

    # Nominations
    print(f"\n--- Nominations ({cn}th Congress) ---")
    noms = search_nominations(cn, limit=3)
    if "error" in noms:
        print(f"  ERROR: {noms['error']}")
    else:
        print(f"  Total available: {noms['count']}")
        for n in noms["nominations"][:2]:
            print(f"  [{n['number']}] {n['description'][:70]}")

    # Treaties
    print(f"\n--- Treaties ({cn}th Congress) ---")
    treats = search_treaties(cn, limit=3)
    if "error" in treats:
        print(f"  ERROR: {treats['error']}")
    else:
        print(f"  Total available: {treats['count']}")
        for t in treats["treaties"][:2]:
            print(f"  Treaty {t['number']}: {t['topic'][:60]}")

    # CRS Reports (via bill summaries proxy)
    print("\n--- CRS Reports (via /summaries — latest 3) ---")
    reports = search_crs_reports(limit=3)
    if "error" in reports:
        print(f"  ERROR: {reports['error']}")
    else:
        print(f"  Note: {reports.get('note', '')[:80]}")
        for r in reports["reports"][:2]:
            print(f"  {r['bill_label']}: {r['title'][:65]}")

    # House Roll Call Votes (BETA — path: /house-vote)
    print(f"\n--- House Roll Call Votes (BETA, {cn}th Congress) ---")
    hv = search_house_votes(cn, session=1, limit=3)
    if "error" in hv:
        print(f"  ERROR: {hv['error']}")
    else:
        print(f"  Total available: {hv['count']}")
        for v in hv["votes"][:2]:
            print(f"  Roll #{v['roll_call']}: {v['legislation']} {v['question'][:40]} -> {v['result']}")

    # House vote detail with party breakdown
    if hv.get("votes"):
        first = hv["votes"][0]
        rc = first.get("roll_call")
        sess = first.get("session", 1)
        vdetail = get_house_vote(cn, sess, rc)
        if "error" not in vdetail:
            print(f"\n  Detail for Roll #{rc}:")
            for pt in vdetail.get("party_totals", []):
                print(f"    {pt['party']}: Yea={pt['yea']} Nay={pt['nay']} NV={pt['not_voting']}")

    # Member lookup
    print("\n--- Member: Bernie Sanders (S000033) ---")
    member = get_member("S000033")
    if "error" in member:
        print(f"  ERROR: {member['error']}")
    else:
        print(f"  {member['name']} ({member['party']}-{member['state']}) | {member['chamber']}")

    print("\nSelf-test complete.")
