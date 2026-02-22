"""
docket.py — Personal bill docket CRUD for each user.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_db

router = APIRouter()


class DocketItemIn(BaseModel):
    bill_id:     str
    bill_number: str | None = None
    state:       str
    title:       str | None = None
    stance:      str | None = None   # support | oppose | neutral | watching
    priority:    str | None = None   # high | medium | low
    notes:       str | None = None
    tags:        list[str] = []


class DocketItemUpdate(BaseModel):
    stance:   str | None = None
    priority: str | None = None
    notes:    str | None = None
    tags:     list[str] | None = None
    title:    str | None = None


# ---------------------------------------------------------------------------
# List docket
# ---------------------------------------------------------------------------
@router.get("", summary="List all docket items")
def list_docket(user=Depends(get_current_user)):
    db = get_db()
    rows = (
        db.table("docket")
        .select("*")
        .eq("user_id", user["user_id"])
        .order("added_date", desc=True)
        .execute()
    )
    return rows.data or []


# ---------------------------------------------------------------------------
# Add to docket
# ---------------------------------------------------------------------------
@router.post("", status_code=status.HTTP_201_CREATED, summary="Add a bill to docket")
def add_to_docket(body: DocketItemIn, user=Depends(get_current_user)):
    db = get_db()
    row = {
        "user_id":     user["user_id"],
        "bill_id":     body.bill_id,
        "bill_number": body.bill_number,
        "state":       body.state.upper(),
        "title":       body.title,
        "stance":      body.stance,
        "priority":    body.priority,
        "notes":       body.notes,
        "tags":        body.tags,
    }
    try:
        result = db.table("docket").insert(row).execute()
        return result.data[0]
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Bill already in docket")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Update a docket item
# ---------------------------------------------------------------------------
@router.patch("/{item_id}", summary="Update stance, notes, tags, or priority")
def update_docket(item_id: str, body: DocketItemUpdate, user=Depends(get_current_user)):
    db = get_db()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = (
        db.table("docket")
        .update(updates)
        .eq("id", item_id)
        .eq("user_id", user["user_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Docket item not found")
    return result.data[0]


# ---------------------------------------------------------------------------
# Remove from docket
# ---------------------------------------------------------------------------
@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove from docket")
def remove_from_docket(item_id: str, user=Depends(get_current_user)):
    db = get_db()
    db.table("docket").delete().eq("id", item_id).eq("user_id", user["user_id"]).execute()
