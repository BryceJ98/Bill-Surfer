"""
db.py — Supabase client (service-role, server-side only)
"""

import os
from supabase import create_client, Client

_client: Client | None = None


def get_db() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        _client = create_client(url, key)
    return _client


def get_user_memory(user_id: str) -> tuple[bool, str]:
    """Return (memory_enabled, summary). Never raises."""
    try:
        db = get_db()
        s = db.table("user_settings").select("memory_enabled").eq("user_id", user_id).execute()
        enabled = bool(s.data and s.data[0].get("memory_enabled"))
        if not enabled:
            return False, ""
        m = db.table("user_memory").select("summary").eq("user_id", user_id).execute()
        summary = (m.data[0]["summary"] if m.data else "") or ""
        return True, summary
    except Exception:
        return False, ""


def memory_system_prefix(user_id: str) -> str:
    """Returns a formatted memory block to prepend to system prompts, or empty string."""
    enabled, summary = get_user_memory(user_id)
    if not enabled or not summary.strip():
        return ""
    return f"[USER MEMORY FROM PREVIOUS SESSIONS]\n{summary}\n\n"


def log_api_usage(user_id: str, provider: str, calls: int = 1, tokens: int = 0) -> None:
    """Best-effort usage logging. Never raises, never blocks the calling request."""
    try:
        from datetime import date
        get_db().rpc("increment_api_usage", {
            "p_user_id": user_id,
            "p_provider": provider,
            "p_month":    date.today().strftime("%Y-%m"),
            "p_calls":    calls,
            "p_tokens":   tokens,
        }).execute()
    except Exception:
        pass
