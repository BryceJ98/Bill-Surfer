"""
search.py — Search bills, nominations, and treaties using the user's own API keys.
"""

import json

import litellm
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_db, log_api_usage
from app.routers.keys import get_user_key
from app.tools import congress_client as cc
from app.tools import legiscan_client as lc

router = APIRouter()


def _require_key(user_id: str, provider: str) -> str:
    key = get_user_key(user_id, provider)
    if not key:
        raise HTTPException(
            status_code=402,
            detail=f"No {provider} API key stored. Add it in Settings.",
        )
    return key


# ---------------------------------------------------------------------------
# Federal: bills
# ---------------------------------------------------------------------------
@router.get("/federal/bills", summary="Search federal bills (Congress.gov)")
def search_federal_bills(
    q:        str  = Query(..., description="Search keywords"),
    congress: int  = Query(None, description="Congress number (default: current)"),
    limit:    int  = Query(20,   ge=1, le=250),
    offset:   int  = Query(0,    ge=0),
    user      = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "congress")
    result = cc.search_bills(q, congress=congress, limit=limit, offset=offset, api_key=api_key)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    log_api_usage(user["user_id"], "congress")
    return result


# ---------------------------------------------------------------------------
# Federal: nominations
# ---------------------------------------------------------------------------
@router.get("/federal/nominations", summary="Search presidential nominations")
def search_nominations(
    q:        str | None = Query(None),
    congress: int        = Query(None),
    limit:    int        = Query(20, ge=1, le=250),
    offset:   int        = Query(0,  ge=0),
    user      = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "congress")
    result = cc.search_nominations(congress=congress, query=q, limit=limit, offset=offset, api_key=api_key)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    log_api_usage(user["user_id"], "congress")
    return result


# ---------------------------------------------------------------------------
# Federal: treaties
# ---------------------------------------------------------------------------
@router.get("/federal/treaties", summary="Search Senate treaties")
def search_treaties(
    congress: int        = Query(None),
    q:        str | None = Query(None),
    limit:    int        = Query(20, ge=1, le=250),
    offset:   int        = Query(0,  ge=0),
    user      = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "congress")
    result = cc.search_treaties(congress=congress, limit=limit, offset=offset, query=q, api_key=api_key)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    log_api_usage(user["user_id"], "congress")
    return result


# ---------------------------------------------------------------------------
# State: bills via LegiScan
# ---------------------------------------------------------------------------
@router.get("/state/bills", summary="Search state bills (LegiScan)")
def search_state_bills(
    q:      str  = Query(...),
    state:  str  = Query(..., min_length=2, max_length=2),
    year:   int  = Query(None),
    limit:  int  = Query(20, ge=1, le=50),
    offset: int  = Query(0,  ge=0),
    user    = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "legiscan")
    result = lc.search_bills(q, state=state.upper(), year=year or 2, api_key=api_key)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    log_api_usage(user["user_id"], "legiscan")
    bills_all = (result.get("bills") or result) if isinstance(result, dict) else result
    if not isinstance(bills_all, list):
        bills_all = []
    return {"bills": bills_all[offset:offset + limit], "total": len(bills_all), "query": q, "state": state.upper()}


# ---------------------------------------------------------------------------
# Bill detail
# ---------------------------------------------------------------------------
@router.get("/federal/bill", summary="Get federal bill detail")
def get_federal_bill(
    congress:    int = Query(...),
    bill_type:   str = Query(...),
    bill_number: int = Query(...),
    user         = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "congress")
    result = cc.get_bill(congress, bill_type, bill_number, api_key=api_key)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    log_api_usage(user["user_id"], "congress")
    return result


@router.get("/federal/bill/full", summary="Get federal bill with CRS summary and recent actions")
def get_federal_bill_full(
    congress:    int = Query(...),
    bill_type:   str = Query(...),
    bill_number: int = Query(...),
    user         = Depends(get_current_user),
):
    api_key  = _require_key(user["user_id"], "congress")
    detail   = cc.get_bill(congress, bill_type, bill_number, api_key=api_key)
    if "error" in detail:
        raise HTTPException(status_code=502, detail=detail["error"])
    summaries = cc.get_bill_summaries(congress, bill_type, bill_number, api_key=api_key)
    actions   = cc.get_bill_actions(congress, bill_type, bill_number, limit=10, api_key=api_key)
    log_api_usage(user["user_id"], "congress", calls=3)
    return {
        **detail,
        "summary_text":   summaries.get("latest", ""),
        "summary_date":   summaries.get("latest_date", ""),
        "recent_actions": actions.get("actions", []),
    }


@router.get("/state/bill", summary="Get state bill detail (LegiScan)")
def get_state_bill(
    bill_id: int = Query(...),
    user     = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "legiscan")
    result = lc.get_bill(bill_id, api_key=api_key)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    log_api_usage(user["user_id"], "legiscan")
    return result


# ---------------------------------------------------------------------------
# Agent search — AI-powered natural language bill finder
# ---------------------------------------------------------------------------

