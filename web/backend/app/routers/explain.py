"""
explain.py — Plain-English bill explanation using the user's configured AI model.
Optionally enriches with CRS summaries and cosponsor data from Congress.gov.
"""

import json
import re

import litellm
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_db, log_api_usage
from app.routers.keys import get_user_key
from app.tools import congress_client as cc

router = APIRouter()


_SYSTEM = """\
You are a nonpartisan legislative expert who explains bills in plain English for ordinary citizens.
When given a bill, produce a JSON object with these exact keys:
  "summary"        : 2-3 clear sentences explaining what the bill does (no jargon, no legalese)
  "key_points"     : list of 3-5 specific, concrete things the bill would change or do
  "who_is_affected": plain-English description of who would be most affected
  "current_status" : the bill's current progress in plain terms (e.g. "Passed the House, awaiting Senate vote")
  "notes"          : any important context about support/opposition, or an empty string

Rules:
- Never take political sides; focus on what the bill actually does
- Use simple language a 10th-grader could understand
- Output ONLY the JSON object, no markdown fences, no commentary
"""


class ExplainRequest(BaseModel):
    title:          str
    state:          str              # "US" for federal, or two-letter state code
    bill_number:    str | None = None
    bill_id:        str | None = None
    summary_text:   str | None = None  # pre-fetched CRS or LegiScan summary
    status:         str | None = None
    # For fetching richer federal data on the fly:
    congress:       int | None = None
    bill_type:      str | None = None
    bill_number_int: int | None = None


@router.post("", summary="Explain a bill in plain English using AI")
def explain_bill(body: ExplainRequest, user=Depends(get_current_user)):
    db      = get_db()
    user_id = user["user_id"]

    s = db.table("user_settings").select("ai_provider, ai_model").eq("user_id", user_id).execute()
    if not s.data:
        raise HTTPException(status_code=400, detail="Configure your AI provider in Settings first.")

    ai_provider = s.data[0]["ai_provider"]
    ai_model    = s.data[0]["ai_model"]
    ai_key      = get_user_key(user_id, ai_provider)
    if not ai_key:
        raise HTTPException(status_code=402, detail=f"No {ai_provider} API key stored.")

    congress_key = get_user_key(user_id, "congress")

    # ---------------------------------------------------------------------------
    # Build rich context for the AI
    # ---------------------------------------------------------------------------
    ctx_parts = [
        f"Bill: {body.bill_number or body.bill_id or 'Unknown'}",
        f"Jurisdiction: {'Federal (U.S. Congress)' if body.state == 'US' else body.state}",
        f"Title: {body.title}",
    ]
    if body.status:
        ctx_parts.append(f"Status: {body.status}")

    # Fetch CRS summary + cosponsor count for federal bills
    if body.state == "US" and body.congress and body.bill_type and body.bill_number_int and congress_key:
        try:
            summaries = cc.get_bill_summaries(
                body.congress, body.bill_type, body.bill_number_int, api_key=congress_key
            )
            if summaries.get("latest"):
                ctx_parts.append(f"\nOfficial CRS Summary:\n{summaries['latest'][:3000]}")
            log_api_usage(user_id, "congress")
        except Exception:
            pass

        try:
            cosponsors = cc.get_bill_cosponsors(
                body.congress, body.bill_type, body.bill_number_int, api_key=congress_key
            )
            count = cosponsors.get("count", 0)
            if count:
                ctx_parts.append(f"Cosponsors: {count}")
            log_api_usage(user_id, "congress")
        except Exception:
            pass

    # Use any pre-fetched summary the client sent
    if body.summary_text and "CRS Summary" not in " ".join(ctx_parts):
        ctx_parts.append(f"\nSummary:\n{body.summary_text[:2000]}")

    bill_context = "\n".join(ctx_parts)

    # ---------------------------------------------------------------------------
    # Call AI
    # ---------------------------------------------------------------------------
    prompt = (
        "Please explain the following bill in plain English.\n\n"
        f"{bill_context}\n\n"
        "Respond with ONLY a JSON object (no markdown, no code block)."
    )

    try:
        resp = litellm.completion(
            model=ai_model,
            api_key=ai_key,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            timeout=45,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI error: {exc}")

    usage = getattr(resp, "usage", None)
    total_tokens = getattr(usage, "total_tokens", 0) or 0
    if total_tokens:
        log_api_usage(user_id, ai_provider, calls=0, tokens=total_tokens)

    raw = (resp.choices[0].message.content if resp.choices else "") or ""

    # Robustly extract JSON — strip markdown fences if present
    json_str = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()
    # Find the first { ... } block
    m = re.search(r"\{.*\}", json_str, re.DOTALL)
    if m:
        json_str = m.group(0)

    try:
        result = json.loads(json_str)
    except Exception:
        result = {
            "summary":         raw,
            "key_points":      [],
            "who_is_affected": "",
            "current_status":  body.status or "",
            "notes":           "",
        }

    return result
