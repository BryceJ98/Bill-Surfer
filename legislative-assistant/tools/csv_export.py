#!/usr/bin/env python3
"""
csv_export.py — Export Congress.gov and LegiScan data to CSV.

Usage:
    python csv_export.py <type> [query] [options]

Federal types (Congress.gov):
    nominations       Presidential nominations
    treaties          Senate treaties
    federal-bills     Federal legislation
    members           Congress members
    crs-reports       CRS bill summaries (supports --from / --to date range)
    house-votes       House roll call votes (118th Congress onward)
    committee-reports Committee reports
    hearings          Committee hearings

State types (LegiScan):
    state-bills       State legislation (requires --state)
    roll-calls        State roll call votes (requires --bill-id)
    legislators       State legislators (requires --state)
    docket            Personal docket entries
    monitor           GAITS monitor list

Options:
    --congress N       Single congress number (default: current)
    --congress N-M     Congress range, e.g. 115-119
    --state XX         State code, e.g. CA, TX (state types)
    --bill-id N        LegiScan bill_id (roll-calls only)
    --from YYYY-MM-DD  Start date filter (crs-reports)
    --to YYYY-MM-DD    End date filter (crs-reports)
    --chamber X        house or senate (members, hearings, committee-reports)
    --session N        Session number for house-votes (1 or 2, default 1)
    --year N           Year filter for state-bills
    --report-type X    hrpt, srpt, or erpt (committee-reports, default hrpt)
    --columns c1,c2    Comma-separated column names to include
    --all-columns      Include all available columns (implies --enrich)
    --enrich           Fetch extra detail per record for computed columns (slower)
    --limit N          Max records per congress/page (default 250)
    --output FILE      Output CSV path (default: <type>_export.csv)

Examples:
    python csv_export.py nominations ambassador --congress 117-119 \\
        --columns citation,nominee_names,position_title,organization,\\
                  received_date,confirmed,days_to_confirmation

    python csv_export.py treaties extradition --congress 100-119 --all-columns

    python csv_export.py state-bills "minimum wage" --state CA --enrich

    python csv_export.py roll-calls --bill-id 1234567

    python csv_export.py members --congress 119 --chamber senate

    python csv_export.py crs-reports healthcare --from 2015-01-01 --to 2020-12-31

    python csv_export.py docket --output my_docket.csv
"""

import argparse
import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path

# Allow importing sibling tools
sys.path.insert(0, str(Path(__file__).parent))

import congress_client as cc
import legiscan_client as lc


# ---------------------------------------------------------------------------
# Column catalog
# Each type has "base" columns (no extra API calls) and
# "enriched" columns (one extra API call per record — slower).
# ---------------------------------------------------------------------------

