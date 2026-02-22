"""
keys.py — API key vault: store, retrieve (masked), and delete per-user API keys.
Plaintext keys are encrypted at rest using crypto.py and never returned to the client.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_db
from app.crypto import encrypt_key, decrypt_key

router = APIRouter()

VALID_PROVIDERS = {"legiscan", "congress", "anthropic", "openai", "google", "groq", "mistral"}


class KeyIn(BaseModel):
    key: str


class KeyStatus(BaseModel):
    provider:  str
    stored:    bool
    masked:    str | None = None  # e.g. "sk-...abc" — last 4 chars shown


# ---------------------------------------------------------------------------
# List all stored providers (no plaintext)
# ---------------------------------------------------------------------------
@router.get("", summary="List stored API key providers")
def list_keys(user=Depends(get_current_user)):
    db = get_db()
    rows = (
        db.table("user_keys")
        .select("provider, key_enc")
        .eq("user_id", user["user_id"])
        .execute()
    )
    result = []
    for row in (rows.data or []):
        plaintext = decrypt_key(row["key_enc"])
        masked = plaintext[:4] + "..." + plaintext[-4:] if len(plaintext) > 8 else "****"
        result.append(KeyStatus(provider=row["provider"], stored=True, masked=masked))
    return result


# ---------------------------------------------------------------------------
# Store or update a key
# ---------------------------------------------------------------------------
@router.post("/{provider}", status_code=status.HTTP_204_NO_CONTENT, summary="Save an API key")
def save_key(provider: str, body: KeyIn, user=Depends(get_current_user)):
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")
    if not body.key.strip():
        raise HTTPException(status_code=400, detail="Key cannot be empty")

    encrypted = encrypt_key(body.key.strip())
    db = get_db()
    db.table("user_keys").upsert({
        "user_id":  user["user_id"],
        "provider": provider,
        "key_enc":  encrypted,
    }, on_conflict="user_id,provider").execute()


# ---------------------------------------------------------------------------
# Delete a key
# ---------------------------------------------------------------------------
@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an API key")
def delete_key(provider: str, user=Depends(get_current_user)):
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")
    db = get_db()
    db.table("user_keys").delete().eq("user_id", user["user_id"]).eq("provider", provider).execute()


# ---------------------------------------------------------------------------
# Helper used internally by other routers — not exposed as HTTP endpoint
# ---------------------------------------------------------------------------
def get_user_key(user_id: str, provider: str) -> str | None:
    """Retrieve and decrypt a user's API key for a given provider. Returns None if not stored."""
    db = get_db()
    rows = (
        db.table("user_keys")
        .select("key_enc")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .execute()
    )
    if not rows.data:
        return None
    return decrypt_key(rows.data[0]["key_enc"])
