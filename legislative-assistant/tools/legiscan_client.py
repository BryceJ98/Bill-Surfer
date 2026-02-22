"""
legiscan_client.py
------------------
Shared LegiScan API client used by legiscan test.py, policy_advisor_mcp.py,
and all Claude Code skills.

Covers every operation needed for senior policy analysis:
  - search / getSearch
  - getBill
  - getBillText      ← fetches + decodes actual statutory language
  - getRollCall      ← individual member votes
  - getSponsor       ← legislator's full bill history
  - getSessionList   ← available sessions per state
  - getMasterList    ← all bills in a session
  - getPerson        ← legislator profile

Monitoring & change detection:
  - getMonitorList    ← full details of monitored bills (GAITS)
  - getMonitorListRaw ← lightweight list with change_hash for detection
  - setMonitor        ← add/remove/update bills on monitor list
  - check_monitor_changes ← compare current vs stored hashes

Personal docket (local tracking with automatic monitoring):
  - docket_add        ← add bill with stance, priority, notes, tags
  - docket_remove     ← remove bill from docket
  - docket_update     ← update stance, priority, notes, tags
  - docket_list       ← list all docket bills with optional filters
  - docket_report     ← full status report with change detection
  - docket_get        ← get single bill with current status

Caching: responses are cached in ~/.legiscan_cache/ by a hash of the request
params so repeated lookups don't burn API quota. Monitor hashes are stored
separately in ~/.legiscan_cache/monitor_hashes.json for change detection.
Personal docket is stored in ~/.legiscan_cache/personal_docket.json.
"""

import io
import os
import json
import base64
import hashlib
import requests
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY  = os.getenv("LEGISCAN_API_KEY")
BASE_URL = "https://api.legiscan.com/"
CACHE_DIR = Path.home() / ".legiscan_cache"

STATUS_MAP = {
    1: "Introduced",
    2: "Engrossed",
    3: "Enrolled",
    4: "Passed",
    5: "Vetoed",
    6: "Failed/Dead",
    7: "Override",
    8: "Chaptered",
    9: "Refer",
    10: "Report Pass",
    11: "Report DNP",
    12: "Draft",
}

