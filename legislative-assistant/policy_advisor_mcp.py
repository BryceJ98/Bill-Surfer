"""
policy_advisor_mcp.py
---------------------
MCP server for the Personal Senior Policy Analyst.
All LegiScan I/O is delegated to legiscan_client.py.

Tools exposed to Claude:
  search_bills            — keyword search across states/sessions
  get_bill_detail         — full bill metadata, sponsors, history, vote stubs
  get_bill_text           — actual statutory language (decoded)
  get_bill_text_latest    — fetch most recent text version automatically
  get_roll_call           — individual member votes on one roll call
  get_all_roll_calls      — every vote on a bill with member breakdowns
  compare_bills_across_states — side-by-side comparison across states
  get_bill_status         — current status + full history
  analyze_policy_impact   — rich structured context for policy analysis
  get_session_list        — available sessions for a state
  get_master_list         — all bills in a session
  get_sponsor_profile     — legislator profile + sponsored bill history
"""

import json
from mcp.server.fastmcp import FastMCP
import legiscan_client as lc

mcp = FastMCP("Policy Advisor")


# ── Search ────────────────────────────────────────────────────────────────────

@mcp.tool()
def search_bills(query: str, state: str = "ALL", year: int = 2) -> str:
    """
    Search for legislation by keyword across U.S. states.

    Args:
        query: Keywords to search for (e.g. "gun control", "healthcare", "minimum wage")
        state: Two-letter state code (e.g. "TX", "CA") or "ALL" for all states
        year:  1=all years, 2=current session (default), 3=recent, 4=prior session
    """
    result = lc.search_bills(query, state, year)
    if "error" in result:
        return json.dumps(result)
    bills = result.get("bills", [])[:20]
    return json.dumps({"summary": result.get("summary", {}), "bills": bills}, indent=2)


# ── Bill detail ───────────────────────────────────────────────────────────────

@mcp.tool()
def get_bill_detail(bill_id: int) -> str:
    """
    Retrieve full bill metadata: title, sponsors, subjects, all history actions,
    vote stubs (use get_roll_call for member-level detail), text document list,
    amendment list, and fiscal note / supplement links.

    Args:
        bill_id: LegiScan bill ID (from search_bills results)
    """
    bill = lc.get_bill(bill_id)
    if "error" in bill:
        return json.dumps(bill)

    # Return the full record; truncate history to last 20 for token efficiency
    out = {
        "bill_id":          bill.get("bill_id"),
        "bill_number":      bill.get("bill_number"),
        "title":            bill.get("title"),
        "description":      bill.get("description"),
        "state":            bill.get("state"),
        "status":           lc.status_label(bill.get("status", 0)),
        "status_date":      bill.get("status_date"),
        "url":              bill.get("url"),
        "state_link":       bill.get("state_link"),
        "sponsors":         [
            {
                "name":    s.get("name"),
                "party":   s.get("party"),
                "role":    s.get("role"),
                "district":s.get("district"),
                "people_id": s.get("people_id"),
            }
            for s in bill.get("sponsors", [])
        ],
        "subjects":         [s.get("subject_name") for s in bill.get("subjects", [])],
        "history":          bill.get("history", [])[-20:],
        "votes": [
            {
                "roll_call_id": v.get("roll_call_id"),
                "date":         v.get("date"),
                "desc":         v.get("desc"),
                "yea":          v.get("yea"),
                "nay":          v.get("nay"),
                "passed":       v.get("passed"),
                "chamber":      v.get("chamber"),
            }
            for v in bill.get("votes", [])
        ],
        "texts": [
            {
                "doc_id":     t.get("doc_id"),
                "date":       t.get("date"),
                "type":       t.get("type"),
                "type_id":    t.get("type_id"),
                "mime":       t.get("mime"),
                "state_link": t.get("state_link"),
            }
            for t in bill.get("texts", [])
        ],
        "amendments": [
            {
                "amendment_id": a.get("amendment_id"),
                "adopted":      a.get("adopted"),
                "chamber":      a.get("chamber"),
                "date":         a.get("date"),
                "title":        a.get("title"),
            }
            for a in bill.get("amendments", [])
        ],
        "supplements": [
            {
                "supplement_id": s.get("supplement_id"),
                "type":          s.get("type"),
                "title":         s.get("title"),
                "description":   s.get("description"),
                "state_link":    s.get("state_link"),
            }
            for s in bill.get("supplements", [])
        ],
    }
    return json.dumps(out, indent=2)


