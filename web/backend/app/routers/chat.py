"""
chat.py — AI chat endpoint with legislative research tools.
Uses LiteLLM to route to the user's chosen model (Claude, GPT-4, Gemini, etc.)
and exposes congress_client + legiscan_client functions as callable tools.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import litellm

from app.auth import get_current_user
from app.db import get_db, log_api_usage
from app.routers.keys import get_user_key
from app.tools import congress_client as cc
from app.tools import legiscan_client as lc

router = APIRouter()


# ---------------------------------------------------------------------------
# Tool definitions (OpenAI-style function calling schema)
# ---------------------------------------------------------------------------
TOOLS = [
    # ── Legislative search ────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "search_federal_bills",
            "description": "Search federal bills by keyword. Use this to find bills on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":    {"type": "string"},
                    "congress": {"type": "integer", "description": "Congress number, e.g. 119"},
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
            "description": "Get full details for a specific federal bill including sponsor, status, committees",
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
            "name": "get_bill_summary",
            "description": "Get the official CRS (Congressional Research Service) summary for a federal bill",
            "parameters": {
                "type": "object",
                "properties": {
                    "congress":    {"type": "integer"},
                    "bill_type":   {"type": "string"},
                    "bill_number": {"type": "integer"},
                },
                "required": ["congress", "bill_type", "bill_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bill_actions",
            "description": "Get recent legislative actions and timeline for a federal bill",
            "parameters": {
                "type": "object",
                "properties": {
                    "congress":    {"type": "integer"},
                    "bill_type":   {"type": "string"},
                    "bill_number": {"type": "integer"},
                    "limit":       {"type": "integer", "default": 10},
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
                    "year":  {"type": "integer"},
                },
                "required": ["query", "state"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_nominations",
            "description": "Search presidential nominations before the Senate",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":    {"type": "string"},
                    "congress": {"type": "integer"},
                    "limit":    {"type": "integer", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_treaties",
            "description": "Search Senate treaties",
            "parameters": {
                "type": "object",
                "properties": {
                    "congress": {"type": "integer"},
                    "query":    {"type": "string"},
                    "limit":    {"type": "integer", "default": 10},
                },
            },
        },
    },
    # ── Docket management ────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_docket",
            "description": "Retrieve the user's current docket (list of tracked bills)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_docket",
            "description": (
                "Add a bill to the user's docket so they can track it. "
                "For federal bills use state='US'. "
                "Provide as much info as you have: bill_id, bill_number, title."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "bill_id":     {"type": "string",  "description": "Unique bill identifier, e.g. 'us-hr-1234' or LegiScan numeric ID as string"},
                    "bill_number": {"type": "string",  "description": "Human-readable number, e.g. 'HR 1234' or 'SB 5'"},
                    "state":       {"type": "string",  "description": "Two-letter state code or 'US' for federal"},
                    "title":       {"type": "string",  "description": "Short bill title"},
                    "stance":      {"type": "string",  "description": "support | oppose | neutral | watching"},
                    "notes":       {"type": "string"},
                    "tags":        {"type": "array", "items": {"type": "string"}},
                },
                "required": ["bill_id", "state"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_docket",
            "description": "Remove a bill from the user's docket by its docket item ID (not bill_id). Call get_docket first to find the item ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string", "description": "The docket item UUID (from get_docket results)"},
                },
                "required": ["item_id"],
            },
        },
    },
    # ── Reports ─────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": (
                "Queue a PDF policy report for a bill. "
                "The report is generated asynchronously and will appear in the user's Report Library. "
                "Use this when the user asks for a report, analysis, or deep-dive on a bill."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "bill_id":     {"type": "string"},
                    "bill_number": {"type": "string"},
                    "state":       {"type": "string", "description": "'US' for federal, or state code"},
                    "title":       {"type": "string"},
                    "report_type": {
                        "type": "string",
                        "description": "policy_impact | summary | vote_analysis | comparison",
                        "default": "policy_impact",
                    },
                },
                "required": ["bill_id", "bill_number", "state", "title"],
            },
        },
    },
]


def _dispatch_tool(
    name: str, args: dict,
    congress_key: str | None, legiscan_key: str | None,
    user_id: str, db,
    ai_provider: str | None = None,
    ai_model: str | None = None,
    ai_key: str | None = None,
) -> str:
    """Execute a tool call and return the result as a JSON string."""
    try:
        # ── Legislative search ──────────────────────────────────────────
        if name == "search_federal_bills":
            r = cc.search_bills(args["query"], congress=args.get("congress"), limit=args.get("limit", 10), api_key=congress_key)
            log_api_usage(user_id, "congress")

        elif name == "get_federal_bill":
            r = cc.get_bill(args["congress"], args["bill_type"], args["bill_number"], api_key=congress_key)
            log_api_usage(user_id, "congress")

        elif name == "get_bill_summary":
            r = cc.get_bill_summaries(args["congress"], args["bill_type"], args["bill_number"], api_key=congress_key)
            log_api_usage(user_id, "congress")

        elif name == "get_bill_actions":
            r = cc.get_bill_actions(args["congress"], args["bill_type"], args["bill_number"],
                                    limit=args.get("limit", 10), api_key=congress_key)
            log_api_usage(user_id, "congress")

        elif name == "search_state_bills":
            r = lc.search_bills(args["query"], state=args["state"], year=args.get("year", 2), api_key=legiscan_key)
            log_api_usage(user_id, "legiscan")

        elif name == "search_nominations":
            r = cc.search_nominations(congress=args.get("congress"), query=args.get("query"), limit=args.get("limit", 10), api_key=congress_key)
            log_api_usage(user_id, "congress")

        elif name == "search_treaties":
            r = cc.search_treaties(congress=args.get("congress"), limit=args.get("limit", 10), query=args.get("query"), api_key=congress_key)
            log_api_usage(user_id, "congress")

        # ── Docket management ──────────────────────────────────────────
        elif name == "get_docket":
            rows = db.table("docket").select("*").eq("user_id", user_id).order("added_date", desc=True).execute()
            r = rows.data or []

        elif name == "add_to_docket":
            row = {
                "user_id":     user_id,
                "bill_id":     str(args["bill_id"]),
                "bill_number": str(args.get("bill_number") or ""),
                "state":       str(args.get("state", "US")).upper(),
                "title":       str(args.get("title") or ""),
                "stance":      args.get("stance"),
                "notes":       args.get("notes"),
                "tags":        args.get("tags") or [],
            }
            try:
                result = db.table("docket").insert(row).execute()
                r = {"success": True, "item": result.data[0] if result.data else row}
            except Exception as exc:
                if "unique" in str(exc).lower():
                    r = {"success": False, "error": "Bill is already in your docket"}
                else:
                    r = {"success": False, "error": str(exc)}

        elif name == "remove_from_docket":
            db.table("docket").delete().eq("id", args["item_id"]).eq("user_id", user_id).execute()
            r = {"success": True, "removed": args["item_id"]}

        # ── Reports ────────────────────────────────────────────────────
        elif name == "generate_report":
            from fastapi import BackgroundTasks
            from app.routers.reports import _run_report_generation
            settings = db.table("user_settings").select("ai_provider, ai_model").eq("user_id", user_id).execute()
            if not settings.data:
                r = {"success": False, "error": "Configure AI provider in Settings first"}
            else:
                _ai_provider = settings.data[0]["ai_provider"]
                _ai_model    = settings.data[0]["ai_model"]
                from app.routers.keys import get_user_key as _guk
                _ai_key = _guk(user_id, _ai_provider)
                if not _ai_key:
                    r = {"success": False, "error": f"No {_ai_provider} API key stored. Add it in Settings."}
                else:
                    report_type = args.get("report_type") or "policy_impact"
                    insert = db.table("reports").insert({
                        "user_id":     user_id,
                        "bill_id":     str(args["bill_id"]),
                        "bill_number": str(args["bill_number"]),
                        "state":       str(args.get("state", "US")).upper(),
                        "title":       str(args["title"]),
                        "report_type": report_type,
                        "ai_provider": _ai_provider,
                        "ai_model":    _ai_model,
                        "status":      "generating",
                    }).execute()
                    report_id = insert.data[0]["id"]
                    import threading
                    thread = threading.Thread(
                        target=_run_report_generation,
                        args=(
                            report_id, user_id,
                            str(args["bill_id"]), str(args["bill_number"]),
                            str(args.get("state", "US")).upper(), str(args["title"]), report_type,
                            _ai_provider, _ai_model, _ai_key,
                            congress_key, legiscan_key,
                        ),
                        daemon=True,
                    )
                    thread.start()
                    r = {
                        "success":   True,
                        "report_id": report_id,
                        "message":   f"Report queued! It will appear in your Report Library at /reports in 30–60 seconds.",
                    }

        else:
            r = {"error": f"Unknown tool: {name}"}

    except Exception as exc:
        r = {"error": str(exc)}

    return json.dumps(r, default=str)[:6000]  # cap at 6k chars to stay within context


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------
class Message(BaseModel):
    role:    str   # user | assistant | system
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------
@router.post("", summary="Chat with the legislative research AI")
def chat(body: ChatRequest, user=Depends(get_current_user)):
    db      = get_db()
    user_id = user["user_id"]

    # Load settings
    settings = db.table("user_settings").select("ai_provider, ai_model").eq("user_id", user_id).execute()
    if not settings.data:
        raise HTTPException(status_code=400, detail="Configure your AI provider in Settings first")

    ai_provider = settings.data[0]["ai_provider"]
    ai_model    = settings.data[0]["ai_model"]
    ai_key      = get_user_key(user_id, ai_provider)
    if not ai_key:
        raise HTTPException(status_code=402, detail=f"No {ai_provider} API key stored")

    congress_key = get_user_key(user_id, "congress")
    legiscan_key = get_user_key(user_id, "legiscan")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a nonpartisan legislative research assistant for political science researchers. "
                "You have access to real-time legislative data AND the ability to manage the user's docket and generate reports.\n\n"
                "CAPABILITIES:\n"
                "- Search federal bills, state bills, nominations, treaties\n"
                "- Fetch full bill details, CRS summaries, and legislative action timelines\n"
                "- Add bills to the user's docket (call add_to_docket). For federal bills use state='US'. "
                "  Build the bill_id as 'us-{bill_type}-{bill_number}' for federal (e.g. 'us-hr-1234').\n"
                "- Remove bills from the docket (call get_docket first to find the item ID)\n"
                "- Queue PDF policy reports (call generate_report). The report appears in /reports in ~60 seconds.\n\n"
                "RULES:\n"
                "- Always cite bill numbers and sources.\n"
                "- When the user asks to 'add to docket', 'track this bill', or 'save this': use add_to_docket.\n"
                "- When the user asks for a 'report', 'analysis', or 'deep-dive': use generate_report.\n"
                "- After adding to docket or queuing a report, confirm to the user with the bill name.\n"
                "- Be concise and factual."
            ),
        }
    ] + [m.model_dump() for m in body.messages]

    # Agentic loop — keep calling until no more tool calls
    for _ in range(8):  # max 8 tool-call rounds
        try:
            response = litellm.completion(
                model=ai_model,
                api_key=ai_key,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                timeout=60,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"AI provider error: {exc}")

        # Log AI token usage
        usage = getattr(response, "usage", None)
        total_tokens = getattr(usage, "total_tokens", 0) or 0
        if total_tokens:
            log_api_usage(user_id, ai_provider, calls=0, tokens=total_tokens)

        msg = response.choices[0].message if response.choices else None
        if not msg:
            raise HTTPException(status_code=502, detail="Empty response from AI provider")

        if not msg.tool_calls:
            return {"role": "assistant", "content": msg.content or ""}

        # Execute tool calls
        messages.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError):
                args = {}
            result = _dispatch_tool(tc.function.name, args, congress_key, legiscan_key, user_id, db, ai_provider, ai_model, ai_key)
            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      result,
            })

    return {"role": "assistant", "content": "I reached the maximum number of tool calls. Please try a more specific question."}
