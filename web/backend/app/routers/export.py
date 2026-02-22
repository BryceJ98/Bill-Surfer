"""
export.py — CSV export endpoint, wrapping csv_export.py with per-user API keys.
"""

import io
import csv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import get_current_user
from app.routers.keys import get_user_key
from app.tools import congress_client as cc
from app.tools import legiscan_client as lc

router = APIRouter()

VALID_TYPES = ["nominations", "treaties", "federal-bills", "state-bills", "members"]


class ExportRequest(BaseModel):
    export_type:  str             # nominations | treaties | federal-bills | state-bills | members
    query:        str | None = None
    state:        str | None = None
    congress:     int | None = None
    year:         int | None = None
    limit:        int = 250


@router.post("/csv", summary="Export data to CSV")
def export_csv(body: ExportRequest, user=Depends(get_current_user)):
    if body.export_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid export type. Use: {', '.join(VALID_TYPES)}")

    user_id = user["user_id"]
    congress_key = get_user_key(user_id, "congress")
    legiscan_key = get_user_key(user_id, "legiscan")
    rows: list[dict] = []

    if body.export_type == "nominations":
        if not congress_key:
            raise HTTPException(status_code=402, detail="Congress API key required")
        result = cc.search_nominations(
            congress=body.congress or cc.current_congress(),
            query=body.query, limit=body.limit,
            api_key=congress_key,
        )
        rows = result.get("nominations", [])

    elif body.export_type == "treaties":
        if not congress_key:
            raise HTTPException(status_code=402, detail="Congress API key required")
        result = cc.search_treaties(
            congress=body.congress or cc.current_congress(),
            limit=body.limit, api_key=congress_key,
        )
        rows = result.get("treaties", [])

    elif body.export_type == "federal-bills":
        if not congress_key:
            raise HTTPException(status_code=402, detail="Congress API key required")
        result = cc.search_bills(
            body.query or "",
            congress=body.congress or cc.current_congress(),
            limit=body.limit, api_key=congress_key,
        )
        rows = result.get("bills", [])

    elif body.export_type == "state-bills":
        if not legiscan_key:
            raise HTTPException(status_code=402, detail="LegiScan API key required")
        if not body.state:
            raise HTTPException(status_code=400, detail="state is required for state-bills export")
        result = lc.search_bills(
            body.query or "", state=body.state.upper(),
            year=body.year or 2, api_key=legiscan_key,
        )
        raw = result.get("bills") or result if isinstance(result, dict) else result
        rows = raw[:body.limit] if isinstance(raw, list) else []

    elif body.export_type == "members":
        if not congress_key:
            raise HTTPException(status_code=402, detail="Congress API key required")
        result = cc.get_members_by_congress(
            congress=body.congress or cc.current_congress(),
            limit=body.limit, api_key=congress_key,
        )
        rows = result.get("members", [])

    if not rows:
        raise HTTPException(status_code=404, detail="No data found for these parameters")

    # Serialize to CSV
    output = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else []
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: (";".join(v) if isinstance(v, list) else v) for k, v in row.items()})

    filename = f"{body.export_type}_export.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