_AGENT_SYSTEM = """\
You are a legislative research agent. Your job is to find specific bills for a researcher.

Given the user's query, search intelligently:
- For named acts (e.g. "CHIPS Act", "ACA", "PATRIOT Act"): try the common name, the acronym
  expanded, and keywords from the full official title.
- Many landmark laws passed in the 117th (2021-22) or 118th (2023-24) Congress, not just
  the current 119th. Always try congress=117, 118, and 119 for well-known legislation.
- Run 3-6 targeted searches to cast a wide net.
- Once you find strong candidates, call get_federal_bill on the 1-2 best matches to fetch
  full details so the researcher gets rich metadata.
- After searching, write exactly 1-2 sentences explaining what you found and from which Congress.
"""

_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_federal_bills",
            "description": "Search federal bills by keyword with optional congress number",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":    {"type": "string"},
                    "congress": {"type": "integer", "description": "e.g. 117, 118, 119"},
                    "limit":    {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_federal_bill",
            "description": "Fetch full details for a specific federal bill",
            "parameters": {
                "type": "object",
                "properties": {
                    "congress":    {"type": "integer"},
                    "bill_type":   {"type": "string", "description": "hr, s, hres, sres, hjres, sjres"},
                    "bill_number": {"type": "integer"},
                },
                "required": ["congress", "bill_type", "bill_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_state_bills",
            "description": "Search state bills via LegiScan",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "state": {"type": "string", "description": "Two-letter state code, e.g. CA"},
                },
                "required": ["query", "state"],
            },
        },
    },
]


class AgentSearchRequest(BaseModel):
    query: str
    state: str | None = None  # optional hint for state-scoped queries


@router.post("/agent", summary="AI agent — natural language bill search")
def agent_search(body: AgentSearchRequest, user=Depends(get_current_user)):
    db      = get_db()
    user_id = user["user_id"]

    s = db.table("user_settings").select("ai_provider, ai_model").eq("user_id", user_id).execute()
    if not s.data:
        raise HTTPException(status_code=400, detail="Configure your AI provider in Settings first.")
    ai_provider = s.data[0]["ai_provider"]
    ai_model    = s.data[0]["ai_model"]
    ai_key      = get_user_key(user_id, ai_provider)
    if not ai_key:
        raise HTTPException(status_code=402, detail=f"No {ai_provider} API key stored. Add it in Settings.")

    congress_key = get_user_key(user_id, "congress")
    legiscan_key = get_user_key(user_id, "legiscan")

    messages: list[dict] = [
        {"role": "system",  "content": _AGENT_SYSTEM},
        {"role": "user",    "content": body.query},
    ]

    collected: list[dict] = []
    seen_ids:  set[str]   = set()
    searches:  list[str]  = []
    explanation = ""

    def _run_tool(name: str, args: dict) -> str:
        try:
            if name == "search_federal_bills":
                q   = args.get("query", "")
                cng = args.get("congress")
                searches.append(f"Federal: \"{q}\"" + (f" ({cng}th)" if cng else ""))
                r = cc.search_bills(q, congress=cng, limit=args.get("limit", 10), api_key=congress_key)
                log_api_usage(user_id, "congress")
                for b in r.get("bills", []):
                    bid = b.get("bill_id", "")
                    if bid and bid not in seen_ids:
                        seen_ids.add(bid)
                        collected.append(b)
                return json.dumps(r, default=str)[:4000]

            elif name == "get_federal_bill":
                r = cc.get_bill(args["congress"], args["bill_type"], args["bill_number"], api_key=congress_key)
                log_api_usage(user_id, "congress")
                bid = r.get("bill_id", "")
                if bid:
                    # Promote this enriched record to the top (replaces any stub from a search)
                    collected[:] = [b for b in collected if b.get("bill_id") != bid]
                    seen_ids.add(bid)
                    collected.insert(0, r)
                return json.dumps(r, default=str)[:4000]

            elif name == "search_state_bills":
                q  = args.get("query", "")
                st = (args.get("state") or body.state or "").upper()
                searches.append(f"State {st}: \"{q}\"")
                r  = lc.search_bills(q, state=st, year=2, api_key=legiscan_key)
                log_api_usage(user_id, "legiscan")
                bills = r.get("bills", r) if isinstance(r, dict) else r
                for b in (bills if isinstance(bills, list) else [])[:10]:
                    bid = str(b.get("bill_id", ""))
                    if bid and bid not in seen_ids:
                        seen_ids.add(bid)
                        collected.append({**b, "state": st})
                return json.dumps(r, default=str)[:4000]

        except Exception as exc:
            return json.dumps({"error": str(exc)})
        return json.dumps({"error": f"Unknown tool: {name}"})

    for _ in range(6):  # max 6 tool-call rounds
        try:
            resp = litellm.completion(
                model=ai_model, api_key=ai_key,
                messages=messages, tools=_AGENT_TOOLS,
                tool_choice="auto", timeout=90,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"AI provider error: {exc}")

        usage = getattr(resp, "usage", None)
        tokens = getattr(usage, "total_tokens", 0) or 0
        if tokens:
            log_api_usage(user_id, ai_provider, calls=0, tokens=tokens)

        msg = resp.choices[0].message if resp.choices else None
        if not msg:
            break
        if not msg.tool_calls:
            explanation = msg.content or ""
            break

        messages.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except Exception:
                args = {}
            messages.append({
                "role": "tool", "tool_call_id": tc.id,
                "content": _run_tool(tc.function.name, args),
            })

    return {
        "bills":       collected[:25],
        "explanation": explanation,
        "searches":    searches,
        "query":       body.query,
    }