COLUMN_CATALOG: dict[str, dict] = {
    "nominations": {
        "base": [
            "congress", "citation", "description", "organization",
            "received_date", "is_civilian", "status", "status_date", "url",
        ],
        "enriched": [
            "nominee_names", "position_title",
            "confirmed", "confirmation_date", "days_to_confirmation",
        ],
    },
    "treaties": {
        "base": [
            "congress", "treaty_number", "suffix", "topic",
            "transmitted_date", "in_force_date", "status", "status_date",
            "url", "congress_url",
        ],
        "enriched": [
            "countries", "index_terms",
            "ratified", "ratification_date", "days_to_ratification",
        ],
    },
    "federal-bills": {
        "base": [
            "congress", "bill_id", "bill_label", "chamber", "title",
            "introduced_date", "policy_area", "status", "status_date",
            "sponsor", "sponsor_party", "sponsor_state", "url",
        ],
        "enriched": ["cosponsor_count", "action_count", "subjects"],
    },
    "members": {
        "base": ["name", "bioguide_id", "party", "state", "district", "chamber", "url"],
        "enriched": ["birth_year", "office_address", "phone", "website"],
    },
    "crs-reports": {
        "base": [
            "congress", "bill_label", "bill_type", "bill_number", "title",
            "summary_date", "summary_type", "summary_text", "url",
        ],
        "enriched": [],
    },
    "house-votes": {
        "base": [
            "roll_call", "session", "congress", "date",
            "question", "vote_type", "legislation", "result",
        ],
        "enriched": [
            "republican_yea", "republican_nay",
            "democrat_yea", "democrat_nay",
            "independent_yea", "independent_nay",
        ],
    },
    "committee-reports": {
        "base": [
            "congress", "number", "type", "type_label", "citation", "title",
            "issued_date", "is_conference", "committees", "associated_bills", "url",
        ],
        "enriched": [],
    },
    "hearings": {
        "base": [
            "congress", "chamber", "number", "date", "title",
            "location", "committees", "associated_bills", "url",
        ],
        "enriched": [],
    },
    "state-bills": {
        "base": [
            "bill_id", "bill_number", "state", "title",
            "status", "status_date", "last_action", "last_action_date", "url",
        ],
        "enriched": [
            "sponsor_name", "sponsor_party", "sponsor_district",
            "introduced_date", "subjects",
            "days_since_introduction", "days_to_last_action",
        ],
    },
    "roll-calls": {
        "base": [
            "roll_call_id", "bill_id", "date", "desc",
            "yea", "nay", "nv", "absent", "passed", "chamber",
            "total_votes", "pass_pct",
        ],
        "enriched": [],
    },
    "legislators": {
        "base": ["people_id", "name", "party", "role", "state", "district", "ballotpedia"],
        "enriched": [],
    },
    "docket": {
        "base": [
            "bill_id", "bill_number", "state", "stance", "priority",
            "notes", "tags", "status", "last_action", "added_date",
        ],
        "enriched": ["has_changed"],
    },
    "monitor": {
        "base": ["bill_id", "bill_number", "state", "status", "stance", "change_hash"],
        "enriched": ["title", "last_action", "last_action_date"],
    },
}