# Operations where caching is safe (deterministic, historical data)
CACHEABLE_OPS = {
    "getBill", "getBillText", "getRollCall",
    "getSponsor", "getPerson", "getSessionList",
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _cache_path(params: dict) -> Path:
    key = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"


def _load_cache(params: dict):
    path = _cache_path(params)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return None


def _save_cache(params: dict, data: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _cache_path(params).write_text(json.dumps(data))
    except Exception:
        pass


def _request(params: dict, use_cache: bool = True) -> dict:
    """Core request method with optional caching."""
    if not API_KEY:
        return {"error": "LEGISCAN_API_KEY environment variable is not set"}

    full_params = {**params, "key": API_KEY}
    op = params.get("op", "")

    # Check cache for safe ops
    if use_cache and op in CACHEABLE_OPS:
        cached = _load_cache(full_params)
        if cached is not None:
            return cached

    try:
        response = requests.get(BASE_URL, params=full_params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Network error: could not connect to LegiScan API"}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {e}"}

    if use_cache and op in CACHEABLE_OPS and data.get("status") == "OK":
        _save_cache(full_params, data)

    return data


# ── Public API functions ───────────────────────────────────────────────────────

def search_bills(query: str, state: str = "ALL", year: int = 2) -> dict:
    """
    Search bills by keyword.
    year: 1=all, 2=current session, 3=recent, 4=prior
    Returns dict with 'summary' and 'bills' list (up to 50).
    """
    data = _request({"op": "getSearch", "state": state, "query": query, "year": year},
                    use_cache=False)
    if "error" in data:
        return data
    results = data.get("searchresult", {})
    bills = [v for k, v in results.items() if k != "summary"]
    return {
        "summary": results.get("summary", {}),
        "bills": bills,
    }


def get_bill(bill_id: int) -> dict:
    """
    Full bill record: metadata, history, sponsors, votes, texts, amendments,
    supplements (fiscal notes), subjects.
    """
    data = _request({"op": "getBill", "id": bill_id})
    if "error" in data:
        return data
    return data.get("bill", {})


def get_bill_text(doc_id: int) -> dict:
    """
    Fetch and decode the actual text of a bill version.
    doc_id comes from bill['texts'][n]['doc_id'].
    Returns dict with 'text' (plain string), 'mime', 'date', 'type'.
    """
    data = _request({"op": "getBillText", "id": doc_id})
    if "error" in data:
        return data

    doc = data.get("text", {})
    encoded = doc.get("doc", "")
    mime = doc.get("mime", "")

    # LegiScan returns base64-encoded content
    try:
        raw_bytes = base64.b64decode(encoded)
    except Exception as e:
        return {"error": f"Failed to decode bill text: {e}"}

    # PDF or HTML — extract text accordingly
    if "html" in mime.lower() or "text" in mime.lower():
        try:
            text_content = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            text_content = raw_bytes.decode("latin-1", errors="replace")
    elif "pdf" in mime.lower():
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            text_content = "\n\n".join(pages).strip()
            if not text_content:
                text_content = f"[PDF extracted no text — {len(raw_bytes):,} bytes. " \
                               f"Use the state_link URL to access the PDF directly.]"
        except ImportError:
            text_content = f"[PDF parsing unavailable — install pdfplumber. " \
                           f"Use the state_link URL to access the PDF directly.]"
        except Exception as e:
            text_content = f"[PDF extraction failed: {e}. " \
                           f"Use the state_link URL to access the PDF directly.]"
    else:
        text_content = f"[Binary content: {mime} — {len(raw_bytes):,} bytes. " \
                       f"Use the state_link URL to access the PDF directly.]"

    return {
        "doc_id":     doc.get("doc_id"),
        "bill_id":    doc.get("bill_id"),
        "date":       doc.get("date"),
        "type":       doc.get("type"),
        "type_id":    doc.get("type_id"),
        "mime":       mime,
        "state_link": doc.get("state_link"),
        "text":       text_content,
        "text_size":  len(raw_bytes),
    }


def get_bill_text_latest(bill_id: int) -> dict:
    """
    Convenience wrapper: fetch the most recent enrolled or amended text for a bill.
    Falls back to the latest available version.
    Returns same structure as get_bill_text().
    """
    bill = get_bill(bill_id)
    if "error" in bill:
        return bill

    texts = bill.get("texts", [])
    if not texts:
        return {"error": "No text documents available for this bill"}

    # Preference order: Enrolled > Chaptered > Amended (latest) > Introduced
    TYPE_PRIORITY = {5: 0, 8: 1, 3: 2, 1: 3}  # enrolled, chaptered, amended, introduced
    sorted_texts = sorted(texts, key=lambda t: (TYPE_PRIORITY.get(t.get("type_id", 99), 99),
                                                 t.get("doc_id", 0)))
    best = sorted_texts[0]
    return get_bill_text(best["doc_id"])


def get_roll_call(roll_call_id: int) -> dict:
    """
    Individual member votes on a specific roll call.
    Returns summary counts plus per-member vote list.
    """
    data = _request({"op": "getRollCall", "id": roll_call_id})
    if "error" in data:
        return data
    return data.get("roll_call", {})


def get_all_roll_calls(bill_id: int) -> list:
    """
    Fetch every roll call vote for a bill, with individual member breakdowns.
    Returns list of enriched roll call dicts.
    """
    bill = get_bill(bill_id)
    if "error" in bill:
        return [bill]

    results = []
    for vote_stub in bill.get("votes", []):
        rc = get_roll_call(vote_stub["roll_call_id"])
        if "error" not in rc:
            results.append(rc)
    return results


def get_sponsor(people_id: int) -> dict:
    """
    Legislator profile + their full bill sponsorship history.
    """
    data = _request({"op": "getSponsor", "id": people_id})
    if "error" in data:
        return data
    return data.get("person", {})


def get_person(people_id: int) -> dict:
    """
    Legislator profile only (no bill list).
    """
    data = _request({"op": "getPerson", "id": people_id})
    if "error" in data:
        return data
    return data.get("person", {})


def get_session_list(state: str) -> list:
    """
    All legislative sessions available for a state.
    """
    data = _request({"op": "getSessionList", "state": state.upper()})
    if "error" in data:
        return [data]
    return data.get("sessions", [])


def get_master_list(session_id: int = None, state: str = None) -> dict:
    """
    All bills in a session. Provide either session_id or state (gets current session).
    Returns dict keyed by bill_id with basic bill info.
    """
    if session_id:
        params = {"op": "getMasterList", "id": session_id}
    elif state:
        params = {"op": "getMasterList", "state": state.upper()}
    else:
        return {"error": "Provide session_id or state"}

    data = _request(params, use_cache=False)
    if "error" in data:
        return data
    return data.get("masterlist", {})


def search_people(name: str, state: str = None) -> list:
    """
    Search for legislators by name, optionally filtered by state.
    Uses getMasterList + sponsor data — LegiScan has no direct people search,
    so this searches via a bill query for the person's name as sponsor.
    """
    params = {"op": "getSearch", "query": name, "year": 1}
    if state:
        params["state"] = state.upper()
    else:
        params["state"] = "ALL"

    data = _request(params, use_cache=False)
    if "error" in data:
        return [data]

    results = data.get("searchresult", {})
    bills = [v for k, v in results.items() if k != "summary"]

    # Collect unique sponsors matching the name
    people_seen = {}
    for bill in bills[:30]:
        bill_detail = get_bill(bill.get("bill_id", 0))
        if "error" in bill_detail:
            continue
        for sponsor in bill_detail.get("sponsors", []):
            pid = sponsor.get("people_id")
            sname = (sponsor.get("name") or "").lower()
            if pid and pid not in people_seen and name.lower() in sname:
                people_seen[pid] = {
                    "people_id":   pid,
                    "name":        sponsor.get("name"),
                    "party":       sponsor.get("party"),
                    "role":        sponsor.get("role"),
                    "state":       bill_detail.get("state"),
                    "district":    sponsor.get("district"),
                    "ballotpedia": sponsor.get("ballotpedia"),
                }
    return list(people_seen.values())


# ── Monitoring API functions ───────────────────────────────────────────────────

MONITOR_CACHE_FILE = CACHE_DIR / "monitor_hashes.json"

STANCE_MAP = {
    0: "watch",
    1: "support",
    2: "oppose",
}
STANCE_REVERSE = {v: k for k, v in STANCE_MAP.items()}


def _load_monitor_hashes() -> dict:
    """Load locally stored change_hash values for comparison."""
    if MONITOR_CACHE_FILE.exists():
        try:
            return json.loads(MONITOR_CACHE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_monitor_hashes(hashes: dict):
    """Save change_hash values locally for future comparison."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        MONITOR_CACHE_FILE.write_text(json.dumps(hashes, indent=2))
    except Exception:
        pass


def get_monitor_list(record: str = "current") -> dict:
    """
    Get the full GAITS monitor list with bill details.
    record: "current", "archived", or a year (e.g., "2024")
    Returns dict with 'bills' list containing full bill info.
    """
    params = {"op": "getMonitorList"}
    if record:
        params["record"] = record

    data = _request(params, use_cache=False)
    if "error" in data:
        return data

    bills = data.get("monitorlist", [])
    return {
        "count": len(bills),
        "bills": bills,
    }


def get_monitor_list_raw(record: str = "current") -> dict:
    """
    Get lightweight monitor list optimized for change detection.
    Returns bill_id, number, state, status, stance, and change_hash only.
    """
    params = {"op": "getMonitorListRaw"}
    if record:
        params["record"] = record

    data = _request(params, use_cache=False)
    if "error" in data:
        return data

    bills = data.get("monitorlist", [])
    return {
        "count": len(bills),
        "bills": bills,
    }


def set_monitor(bill_ids: list, action: str = "monitor", stance: str = "watch") -> dict:
    """
    Add, remove, or update bills on the monitor list.

    bill_ids: list of bill_id integers
    action: "monitor" (add), "remove" (delete), or "set" (update stance)
    stance: "watch", "support", or "oppose"

    Returns success/failure status.
    """
    if not bill_ids:
        return {"error": "No bill IDs provided"}

    valid_actions = {"monitor", "remove", "set"}
    if action not in valid_actions:
        return {"error": f"Invalid action '{action}'. Use: {', '.join(valid_actions)}"}

    valid_stances = {"watch", "support", "oppose"}
    if stance not in valid_stances:
        return {"error": f"Invalid stance '{stance}'. Use: {', '.join(valid_stances)}"}

    bill_list = ",".join(str(bid) for bid in bill_ids)
    params = {
        "op": "setMonitor",
        "list": bill_list,
        "action": action,
    }
    if action in ("monitor", "set"):
        params["stance"] = stance

    data = _request(params, use_cache=False)
    if "error" in data:
        return data

    return {
        "status": data.get("status", "OK"),
        "action": action,
        "bill_ids": bill_ids,
        "stance": stance if action != "remove" else None,
    }


def check_monitor_changes() -> dict:
    """
    Compare current monitor list against locally stored change_hash values.
    Returns bills that have changed since last check, plus summary.
    """
    # Get current state from API
    current = get_monitor_list_raw()
    if "error" in current:
        return current

    # Load previous hashes
    stored = _load_monitor_hashes()

    changed = []
    new_bills = []
    unchanged = []

    current_hashes = {}

    for bill in current.get("bills", []):
        bill_id = str(bill.get("bill_id"))
        current_hash = bill.get("change_hash", "")
        current_hashes[bill_id] = current_hash

        if bill_id not in stored:
            new_bills.append(bill)
        elif stored[bill_id] != current_hash:
            changed.append(bill)
        else:
            unchanged.append(bill)

    # Save current hashes for next comparison
    _save_monitor_hashes(current_hashes)

    return {
        "changed": changed,
        "new": new_bills,
        "unchanged_count": len(unchanged),
        "total": len(current.get("bills", [])),
        "has_changes": len(changed) > 0 or len(new_bills) > 0,
    }


def get_bill_changes(bill_id: int) -> dict:
    """
    Get detailed change information for a specific bill.
    Fetches full bill record and compares key fields to identify what changed.
    """
    bill = get_bill(bill_id)
    if "error" in bill:
        return bill

    return {
        "bill_id": bill.get("bill_id"),
        "bill_number": bill.get("bill_number"),
        "state": bill.get("state"),
        "title": bill.get("title"),
        "status": status_label(bill.get("status", 0)),
        "status_date": bill.get("status_date"),
        "last_action": bill.get("last_action"),
        "last_action_date": bill.get("last_action_date"),
        "change_hash": bill.get("change_hash"),
        "history": bill.get("history", [])[-5:],  # Last 5 actions
        "votes": bill.get("votes", []),
        "texts": bill.get("texts", []),
        "url": bill.get("url"),
    }


def stance_label(code: int) -> str:
    """Convert stance code to human-readable label."""
    return STANCE_MAP.get(code, "watch")


# ── Personal Docket functions ──────────────────────────────────────────────────

DOCKET_FILE = CACHE_DIR / "personal_docket.json"

PRIORITY_MAP = {
    1: "high",
    2: "medium",
    3: "low",
}
PRIORITY_REVERSE = {"high": 1, "medium": 2, "low": 3}


def _load_docket() -> dict:
    """Load the personal docket from disk."""
    if DOCKET_FILE.exists():
        try:
            return json.loads(DOCKET_FILE.read_text())
        except Exception:
            pass
    return {"bills": {}, "last_checked": None}


def _save_docket(docket: dict):
    """Save the personal docket to disk."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        DOCKET_FILE.write_text(json.dumps(docket, indent=2))
    except Exception:
        pass


def docket_add(bill_id: int, stance: str = "watch", priority: str = "medium",
               notes: str = "", tags: list = None) -> dict:
    """
    Add a bill to the personal docket and automatically monitor it.

    bill_id: LegiScan bill ID
    stance: "watch", "support", or "oppose"
    priority: "high", "medium", or "low"
    notes: optional personal notes about this bill
    tags: optional list of tags for categorization

    Returns the docket entry with bill details.
    """
    # Validate inputs
    if stance not in STANCE_REVERSE:
        return {"error": f"Invalid stance '{stance}'. Use: watch, support, oppose"}
    if priority not in PRIORITY_REVERSE:
        return {"error": f"Invalid priority '{priority}'. Use: high, medium, low"}

    # Fetch bill details
    bill = get_bill(bill_id)
    if "error" in bill:
        return bill

    # Add to GAITS monitor list
    monitor_result = set_monitor([bill_id], action="monitor", stance=stance)
    if "error" in monitor_result:
        return monitor_result

    # Build docket entry
    now = datetime.now().isoformat()
    entry = {
        "bill_id": bill_id,
        "state": bill.get("state"),
        "bill_number": bill.get("bill_number"),
        "title": bill.get("title"),
        "stance": stance,
        "priority": priority,
        "notes": notes,
        "tags": tags or [],
        "added_date": now,
        "last_updated": now,
        "initial_status": bill.get("status"),
        "initial_change_hash": bill.get("change_hash"),
    }

    # Save to docket
    docket = _load_docket()
    docket["bills"][str(bill_id)] = entry
    _save_docket(docket)

    return {
        "status": "added",
        "entry": entry,
        "bill": {
            "status": status_label(bill.get("status", 0)),
            "last_action": bill.get("last_action"),
            "last_action_date": bill.get("last_action_date"),
            "url": bill.get("url"),
        }
    }


def docket_remove(bill_id: int, keep_monitoring: bool = False) -> dict:
    """
    Remove a bill from the personal docket.

    bill_id: LegiScan bill ID
    keep_monitoring: if False, also removes from GAITS monitor list

    Returns confirmation.
    """
    docket = _load_docket()
    bill_key = str(bill_id)

    if bill_key not in docket["bills"]:
        return {"error": f"Bill {bill_id} is not in your docket"}

    removed_entry = docket["bills"].pop(bill_key)
    _save_docket(docket)

    # Optionally remove from GAITS monitor
    if not keep_monitoring:
        set_monitor([bill_id], action="remove")

    return {
        "status": "removed",
        "bill_id": bill_id,
        "bill_number": removed_entry.get("bill_number"),
        "state": removed_entry.get("state"),
        "was_monitoring": not keep_monitoring,
    }


def docket_update(bill_id: int, stance: str = None, priority: str = None,
                  notes: str = None, tags: list = None) -> dict:
    """
    Update a bill's docket entry (stance, priority, notes, or tags).

    Only provided fields are updated; others remain unchanged.
    """
    docket = _load_docket()
    bill_key = str(bill_id)

    if bill_key not in docket["bills"]:
        return {"error": f"Bill {bill_id} is not in your docket"}

    entry = docket["bills"][bill_key]

    if stance is not None:
        if stance not in STANCE_REVERSE:
            return {"error": f"Invalid stance '{stance}'. Use: watch, support, oppose"}
        entry["stance"] = stance
        # Update GAITS stance too
        set_monitor([bill_id], action="set", stance=stance)

    if priority is not None:
        if priority not in PRIORITY_REVERSE:
            return {"error": f"Invalid priority '{priority}'. Use: high, medium, low"}
        entry["priority"] = priority

    if notes is not None:
        entry["notes"] = notes

    if tags is not None:
        entry["tags"] = tags

    entry["last_updated"] = datetime.now().isoformat()
    _save_docket(docket)

    return {
        "status": "updated",
        "entry": entry,
    }


def docket_list(filter_by: dict = None) -> dict:
    """
    List all bills in the personal docket.

    filter_by: optional dict with keys like:
        - state: "TX", "CA", etc.
        - stance: "support", "oppose", "watch"
        - priority: "high", "medium", "low"
        - tag: a specific tag to filter by

    Returns list of docket entries sorted by priority then date added.
    """
    docket = _load_docket()
    entries = list(docket["bills"].values())

    # Apply filters
    if filter_by:
        if "state" in filter_by:
            entries = [e for e in entries if e.get("state", "").upper() == filter_by["state"].upper()]
        if "stance" in filter_by:
            entries = [e for e in entries if e.get("stance") == filter_by["stance"]]
        if "priority" in filter_by:
            entries = [e for e in entries if e.get("priority") == filter_by["priority"]]
        if "tag" in filter_by:
            entries = [e for e in entries if filter_by["tag"] in e.get("tags", [])]

    # Sort by priority (high first), then by added date (newest first)
    entries.sort(key=lambda e: (
        PRIORITY_REVERSE.get(e.get("priority", "medium"), 2),
        e.get("added_date", ""),
    ))

    return {
        "count": len(entries),
        "bills": entries,
        "last_checked": docket.get("last_checked"),
    }


def docket_report() -> dict:
    """
    Generate a comprehensive status report for all bills in the docket.

    Fetches current status for each bill, compares to initial state,
    and identifies what has changed.
    """
    docket = _load_docket()
    entries = list(docket["bills"].values())

    if not entries:
        return {
            "count": 0,
            "bills": [],
            "summary": {"total": 0},
        }

    # Check for changes via monitor API
    changes = check_monitor_changes()

    # Build set of changed bill IDs for quick lookup
    changed_ids = {str(b.get("bill_id")) for b in changes.get("changed", [])}

    report_bills = []
    status_counts = {}
    priority_counts = {"high": 0, "medium": 0, "low": 0}
    stance_counts = {"watch": 0, "support": 0, "oppose": 0}

    for entry in entries:
        bill_id = entry.get("bill_id")
        bill_key = str(bill_id)

        # Fetch current bill state
        bill = get_bill(bill_id)
        if "error" in bill:
            report_bills.append({
                "entry": entry,
                "current": None,
                "error": bill.get("error"),
                "has_changed": False,
            })
            continue

        current_status = status_label(bill.get("status", 0))
        status_counts[current_status] = status_counts.get(current_status, 0) + 1
        priority_counts[entry.get("priority", "medium")] += 1
        stance_counts[entry.get("stance", "watch")] += 1

        # Determine if changed
        has_changed = bill_key in changed_ids
        initial_hash = entry.get("initial_change_hash")
        current_hash = bill.get("change_hash")

        # Get recent history
        history = bill.get("history", [])[-3:]

        report_bills.append({
            "entry": entry,
            "current": {
                "status": current_status,
                "status_code": bill.get("status"),
                "last_action": bill.get("last_action"),
                "last_action_date": bill.get("last_action_date"),
                "change_hash": current_hash,
                "url": bill.get("url"),
                "votes": len(bill.get("votes", [])),
                "texts": len(bill.get("texts", [])),
            },
            "recent_history": history,
            "has_changed": has_changed or (initial_hash and initial_hash != current_hash),
        })

    # Sort: changed bills first, then by priority
    report_bills.sort(key=lambda b: (
        0 if b.get("has_changed") else 1,
        PRIORITY_REVERSE.get(b.get("entry", {}).get("priority", "medium"), 2),
    ))

    # Update last checked timestamp
    docket["last_checked"] = datetime.now().isoformat()
    _save_docket(docket)

    return {
        "count": len(report_bills),
        "bills": report_bills,
        "summary": {
            "total": len(report_bills),
            "changed": sum(1 for b in report_bills if b.get("has_changed")),
            "by_status": status_counts,
            "by_priority": priority_counts,
            "by_stance": stance_counts,
        },
        "checked_at": docket["last_checked"],
    }


def docket_get(bill_id: int) -> dict:
    """
    Get a single docket entry with current bill status.
    """
    docket = _load_docket()
    bill_key = str(bill_id)

    if bill_key not in docket["bills"]:
        return {"error": f"Bill {bill_id} is not in your docket"}

    entry = docket["bills"][bill_key]

    # Fetch current state
    bill = get_bill(bill_id)
    if "error" in bill:
        return {"entry": entry, "current": None, "error": bill.get("error")}

    return {
        "entry": entry,
        "current": {
            "status": status_label(bill.get("status", 0)),
            "last_action": bill.get("last_action"),
            "last_action_date": bill.get("last_action_date"),
            "change_hash": bill.get("change_hash"),
            "url": bill.get("url"),
            "sponsors": [s.get("name") for s in bill.get("sponsors", [])[:5]],
            "history": bill.get("history", [])[-5:],
            "votes": bill.get("votes", []),
        },
        "has_changed": entry.get("initial_change_hash") != bill.get("change_hash"),
    }


# ── Utility helpers used by skills ────────────────────────────────────────────

def status_label(code: int) -> str:
    return STATUS_MAP.get(code, f"Unknown ({code})")


def bills_from_master(master: dict) -> list:
    """Convert getMasterList response to a clean list."""
    return [v for k, v in master.items() if k != "session"]


def top_text_doc(bill: dict) -> dict | None:
    """Return the best available text document stub from a bill record."""
    texts = bill.get("texts", [])
    if not texts:
        return None
    TYPE_PRIORITY = {5: 0, 8: 1, 3: 2, 1: 3}
    return sorted(texts, key=lambda t: (TYPE_PRIORITY.get(t.get("type_id", 99), 99),
                                         t.get("doc_id", 0)))[0]


def format_date(d: str) -> str:
    """Format YYYY-MM-DD to Month D, YYYY, gracefully."""
    try:
        dt = datetime.strptime(d, "%Y-%m-%d")
        return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
    except Exception:
        return d or "—"