# ── Bill text ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_bill_text(doc_id: int) -> str:
    """
    Fetch and decode the actual statutory text of a specific bill version.
    Use get_bill_detail first to get doc_id values from the 'texts' list.
    For PDF documents, returns a message with the direct state URL instead.

    Args:
        doc_id: Document ID from the bill's texts list (bill['texts'][n]['doc_id'])
    """
    result = lc.get_bill_text(doc_id)
    if "error" in result:
        return json.dumps(result)

    # Truncate very long texts to avoid overwhelming context — callers can
    # re-call with a specific section range if needed
    text = result.get("text", "")
    truncated = False
    if len(text) > 40000:
        text = text[:40000]
        truncated = True

    return json.dumps({
        "doc_id":     result.get("doc_id"),
        "bill_id":    result.get("bill_id"),
        "type":       result.get("type"),
        "date":       result.get("date"),
        "mime":       result.get("mime"),
        "state_link": result.get("state_link"),
        "text_size":  result.get("text_size"),
        "truncated":  truncated,
        "text":       text,
    }, indent=2)


@mcp.tool()
def get_bill_text_latest(bill_id: int) -> str:
    """
    Automatically fetch the most recent enrolled or amended text for a bill
    without needing to look up doc_id manually. Prefers enrolled > amended > introduced.

    Args:
        bill_id: LegiScan bill ID
    """
    result = lc.get_bill_text_latest(bill_id)
    if "error" in result:
        return json.dumps(result)

    text = result.get("text", "")
    truncated = False
    if len(text) > 40000:
        text = text[:40000]
        truncated = True

    return json.dumps({
        "doc_id":     result.get("doc_id"),
        "bill_id":    result.get("bill_id"),
        "type":       result.get("type"),
        "date":       result.get("date"),
        "mime":       result.get("mime"),
        "state_link": result.get("state_link"),
        "text_size":  result.get("text_size"),
        "truncated":  truncated,
        "text":       text,
    }, indent=2)


# ── Roll calls ────────────────────────────────────────────────────────────────

@mcp.tool()
def get_roll_call(roll_call_id: int) -> str:
    """
    Retrieve individual member votes for a specific roll call.
    Includes each legislator's name, party, and vote (Yea/Nay/NV/Absent).
    Get roll_call_id values from get_bill_detail's 'votes' list.

    Args:
        roll_call_id: Roll call ID from the bill's votes list
    """
    rc = lc.get_roll_call(roll_call_id)
    if "error" in rc:
        return json.dumps(rc)
    return json.dumps(rc, indent=2)


@mcp.tool()
def get_all_roll_calls(bill_id: int) -> str:
    """
    Fetch every roll call vote for a bill with full member-level breakdowns.
    Useful for partisan analysis, identifying persuadable votes, and comparing
    how individual legislators voted across multiple roll calls on the same bill.

    Args:
        bill_id: LegiScan bill ID
    """
    results = lc.get_all_roll_calls(bill_id)
    return json.dumps(results, indent=2)


# ── Status ────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_bill_status(bill_id: int) -> str:
    """
    Check the current legislative status and complete action history of a bill.

    Args:
        bill_id: LegiScan bill ID
    """
    bill = lc.get_bill(bill_id)
    if "error" in bill:
        return json.dumps(bill)

    return json.dumps({
        "bill_number":    bill.get("bill_number"),
        "title":          bill.get("title"),
        "state":          bill.get("state"),
        "current_status": lc.status_label(bill.get("status", 0)),
        "status_date":    bill.get("status_date"),
        "last_action":    bill.get("last_action"),
        "last_action_date": bill.get("last_action_date"),
        "url":            bill.get("url"),
        "full_history":   bill.get("history", []),
    }, indent=2)


# ── Policy analysis ───────────────────────────────────────────────────────────

