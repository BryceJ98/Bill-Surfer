"""
settings.py — User profile/settings and usage stats (for the scoreboard).
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_db

router = APIRouter()


class SettingsUpdate(BaseModel):
    display_name:    str | None = None
    institution:     str | None = None
    research_areas:  list[str] | None = None
    ai_provider:     str | None = None
    ai_model:        str | None = None


AI_MODELS = {
    "anthropic": ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"],
    "openai":    ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "google":    [
        "gemini/gemini-2.0-flash",
        "gemini/gemini-2.0-flash-lite",
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash",
    ],
    "groq":      ["groq/llama-3.3-70b-versatile", "groq/llama-3.1-70b-versatile", "groq/llama-3.1-8b-instant"],
    "mistral":   ["mistral/mistral-large-latest", "mistral/mistral-small-latest"],
}


@router.get("", summary="Get user settings")
def get_settings(user=Depends(get_current_user)):
    db = get_db()
    rows = db.table("user_settings").select("*").eq("user_id", user["user_id"]).execute()
    if not rows.data:
        # Auto-create defaults
        db.table("user_settings").insert({"user_id": user["user_id"]}).execute()
        return {"user_id": user["user_id"], "ai_provider": "anthropic", "ai_model": "claude-sonnet-4-6"}
    return rows.data[0]


@router.patch("", summary="Update user settings")
def update_settings(body: SettingsUpdate, user=Depends(get_current_user)):
    db = get_db()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Validate ai_provider and ai_model when provided
    if "ai_provider" in updates and updates["ai_provider"] not in AI_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown AI provider: {updates['ai_provider']}")
    if "ai_model" in updates and "ai_provider" in updates:
        allowed = AI_MODELS.get(updates["ai_provider"], [])
        if updates["ai_model"] not in allowed:
            raise HTTPException(status_code=400, detail=f"Unknown model '{updates['ai_model']}' for provider '{updates['ai_provider']}'")

    db.table("user_settings").upsert(
        {"user_id": user["user_id"], **updates},
        on_conflict="user_id"
    ).execute()
    return {"updated": True}


@router.get("/ai-models", summary="List available AI models by provider")
def get_ai_models():
    return AI_MODELS


# ---------------------------------------------------------------------------
# Scoreboard — daily stats shown at the top of the dashboard
# ---------------------------------------------------------------------------
@router.get("/scoreboard", summary="Get today's usage scoreboard")
def get_scoreboard(user=Depends(get_current_user)):
    db      = get_db()
    user_id = user["user_id"]
    today   = date.today().isoformat()

    # Bills in docket
    docket = db.table("docket").select("id", count="exact").eq("user_id", user_id).execute()
    docket_count = docket.count or 0

    # Reports generated
    reports = db.table("reports").select("id", count="exact").eq("user_id", user_id).execute()
    reports_total = reports.count or 0

    # Reports today
    reports_today = (
        db.table("reports")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", f"{today}T00:00:00")
        .execute()
    )
    reports_today_count = reports_today.count or 0

    # Active AI model
    settings = db.table("user_settings").select("ai_model, ai_provider").eq("user_id", user_id).execute()
    ai_model    = settings.data[0]["ai_model"]    if settings.data else "—"
    ai_provider = settings.data[0]["ai_provider"] if settings.data else "—"

    # API usage this month
    this_month = date.today().strftime("%Y-%m")
    usage_rows = (
        db.table("api_usage")
        .select("provider, call_count, token_count")
        .eq("user_id", user_id)
        .eq("month", this_month)
        .execute()
    )

    return {
        "docket_count":        docket_count,
        "reports_total":       reports_total,
        "reports_today":       reports_today_count,
        "ai_model":            ai_model,
        "ai_provider":         ai_provider,
        "date":                today,
        "usage":               usage_rows.data or [],
    }