ALL_COLS      = {t: v["base"] + v["enriched"] for t, v in COLUMN_CATALOG.items()}
BASE_COLS     = {t: list(v["base"])            for t, v in COLUMN_CATALOG.items()}
ENRICHED_COLS = {t: set(v["enriched"])         for t, v in COLUMN_CATALOG.items()}
VALID_TYPES   = sorted(COLUMN_CATALOG.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(d: str):
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%m/%d/%Y"):
        try:
            return datetime.strptime(d, fmt).date()
        except (ValueError, TypeError):
            pass
    return None


def _days_between(d1: str, d2: str):
    a, b = _parse_date(d1), _parse_date(d2)
    return (b - a).days if (a and b) else ""


def _days_since(d1: str):
    a = _parse_date(d1)
    return (date.today() - a).days if a else ""


def _progress(i: int, total: int, label: str) -> None:
    msg = f"  Enriching {i}/{total}: {label[:45]}"
    print(f"\r{msg:<70}", end="", flush=True)


def _die(msg: str) -> None:
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _write_csv(path: str, fieldnames: list, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _print_preview(rows: list, columns: list, n: int = 5) -> None:
    if not rows:
        return
    preview  = rows[:n]
    # Show first 6 cols max to keep it readable
    cols     = columns[:6]
    max_cell = 30
    widths   = {
        c: min(max_cell, max(len(c), max(len(str(r.get(c) or "")) for r in preview)))
        for c in cols
    }

    def _fmt(v, w):
        return str(v or "")[:w].ljust(w)

    header = " | ".join(_fmt(c, widths[c]) for c in cols)
    sep    = "-+-".join("-" * widths[c] for c in cols)
    note   = f"(first {min(n, len(rows))} of {len(rows)} rows, first 6 columns)"
    print(f"\nPreview {note}:")
    print(header)
    print(sep)
    for row in preview:
        print(" | ".join(_fmt(row.get(c, ""), widths[c]) for c in cols))


def _parse_congress_arg(s: str | None) -> tuple[int, int]:
    if not s:
        cn = cc.current_congress()
        return cn, cn
    s = s.strip()
    m = re.match(r"^(\d{2,3})-(\d{2,3})$", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    try:
        n = int(s)
        return n, n
    except ValueError:
        _die(f"Invalid --congress value: '{s}'. Use a number (119) or range (115-119).")


def _resolve_columns(
    type_name: str, cols_arg: str | None, all_cols: bool
) -> tuple[list, bool]:
    """Return (final_column_list, enrich_needed)."""
    if all_cols:
        return ALL_COLS[type_name], bool(ENRICHED_COLS[type_name])
    if not cols_arg:
        return BASE_COLS[type_name], False

    requested = [c.strip() for c in cols_arg.split(",") if c.strip()]
    valid     = set(ALL_COLS[type_name])
    unknown   = [c for c in requested if c not in valid]
    if unknown:
        print(f"Warning: unknown columns for '{type_name}': {', '.join(unknown)}")
        print(f"  Available: {', '.join(ALL_COLS[type_name])}")
    final = [c for c in requested if c in valid]
    if not final:
        _die("No valid columns specified.")
    enrich = bool(set(final) & ENRICHED_COLS[type_name])
    return final, enrich


# ---------------------------------------------------------------------------
# Congress.gov fetch functions
# ---------------------------------------------------------------------------

def _enrich_nomination(nom: dict, congress: int, number) -> dict:
    row: dict = {}

    # Nominee names and positions
    nr = cc.get_nomination_nominees(congress, number)
    if "error" not in nr:
        nominees           = nr.get("nominees", [])
        row["nominee_names"]  = "; ".join(n.get("name", "")     for n in nominees[:5])
        row["position_title"] = "; ".join(n.get("position", "") for n in nominees[:5])
    else:
        row["nominee_names"] = row["position_title"] = ""

    # Confirmation status from action history
    ar = cc.get_nomination_actions(congress, number)
    if "error" not in ar:
        conf_date, confirmed = None, False
        for a in ar.get("actions", []):
            text = (a.get("text") or "").lower()
            if "confirmed" in text:
                conf_date, confirmed = a.get("date", ""), True
                break
            elif any(w in text for w in ("rejected", "withdrawn", "returned")):
                conf_date = a.get("date", "")
                break
        row["confirmed"]            = confirmed
        row["confirmation_date"]    = conf_date or ""
        row["days_to_confirmation"] = (
            _days_between(nom.get("received_date", ""), conf_date)
            if conf_date else ""
        )
    else:
        row["confirmed"] = row["confirmation_date"] = row["days_to_confirmation"] = ""
    return row


def fetch_nominations(congress_range: tuple, query: str | None, enrich: bool, limit: int) -> list:
    from_c, to_c = congress_range
    if from_c == to_c:
        r = cc.search_nominations(from_c, query=query, limit=limit)
        if "error" in r:
            _die(r["error"])
        nominations = r.get("nominations", [])
    else:
        r = cc.search_nominations_range(
            query=query, from_congress=from_c, to_congress=to_c, limit_per_congress=limit
        )
        if "error" in r:
            _die(r["error"])
        nominations = r.get("nominations", [])

    rows = []
    for i, nom in enumerate(nominations, 1):
        congress = nom.get("congress")
        number   = nom.get("number")
        row = {
            "congress":      congress,
            "citation":      nom.get("citation", ""),
            "description":   nom.get("description", ""),
            "organization":  nom.get("organization", ""),
            "received_date": nom.get("received_date", ""),
            "is_civilian":   nom.get("is_civilian", ""),
            "status":        nom.get("status", ""),
            "status_date":   nom.get("status_date", ""),
            "url":           nom.get("url", ""),
        }
        if enrich and congress and number:
            _progress(i, len(nominations), nom.get("citation", str(number)))
            row.update(_enrich_nomination(nom, congress, number))
        rows.append(row)
    if enrich:
        print()
    return rows


def fetch_treaties(congress_range: tuple, query: str | None, enrich: bool, limit: int) -> list:
    from_c, to_c = congress_range
    if from_c == to_c:
        r = cc.search_treaties(from_c, limit=limit)
        if "error" in r:
            _die(r["error"])
        treaties = r.get("treaties", [])
        if query:
            q        = query.lower()
            treaties = [t for t in treaties if q in (t.get("topic") or "").lower()]
    else:
        r = cc.search_treaties_range(
            query=query, from_congress=from_c, to_congress=to_c, limit_per_congress=limit
        )
        if "error" in r:
            _die(r["error"])
        treaties = r.get("treaties", [])

    rows = []
    for i, t in enumerate(treaties, 1):
        congress = t.get("congress")
        number   = t.get("number")
        row = {
            "congress":         congress,
            "treaty_number":    number,
            "suffix":           t.get("suffix", ""),
            "topic":            t.get("topic", ""),
            "transmitted_date": t.get("transmitted_date", ""),
            "in_force_date":    t.get("in_force_date", ""),
            "status":           t.get("status", ""),
            "status_date":      t.get("status_date", ""),
            "url":              t.get("url", ""),
            "congress_url":     t.get("congress_url", ""),
        }
        if enrich and congress and number:
            _progress(i, len(treaties), f"Treaty {congress}-{number}")

            detail = cc.get_treaty(congress, number)
            if "error" not in detail:
                row["countries"]   = "; ".join(detail.get("countries", []))
                row["index_terms"] = "; ".join(detail.get("index_terms", []))
            else:
                row["countries"] = row["index_terms"] = ""

            ar = cc.get_treaty_actions(congress, number)
            if "error" not in ar:
                rat_date, ratified = None, False
                for a in ar.get("actions", []):
                    text = (a.get("text") or "").lower()
                    if "resolution of ratification" in text or "ratif" in text:
                        rat_date, ratified = a.get("date", ""), True
                        break
                row["ratified"]             = ratified
                row["ratification_date"]    = rat_date or ""
                row["days_to_ratification"] = (
                    _days_between(t.get("transmitted_date", ""), rat_date)
                    if rat_date else ""
                )
            else:
                row["ratified"] = row["ratification_date"] = row["days_to_ratification"] = ""

        rows.append(row)
    if enrich:
        print()
    return rows


def fetch_federal_bills(congress_range: tuple, query: str | None, enrich: bool, limit: int) -> list:
    from_c, to_c = congress_range
    all_bills: list = []
    for cn in range(from_c, to_c + 1):
        r = cc.search_bills(query or "", congress=cn, limit=limit)
        if "error" not in r:
            all_bills.extend(r.get("bills", []))

    rows = []
    for i, b in enumerate(all_bills, 1):
        sponsors = b.get("sponsors", [])
        primary  = sponsors[0] if sponsors else {}
        row = {
            "congress":        b.get("congress", ""),
            "bill_id":         b.get("bill_id", ""),
            "bill_label":      b.get("bill_label", ""),
            "chamber":         b.get("chamber", ""),
            "title":           b.get("title", ""),
            "introduced_date": b.get("introduced_date", ""),
            "policy_area":     b.get("policy_area", ""),
            "status":          b.get("status", ""),
            "status_date":     b.get("status_date", ""),
            "sponsor":         primary.get("fullName", ""),
            "sponsor_party":   primary.get("party", ""),
            "sponsor_state":   primary.get("state", ""),
            "url":             b.get("url", ""),
        }
        if enrich:
            congress = b.get("congress")
            bt       = b.get("bill_type", "")
            bn       = b.get("bill_number", "")
            if congress and bt and bn:
                _progress(i, len(all_bills), b.get("bill_label", ""))
                detail = cc.get_bill(congress, bt, bn)
                if "error" not in detail:
                    row["cosponsor_count"] = detail.get("cosponsor_count", "")
                    row["action_count"]    = detail.get("action_count", "")
                    row["subjects"]        = "; ".join(detail.get("subjects", []))
                else:
                    row["cosponsor_count"] = row["action_count"] = row["subjects"] = ""
        rows.append(row)
    if enrich:
        print()
    return rows


def fetch_members(
    congress_range: tuple, state: str | None, chamber: str | None,
    enrich: bool, limit: int
) -> list:
    from_c = congress_range[0]
    if state:
        r = cc.search_members(state=state, limit=limit)
    else:
        r = cc.get_members_by_congress(congress=from_c, chamber=chamber, limit=limit)
    if "error" in r:
        _die(r["error"])
    members = r.get("members", [])

    rows = []
    for i, m in enumerate(members, 1):
        row = {
            "name":        m.get("name", ""),
            "bioguide_id": m.get("bioguide_id", ""),
            "party":       m.get("party", ""),
            "state":       m.get("state", ""),
            "district":    m.get("district", ""),
            "chamber":     m.get("chamber", ""),
            "url":         m.get("url", ""),
        }
        if enrich:
            bgid = m.get("bioguide_id", "")
            if bgid:
                _progress(i, len(members), m.get("name", ""))
                detail = cc.get_member(bgid)
                if "error" not in detail:
                    row["birth_year"]     = detail.get("birth_year", "")
                    row["office_address"] = detail.get("office_address", "")
                    row["phone"]          = detail.get("phone", "")
                    row["website"]        = detail.get("website", "")
                else:
                    row["birth_year"] = row["office_address"] = row["phone"] = row["website"] = ""
        rows.append(row)
    if enrich:
        print()
    return rows


def fetch_crs_reports(
    query: str | None, from_date: str | None, to_date: str | None, limit: int
) -> list:
    r = cc.search_crs_reports(query=query, limit=limit, from_date=from_date, to_date=to_date)
    if "error" in r:
        _die(r["error"])
    return [
        {
            "congress":     rpt.get("congress", ""),
            "bill_label":   rpt.get("bill_label", ""),
            "bill_type":    rpt.get("bill_type", ""),
            "bill_number":  rpt.get("bill_number", ""),
            "title":        rpt.get("title", ""),
            "summary_date": rpt.get("summary_date", ""),
            "summary_type": rpt.get("summary_type", ""),
            "summary_text": rpt.get("summary_text", ""),
            "url":          rpt.get("url", ""),
        }
        for rpt in r.get("reports", [])
    ]


def fetch_house_votes(
    congress_range: tuple, session: int, enrich: bool, limit: int
) -> list:
    from_c = congress_range[0]
    r = cc.search_house_votes(congress=from_c, session=session, limit=limit)
    if "error" in r:
        _die(r["error"])
    votes = r.get("votes", [])

    rows = []
    for i, v in enumerate(votes, 1):
        row = {
            "roll_call":  v.get("roll_call", ""),
            "session":    v.get("session", ""),
            "congress":   v.get("congress", ""),
            "date":       v.get("date", ""),
            "question":   v.get("question", ""),
            "vote_type":  v.get("vote_type", ""),
            "legislation": v.get("legislation", ""),
            "result":     v.get("result", ""),
        }
        if enrich:
            cn   = v.get("congress")
            sess = v.get("session")
            rc   = v.get("roll_call")
            if cn and sess and rc:
                _progress(i, len(votes), f"Roll #{rc}")
                detail = cc.get_house_vote(cn, sess, rc)
                if "error" not in detail:
                    for pt in detail.get("party_totals", []):
                        party = (pt.get("party") or "").upper()
                        if party in ("R", "REPUBLICAN"):
                            row["republican_yea"] = pt.get("yea", 0)
                            row["republican_nay"] = pt.get("nay", 0)
                        elif party in ("D", "DEMOCRAT", "DEMOCRATIC"):
                            row["democrat_yea"] = pt.get("yea", 0)
                            row["democrat_nay"] = pt.get("nay", 0)
                        elif party in ("ID", "INDEPENDENT", "I"):
                            row["independent_yea"] = pt.get("yea", 0)
                            row["independent_nay"] = pt.get("nay", 0)
        rows.append(row)
    if enrich:
        print()
    return rows


def fetch_committee_reports(
    congress_range: tuple, report_type: str, limit: int
) -> list:
    from_c = congress_range[0]
    r = cc.search_committee_reports(congress=from_c, report_type=report_type, limit=limit)
    if "error" in r:
        _die(r["error"])
    return [
        {
            "congress":        rpt.get("congress", ""),
            "number":          rpt.get("number", ""),
            "type":            rpt.get("type", ""),
            "type_label":      rpt.get("type_label", ""),
            "citation":        rpt.get("citation", ""),
            "title":           rpt.get("title", ""),
            "issued_date":     rpt.get("issued_date", ""),
            "is_conference":   rpt.get("is_conference", ""),
            "committees":      "; ".join(rpt.get("committees", [])),
            "associated_bills": "; ".join(rpt.get("associated_bills", [])),
            "url":             rpt.get("url", ""),
        }
        for rpt in r.get("reports", [])
    ]


def fetch_hearings(congress_range: tuple, chamber: str | None, limit: int) -> list:
    from_c = congress_range[0]
    ch = chamber or "house"
    r = cc.search_hearings(congress=from_c, chamber=ch, limit=limit)
    if "error" in r:
        _die(r["error"])
    return [
        {
            "congress":        h.get("congress", ""),
            "chamber":         h.get("chamber", ""),
            "number":          h.get("number", ""),
            "date":            h.get("date", ""),
            "title":           h.get("title", ""),
            "location":        h.get("location", ""),
            "committees":      "; ".join(h.get("committees", [])),
            "associated_bills": "; ".join(h.get("associated_bills", [])),
            "url":             h.get("url", ""),
        }
        for h in r.get("hearings", [])
    ]


# ---------------------------------------------------------------------------
# LegiScan fetch functions
# ---------------------------------------------------------------------------

def fetch_state_bills(
    query: str | None, state: str | None, year: int | None,
    enrich: bool, limit: int
) -> list:
    if not state:
        _die("--state is required for state-bills (e.g. --state CA)")
    r = lc.search_bills(query or "", state=state, year=year or 2)
    if "error" in r:
        _die(r["error"])
    bills = r.get("bills", [])[:limit]

    rows = []
    for i, b in enumerate(bills, 1):
        status_raw = b.get("status")
        status_code = status_raw if isinstance(status_raw, int) else 0
        row = {
            "bill_id":          b.get("bill_id", ""),
            "bill_number":      b.get("number", ""),
            "state":            b.get("state", ""),
            "title":            b.get("title", ""),
            "status":           lc.status_label(status_code),
            "status_date":      b.get("status_date", ""),
            "last_action":      b.get("last_action", ""),
            "last_action_date": b.get("last_action_date", ""),
            "url":              b.get("url", ""),
        }
        if enrich:
            bill_id = b.get("bill_id")
            if bill_id:
                _progress(i, len(bills), b.get("number", str(bill_id)))
                detail = lc.get_bill(bill_id)
                if "error" not in detail:
                    sponsors = detail.get("sponsors", [])
                    primary  = next(
                        (s for s in sponsors if s.get("sponsor_type_id") == 1),
                        sponsors[0] if sponsors else {}
                    )
                    row["sponsor_name"]     = primary.get("name", "")
                    row["sponsor_party"]    = primary.get("party", "")
                    row["sponsor_district"] = primary.get("district", "")

                    history    = detail.get("history", [])
                    intro_date = history[0].get("date", "") if history else ""
                    row["introduced_date"] = intro_date

                    subjects     = detail.get("subjects", [])
                    row["subjects"] = "; ".join(s.get("subject_name", "") for s in subjects)

                    last_date = b.get("last_action_date", "")
                    row["days_since_introduction"] = _days_since(intro_date) if intro_date else ""
                    row["days_to_last_action"]     = (
                        _days_between(intro_date, last_date) if (intro_date and last_date) else ""
                    )
                else:
                    for col in [
                        "sponsor_name", "sponsor_party", "sponsor_district",
                        "introduced_date", "subjects",
                        "days_since_introduction", "days_to_last_action",
                    ]:
                        row[col] = ""
        rows.append(row)
    if enrich:
        print()
    return rows


def fetch_roll_calls(bill_id: int | None) -> list:
    if not bill_id:
        _die("--bill-id is required for roll-calls export")
    r = lc.get_all_roll_calls(bill_id)
    if isinstance(r, list) and r and "error" in r[0]:
        _die(r[0]["error"])
    if not isinstance(r, list):
        _die(f"Unexpected response from get_all_roll_calls: {r}")

    rows = []
    for rc in r:
        yea   = rc.get("yea", 0) or 0
        nay   = rc.get("nay", 0) or 0
        total = yea + nay
        rows.append({
            "roll_call_id": rc.get("roll_call_id", ""),
            "bill_id":      bill_id,
            "date":         rc.get("date", ""),
            "desc":         rc.get("desc", ""),
            "yea":          yea,
            "nay":          nay,
            "nv":           rc.get("nv", ""),
            "absent":       rc.get("absent", ""),
            "passed":       rc.get("passed", ""),
            "chamber":      rc.get("chamber", ""),
            "total_votes":  total,
            "pass_pct":     round(yea / total * 100, 1) if total > 0 else "",
        })
    return rows


def fetch_legislators(query: str | None, state: str | None) -> list:
    if not state and not query:
        _die("Provide --state or a query keyword for legislators export")
    r = lc.search_people(name=query or "", state=state)
    if isinstance(r, list) and r and "error" in r[0]:
        _die(r[0]["error"])
    return [
        {
            "people_id":   p.get("people_id", ""),
            "name":        p.get("name", ""),
            "party":       p.get("party", ""),
            "role":        p.get("role", ""),
            "state":       p.get("state", ""),
            "district":    p.get("district", ""),
            "ballotpedia": p.get("ballotpedia", ""),
        }
        for p in (r if isinstance(r, list) else [])
    ]


def fetch_docket(enrich: bool) -> list:
    r = lc.docket_report()
    if "error" in r:
        _die(r["error"])

    changed_ids: set = set()
    if enrich:
        changes     = lc.check_monitor_changes()
        changed_ids = {b.get("bill_id") for b in changes.get("changed", [])}

    rows = []
    for item in r.get("bills", []):
        entry   = item.get("entry", {})
        current = item.get("current", {})
        bill_id = entry.get("bill_id", current.get("bill_id", ""))
        row = {
            "bill_id":     bill_id,
            "bill_number": current.get("bill_number", entry.get("bill_number", "")),
            "state":       current.get("state", entry.get("state", "")),
            "stance":      entry.get("stance", ""),
            "priority":    entry.get("priority", ""),
            "notes":       entry.get("notes", ""),
            "tags":        "; ".join(entry.get("tags") or []),
            "status":      current.get("status", ""),
            "last_action": current.get("last_action", ""),
            "added_date":  entry.get("added_date", ""),
        }
        if enrich:
            row["has_changed"] = bill_id in changed_ids
        rows.append(row)
    return rows


def fetch_monitor(enrich: bool) -> list:
    if enrich:
        r = lc.get_monitor_list(record="current")
        if "error" in r:
            _die(r["error"])
        return [
            {
                "bill_id":          b.get("bill_id", ""),
                "bill_number":      b.get("bill_number", ""),
                "state":            b.get("state", ""),
                "status":           lc.status_label(b.get("status", 0)),
                "stance":           lc.stance_label(b.get("stance", 0)),
                "change_hash":      b.get("change_hash", ""),
                "title":            b.get("title", ""),
                "last_action":      b.get("last_action", ""),
                "last_action_date": b.get("last_action_date", ""),
            }
            for b in r.get("bills", [])
        ]
    else:
        r = lc.get_monitor_list_raw(record="current")
        if "error" in r:
            _die(r["error"])
        return [
            {
                "bill_id":     b.get("bill_id", ""),
                "bill_number": b.get("number", b.get("bill_number", "")),
                "state":       b.get("state", ""),
                "status":      lc.status_label(b.get("status", 0)),
                "stance":      lc.stance_label(b.get("stance", 0)),
                "change_hash": b.get("change_hash", ""),
            }
            for b in r.get("bills", [])
        ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Congress.gov and LegiScan data to CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "type", choices=VALID_TYPES, metavar="type",
        help=f"Data type to export: {', '.join(VALID_TYPES)}",
    )
    parser.add_argument("query",        nargs="?",  default=None,   help="Keyword search query (optional)")
    parser.add_argument("--congress",               default=None,   help="Congress N or range N-M")
    parser.add_argument("--state",                  default=None,   help="State code, e.g. CA")
    parser.add_argument("--bill-id",   type=int,    default=None,   dest="bill_id", help="LegiScan bill_id")
    parser.add_argument("--from",                   default=None,   dest="from_date", help="Start date YYYY-MM-DD")
    parser.add_argument("--to",                     default=None,   dest="to_date",   help="End date YYYY-MM-DD")
    parser.add_argument("--chamber",   choices=["house","senate"],  default=None)
    parser.add_argument("--session",   type=int,    default=1,      help="Session number (house-votes)")
    parser.add_argument("--year",      type=int,    default=None,   help="Year filter (state-bills)")
    parser.add_argument("--report-type", choices=["hrpt","srpt","erpt"], default="hrpt", dest="report_type")
    parser.add_argument("--columns",                default=None,   help="Comma-separated column names")
    parser.add_argument("--all-columns", action="store_true",       dest="all_columns")
    parser.add_argument("--enrich",    action="store_true",         help="Fetch extra detail per record")
    parser.add_argument("--limit",     type=int,    default=250,    help="Max records per page (default 250)")
    parser.add_argument("--output",                 default=None,   help="Output CSV path")
    args = parser.parse_args()

    type_name      = args.type
    output         = args.output or f"{type_name.replace('-', '_')}_export.csv"
    congress_range = _parse_congress_arg(args.congress)
    final_cols, enrich_auto = _resolve_columns(type_name, args.columns, args.all_columns)
    enrich = args.enrich or args.all_columns or enrich_auto

    # Summary header
    print(f"Exporting: {type_name}")
    if args.query:      print(f"  Query:    '{args.query}'")
    if args.state:      print(f"  State:    {args.state}")
    if args.congress:   print(f"  Congress: {congress_range[0]}–{congress_range[1]}")
    if args.from_date:  print(f"  From:     {args.from_date}")
    if args.to_date:    print(f"  To:       {args.to_date}")
    print(f"  Columns:  {', '.join(final_cols)}")
    if enrich:          print("  Enrichment: ON (one extra API call per record)")
    print()

    # Dispatch
    rows: list = []
    if   type_name == "nominations":       rows = fetch_nominations(congress_range, args.query, enrich, args.limit)
    elif type_name == "treaties":          rows = fetch_treaties(congress_range, args.query, enrich, args.limit)
    elif type_name == "federal-bills":     rows = fetch_federal_bills(congress_range, args.query, enrich, args.limit)
    elif type_name == "members":           rows = fetch_members(congress_range, args.state, args.chamber, enrich, args.limit)
    elif type_name == "crs-reports":       rows = fetch_crs_reports(args.query, args.from_date, args.to_date, args.limit)
    elif type_name == "house-votes":       rows = fetch_house_votes(congress_range, args.session, enrich, args.limit)
    elif type_name == "committee-reports": rows = fetch_committee_reports(congress_range, args.report_type, args.limit)
    elif type_name == "hearings":          rows = fetch_hearings(congress_range, args.chamber, args.limit)
    elif type_name == "state-bills":       rows = fetch_state_bills(args.query, args.state, args.year, enrich, args.limit)
    elif type_name == "roll-calls":        rows = fetch_roll_calls(args.bill_id)
    elif type_name == "legislators":       rows = fetch_legislators(args.query, args.state)
    elif type_name == "docket":            rows = fetch_docket(enrich)
    elif type_name == "monitor":           rows = fetch_monitor(enrich)

    if not rows:
        print("No data found. Nothing exported.")
        sys.exit(1)

    _write_csv(output, final_cols, rows)
    _print_preview(rows, final_cols)
    print(f"\nExported {len(rows)} records to:")
    print(f"  {Path(output).resolve()}")


if __name__ == "__main__":
    main()