@mcp.tool()
def analyze_policy_impact(bill_id: int) -> str:
    """
    Assemble the full evidence package for senior policy analysis of a bill:
    metadata, complete legislative history, all vote records with member breakdowns,
    sponsor profiles, fiscal note links, and the actual enrolled bill text.

    Claude should use this output to produce a structured analysis covering:
    - Which citizen groups are directly affected and how
    - Economic and fiscal implications (use fiscal notes + text)
    - Implementation challenges and regulatory requirements
    - Partisan dynamics (examine sponsor party + roll call party breakdown)
    - Likelihood of passage / sustainability based on history and current status
    - Comparison to similar legislation in other states where relevant

    Args:
        bill_id: LegiScan bill ID
    """
    bill = lc.get_bill(bill_id)
    if "error" in bill:
        return json.dumps(bill)

    # Fetch roll calls with member detail
    roll_calls = []
    for vote_stub in bill.get("votes", []):
        rc = lc.get_roll_call(vote_stub["roll_call_id"])
        if "error" not in rc:
            roll_calls.append(rc)

    # Fetch best available text
    text_result = lc.get_bill_text_latest(bill_id)
    bill_text = text_result.get("text", "") if "error" not in text_result else ""
    text_source = text_result.get("type", "")
    text_link = text_result.get("state_link", "")

    # Truncate text for context budget; still gives analyst substance
    if len(bill_text) > 30000:
        bill_text = bill_text[:30000] + "\n\n[TEXT TRUNCATED — see state_link for full document]"

    # Fiscal notes
    fiscal_notes = [
        {"title": s.get("title"), "description": s.get("description"),
         "state_link": s.get("state_link")}
        for s in bill.get("supplements", [])
        if s.get("type_id") == 1  # type_id 1 = Fiscal Note
    ]

    return json.dumps({
        "bill_number":      bill.get("bill_number"),
        "title":            bill.get("title"),
        "state":            bill.get("state"),
        "description":      bill.get("description"),
        "current_status":   lc.status_label(bill.get("status", 0)),
        "status_date":      bill.get("status_date"),
        "url":              bill.get("url"),
        "sponsors":         [
            {
                "name":      s.get("name"),
                "party":     s.get("party"),
                "role":      s.get("role"),
                "district":  s.get("district"),
                "people_id": s.get("people_id"),
            }
            for s in bill.get("sponsors", [])
        ],
        "subjects":          [s.get("subject_name") for s in bill.get("subjects", [])],
        "legislative_history": bill.get("history", []),
        "roll_calls":        roll_calls,
        "fiscal_notes":      fiscal_notes,
        "bill_text_type":    text_source,
        "bill_text_link":    text_link,
        "bill_text":         bill_text,
        "amendments":        [
            {
                "title":   a.get("title"),
                "adopted": a.get("adopted"),
                "chamber": a.get("chamber"),
                "date":    a.get("date"),
            }
            for a in bill.get("amendments", [])
        ],
    }, indent=2)


# ── Cross-state comparison ────────────────────────────────────────────────────

@mcp.tool()
def compare_bills_across_states(query: str, states: str, year: int = 1) -> str:
    """
    Search for similar legislation across multiple states and compare them.
    Returns top bills per state with status, last action, and bill numbers
    for use in a comparative policy analysis.

    Args:
        query:  Policy topic (e.g. "paid family leave", "assault weapons ban")
        states: Comma-separated state codes (e.g. "TX,CA,NY,FL,KS")
        year:   1=all years (default), 2=current session, 3=recent, 4=prior
    """
    state_list = [s.strip().upper() for s in states.split(",") if s.strip()]
    if not state_list:
        return json.dumps({"error": "No valid states provided"})

    comparison = {}
    for state in state_list:
        result = lc.search_bills(query, state, year)
        if "error" in result:
            comparison[state] = {"error": result["error"]}
            continue
        bills = result.get("bills", [])
        summary = result.get("summary", {})
        comparison[state] = {
            "total_found": summary.get("count", 0),
            "top_bills": [
                {
                    "bill_id":     b.get("bill_id"),
                    "bill_number": b.get("bill_number"),
                    "title":       b.get("title"),
                    "last_action": b.get("last_action"),
                    "last_action_date": b.get("last_action_date"),
                    "url":         b.get("url"),
                }
                for b in bills[:8]
            ],
        }
    return json.dumps(comparison, indent=2)


# ── Sessions & master lists ───────────────────────────────────────────────────

@mcp.tool()
def get_session_list(state: str) -> str:
    """
    List all available legislative sessions for a state.
    Useful for targeting a specific session when searching or pulling master lists.

    Args:
        state: Two-letter state code (e.g. "TX", "KS")
    """
    sessions = lc.get_session_list(state)
    return json.dumps(sessions, indent=2)


@mcp.tool()
def get_master_list(state: str = None, session_id: int = None) -> str:
    """
    Retrieve all bills in a legislative session. Provide state (current session)
    or session_id (specific session from get_session_list).
    Returns bill numbers, titles, and last actions for every bill in the session.

    Args:
        state:      Two-letter state code for current session
        session_id: Specific session ID (from get_session_list) for historical sessions
    """
    master = lc.get_master_list(session_id=session_id, state=state)
    if "error" in master:
        return json.dumps(master)

    bills = lc.bills_from_master(master)
    # Sort by last action date descending
    bills.sort(key=lambda b: b.get("last_action_date", ""), reverse=True)

    return json.dumps({
        "total_bills": len(bills),
        "bills": bills,
    }, indent=2)


# ── Legislator profile ────────────────────────────────────────────────────────

@mcp.tool()
def get_sponsor_profile(people_id: int) -> str:
    """
    Retrieve a legislator's full profile and their complete bill sponsorship history.
    Useful for understanding a sponsor's policy priorities and ideology.
    Get people_id from get_bill_detail's 'sponsors' list.

    Args:
        people_id: LegiScan person ID (from bill sponsors list)
    """
    person = lc.get_sponsor(people_id)
    if "error" in person:
        return json.dumps(person)
    return json.dumps(person, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
