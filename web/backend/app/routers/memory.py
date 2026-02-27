"""
memory.py — Per-user AI memory: opt-in persistent context injected across all AI calls.

The memory is a ≤150-word natural-language profile maintained by the AI itself.
After each AI interaction it is updated in a background thread — never blocking the main response.

Endpoints:
  GET    /memory   — fetch current memory summary
  DELETE /memory   — clear memory summary
"""

import threading
from datetime import datetime

import litellm
from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.db import get_db, get_user_memory

router = APIRouter()

_UPDATE_PROMPT = """\
You maintain a persistent memory profile for a legislative researcher.
Given their current memory and their latest interaction, rewrite the memory profile.

Rules:
- ≤150 words
- Focus on: research topics, states of interest, tools used, policy areas, observable preferences
- Factual, no fluff, no filler phrases like "The user..."
- Write in compact note form: "Tracks CA education bills. Prefers Claude. Imported 3 CSVs..."
- Preserve valuable older context; replace stale or redundant entries

Output ONLY the updated memory text. No preamble, no markdown.
"""


# ---------------------------------------------------------------------------
# Background update helper (called from other routers, not an endpoint)
# ---------------------------------------------------------------------------
def fire_memory_update(
    user_id:     str,
    ai_provider: str,
    ai_model:    str,
    ai_key:      str,
    interaction: str,
) -> None:
    """Spawn a daemon thread to update user memory. Never blocks the caller."""
    thread = threading.Thread(
        target=_do_memory_update,
        args=(user_id, ai_provider, ai_model, ai_key, interaction),
        daemon=True,
    )
    thread.start()


def _do_memory_update(
    user_id:     str,
    ai_provider: str,
    ai_model:    str,
    ai_key:      str,
    interaction: str,
) -> None:
    """Actual update logic — runs in background thread."""
    try:
        db = get_db()

        # Re-check opt-in (user may have disabled since the call started)
        enabled, current = get_user_memory(user_id)
        if not enabled:
            return

        prompt = (
            f"CURRENT MEMORY:\n{current or '(empty)'}\n\n"
            f"LATEST INTERACTION:\n{interaction}"
        )

        resp = litellm.completion(
            model=ai_model,
            api_key=ai_key,
            messages=[
                {"role": "system", "content": _UPDATE_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            timeout=30,
        )
        new_summary = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        if not new_summary:
            return

        db.table("user_memory").upsert(
            {
                "user_id":    user_id,
                "summary":    new_summary,
                "updated_at": datetime.utcnow().isoformat(),
            },
            on_conflict="user_id",
        ).execute()
    except Exception:
        pass  # best-effort; never surface errors to user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("", summary="Get current AI memory summary")
def get_memory(user=Depends(get_current_user)):
    db      = get_db()
    user_id = user["user_id"]

    s = db.table("user_settings").select("memory_enabled").eq("user_id", user_id).execute()
    enabled = bool(s.data and s.data[0].get("memory_enabled"))

    m = db.table("user_memory").select("summary, updated_at").eq("user_id", user_id).execute()
    if m.data:
        return {"enabled": enabled, "summary": m.data[0]["summary"], "updated_at": m.data[0]["updated_at"]}
    return {"enabled": enabled, "summary": "", "updated_at": None}


@router.delete("", summary="Clear AI memory summary")
def clear_memory(user=Depends(get_current_user)):
    db = get_db()
    db.table("user_memory").delete().eq("user_id", user["user_id"]).execute()
    return {"cleared": True}
