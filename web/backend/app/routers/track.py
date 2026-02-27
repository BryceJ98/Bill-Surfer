"""
track.py — Topic tracking: search bills + CRS research reports + congressional record
across federal and state sources, with AI-powered legislative landscape summary.

Exposes previously unused Congress.gov API surface:
  - search_crs_reports()      — nonpartisan CRS research reports by topic
  - get_crs_report()          — full CRS report detail
  - get_bill_cosponsors()     — cosponsor counts (signals political traction)
  - search_congressional_record_by_keyword() — floor speeches on topic
"""

import litellm
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_db, log_api_usage, memory_system_prefix, personality_system_prefix
from app.routers.keys import get_user_key
from app.routers.memory import fire_memory_update
from app.tools import congress_client as cc
from app.tools import legiscan_client as lc

router = APIRouter()


_TRACK_SYSTEM = """\
You are a nonpartisan legislative tracking expert. A researcher has asked you to summarize
the current legislative landscape on a policy topic.

Write 2-4 paragraphs covering:
1. What major federal legislation exists or is pending on this topic
2. What state-level trends or patterns are visible (if state data provided)
3. What's actively moving vs. stalled
4. Key context: how many cosponsors, whether CRS has weighed in, etc.

Be factual, balanced, and concise. Mention specific bills by name/number where relevant.
Do not take political sides.
"""


class TrackRequest(BaseModel):
    topic:           str
    state:           str | None = None   # optional state for state-level bills
    congress:        int | None = None   # specific Congress, or None for current
    include_crs:     bool = True         # include CRS research reports
    include_record:  bool = False        # include congressional record (slower)


@router.post("", summary="Track legislation on a policy topic with AI analysis")
def track_topic(body: TrackRequest, user=Depends(get_current_user)):
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
    legiscan_key = get_user_key(user_id, "legiscan")

    # ---------------------------------------------------------------------------
    # 1. Federal bills (LegiScan getSearch for real full-text keyword relevance)
    # ---------------------------------------------------------------------------
    federal_bills: list[dict] = []
    if legiscan_key:
        try:
            r = lc.search_bills(body.topic, state="US", year=2, api_key=legiscan_key)
            bills_raw = r.get("bills", []) if isinstance(r, dict) else []
            federal_bills = [
                {
                    "bill_label": b.get("bill_number", ""),
                    "title":      b.get("title", ""),
                    "status":     b.get("last_action", ""),
                    "status_date": b.get("last_action_date", ""),
                    "state":      "US",
                    "url":        b.get("url", ""),
                    "bill_id":    str(b.get("bill_id", "")),
                }
                for b in bills_raw[:20]
            ]
            log_api_usage(user_id, "legiscan")
        except Exception:
            pass

    # ---------------------------------------------------------------------------
    # 2. CRS research reports (nonpartisan background research) — NEW API SURFACE
    # ---------------------------------------------------------------------------
    crs_reports: list[dict] = []
    if congress_key and body.include_crs:
        try:
            r = cc.search_crs_reports(body.topic, limit=5, api_key=congress_key)
            crs_reports = r.get("reports", r) if isinstance(r, dict) else r
            if not isinstance(crs_reports, list):
                crs_reports = []
            # Enrich top CRS report with full detail
            if crs_reports:
                top = crs_reports[0]
                report_id = top.get("reportNumber") or top.get("id")
                if report_id:
                    try:
                        detail = cc.get_crs_report(report_id, api_key=congress_key)
                        top["detail"] = detail
                    except Exception:
                        pass
            log_api_usage(user_id, "congress", calls=len(crs_reports) + 1)
        except Exception:
            pass

    # ---------------------------------------------------------------------------
    # 3. Congressional Record floor speeches — NEW API SURFACE (optional, slower)
    # ---------------------------------------------------------------------------
    record_items: list[dict] = []
    if congress_key and body.include_record:
        try:
            r = cc.search_congressional_record_by_keyword(body.topic, limit=5, api_key=congress_key)
            record_items = r.get("items", r) if isinstance(r, dict) else r
            if not isinstance(record_items, list):
                record_items = []
            log_api_usage(user_id, "congress")
        except Exception:
            pass

    # ---------------------------------------------------------------------------
    # 4. State bills via LegiScan
    # ---------------------------------------------------------------------------
    state_bills: list[dict] = []
    if body.state and legiscan_key:
        try:
            r = lc.search_bills(body.topic, state=body.state.upper(), year=2, api_key=legiscan_key)
            bills_data = r.get("bills", r) if isinstance(r, dict) else r
            state_bills = bills_data[:20] if isinstance(bills_data, list) else []
            log_api_usage(user_id, "legiscan")
        except Exception:
            pass

    # ---------------------------------------------------------------------------
    # 5. AI legislative landscape summary
    # ---------------------------------------------------------------------------
    context_lines = [f"Policy Topic: {body.topic}\n"]

    if federal_bills:
        context_lines.append(f"FEDERAL BILLS ({len(federal_bills)} found):")
        for b in federal_bills[:12]:
            label  = b.get("bill_label", b.get("number", ""))
            title  = b.get("title", "")
            status = b.get("status", "")
            context_lines.append(f"  • {label}: {title[:120]} [{status}]")

    if crs_reports:
        context_lines.append(f"\nCRS RESEARCH REPORTS ({len(crs_reports)} found):")
        for r in crs_reports[:3]:
            context_lines.append(f"  • {r.get('title', '')} ({r.get('date', '')})")

    if state_bills:
        context_lines.append(f"\nSTATE BILLS — {body.state} ({len(state_bills)} found):")
        for b in state_bills[:10]:
            number = b.get("bill_number", "")
            title  = b.get("title", "")
            status = b.get("status", "")
            context_lines.append(f"  • {number}: {title[:120]} [{status}]")

    if record_items:
        context_lines.append(f"\nCONGRESSIONAL RECORD MENTIONS: {len(record_items)} floor speeches/debates found")

    context = "\n".join(context_lines)

    mem_prefix  = memory_system_prefix(user_id)
    pers_prefix = personality_system_prefix(user_id)

    ai_summary = ""
    try:
        resp = litellm.completion(
            model=ai_model,
            api_key=ai_key,
            messages=[
                {"role": "system", "content": pers_prefix + mem_prefix + _TRACK_SYSTEM},
                {"role": "user",   "content": f"Analyze the following legislation on '{body.topic}':\n\n{context}"},
            ],
            timeout=60,
        )
        usage = getattr(resp, "usage", None)
        total_tokens = getattr(usage, "total_tokens", 0) or 0
        if total_tokens:
            log_api_usage(user_id, ai_provider, calls=0, tokens=total_tokens)
        ai_summary = (resp.choices[0].message.content if resp.choices else "") or ""
    except Exception as exc:
        ai_summary = f"AI analysis unavailable: {exc}"

    state_label = f" in {body.state}" if body.state else ""
    fire_memory_update(
        user_id, ai_provider, ai_model, ai_key,
        f"Tracked topic: '{body.topic}'{state_label}. Found {len(federal_bills)} federal, {len(state_bills)} state bills.",
    )

    return {
        "topic":         body.topic,
        "federal_bills": federal_bills,
        "state_bills":   state_bills,
        "crs_reports":   crs_reports,
        "record_items":  record_items,
        "ai_summary":    ai_summary,
        "total_federal": len(federal_bills),
        "total_state":   len(state_bills),
        "total_crs":     len(crs_reports),
    }
