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
    {
        "type": "function",
        "function": {
            "name": "search_federal_bills",
            "description": "Search federal bills by keyword",
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
            "name": "search_nominations",
            "description": "Search presidential nominations",
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
            "name": "get_federal_bill",
            "description": "Get full details for a specific federal bill",
            "parameters": {
                "type": "object",
                "properties": {
                    "congress":    {"type": "integer"},
                    "bill_type":   {"type": "string", "description": "hr, s, hres, sres, etc."},
                    "bill_number": {"type": "integer"},
                },
                "required": ["congress", "bill_type", "bill_number"],
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
                    "limit":    {"type": "integer", "default": 10},
                },
            },
        },
    },
]


def _dispatch_tool(
    name: str, args: dict,
    congress_key: str | None, legiscan_key: str | None,
    user_id: str, db,
) -> str:
    """Execute a tool call and return the result as a JSON string."""
    try:
        if name == "search_federal_bills":
            r = cc.search_bills(args["query"], congress=args.get("congress"), limit=args.get("limit", 10), api_key=congress_key)
            log_api_usage(user_id, "congress")
        elif name == "search_nominations":
            r = cc.search_nominations(congress=args.get("congress"), query=args.get("query"), limit=args.get("limit", 10), api_key=congress_key)
            log_api_usage(user_id, "congress")
        elif name == "search_state_bills":
            r = lc.search_bills(args["query"], state=args["state"], year=args.get("year", 2), api_key=legiscan_key)
            log_api_usage(user_id, "legiscan")
        elif name == "get_federal_bill":
            r = cc.get_bill(args["congress"], args["bill_type"], args["bill_number"], api_key=congress_key)
            log_api_usage(user_id, "congress")
        elif name == "search_treaties":
            r = cc.search_treaties(congress=args.get("congress"), limit=args.get("limit", 10), api_key=congress_key)
            log_api_usage(user_id, "congress")
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
                "You have access to real-time legislative data via tools. "
                "Always cite bill numbers and sources. Be concise and factual."
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
            result = _dispatch_tool(tc.function.name, args, congress_key, legiscan_key, user_id, db)
            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      result,
            })

    return {"role": "assistant", "content": "I reached the maximum number of tool calls. Please try a more specific question."}
