"""
import_csv.py — BYOD (Bring Your Own Data) CSV upload and analysis endpoints.

Named import_csv (not import) because `import` is a Python reserved keyword.

Endpoints:
  POST /import/csv          — parse upload, detect mode (bill vs generic)
  POST /import/docket-bulk  — batch upsert rows into docket table
  POST /import/landscape    — AI legislative landscape for bill CSVs
  POST /import/stats        — AI stats table + abstract + insights for generic CSVs
  GET  /import/template     — download example bill CSV (no auth)
"""

import csv
import io
import json
import re

import litellm
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_db, log_api_usage, memory_system_prefix
from app.routers.keys import get_user_key
from app.routers.memory import fire_memory_update

router = APIRouter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_FILE_BYTES       = 2 * 1024 * 1024   # 2 MB
MAX_ROWS             = 1000
PREVIEW_ROWS         = 100
AI_CONTEXT_CHARS     = 15_000

BILL_KEYWORDS = {
    "bill_id", "bill_number", "bill_no", "billnumber", "billid",
    "state", "title", "status", "sponsor", "congress",
    "introduced", "enacted", "passed", "chamber",
}
BILL_KEYWORD_THRESHOLD = 2   # ≥2 matching headers → bill mode

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class BulkDocketRow(BaseModel):
    bill_id:     str
    bill_number: str | None = None
    state:       str
    title:       str | None = None
    notes:       str | None = None
    tags:        list[str] = []


class BulkDocketRequest(BaseModel):
    rows: list[BulkDocketRow]


class LandscapeRequest(BaseModel):
    raw_csv:   str
    row_count: int
    columns:   list[str]


class StatsRequest(BaseModel):
    raw_csv:   str
    row_count: int
    columns:   list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalize_header(h: str) -> str:
    """Lowercase + strip non-alphanumeric."""
    return re.sub(r"[^a-z0-9]", "", h.lower())


def _detect_bill_mode(headers: list[str]) -> bool:
    normalized = {_normalize_header(h) for h in headers}
    matches = normalized & BILL_KEYWORDS
    return len(matches) >= BILL_KEYWORD_THRESHOLD


def _parse_csv_bytes(content: bytes) -> tuple[list[str], list[dict], str]:
    """Decode bytes, parse CSV, return (headers, rows, raw_csv_str)."""
    # Try UTF-8 with BOM first (Excel), fall back to latin-1
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    rows: list[dict] = []
    for i, row in enumerate(reader):
        if i >= MAX_ROWS:
            break
        rows.append(dict(row))

    raw_csv = text[:AI_CONTEXT_CHARS]
    return headers, rows, raw_csv


# ---------------------------------------------------------------------------
# AI helper: get user AI settings and key
# ---------------------------------------------------------------------------
def _get_ai_settings(user_id: str):
    db = get_db()
    s = db.table("user_settings").select("ai_provider, ai_model").eq("user_id", user_id).execute()
    if not s.data:
        raise HTTPException(status_code=400, detail="Configure your AI provider in Settings first.")
    ai_provider = s.data[0]["ai_provider"]
    ai_model    = s.data[0]["ai_model"]
    ai_key      = get_user_key(user_id, ai_provider)
    if not ai_key:
        raise HTTPException(status_code=402, detail=f"No {ai_provider} API key stored.")
    return ai_provider, ai_model, ai_key


# ---------------------------------------------------------------------------
# Endpoint 1: Parse and detect CSV
# ---------------------------------------------------------------------------
@router.post("/csv", summary="Parse CSV upload and detect bill vs generic mode")
async def parse_csv(file: UploadFile, user=Depends(get_current_user)):
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Max 2 MB.")

    try:
        headers, rows, raw_csv = _parse_csv_bytes(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {exc}")

    if not headers:
        raise HTTPException(status_code=422, detail="CSV has no headers.")

    mode = "bill" if _detect_bill_mode(headers) else "generic"

    return {
        "mode":      mode,
        "columns":   headers,
        "row_count": len(rows),
        "rows":      rows[:PREVIEW_ROWS],
        "raw_csv":   raw_csv,
    }


# ---------------------------------------------------------------------------
# Endpoint 2: Bulk docket upsert
# ---------------------------------------------------------------------------
@router.post("/docket-bulk", summary="Batch upsert CSV rows into docket")
def docket_bulk(body: BulkDocketRequest, user=Depends(get_current_user)):
    db      = get_db()
    user_id = user["user_id"]

    imported = 0
    skipped  = 0
    errors: list[str] = []

    for row in body.rows:
        record = {
            "user_id":     user_id,
            "bill_id":     row.bill_id,
            "bill_number": row.bill_number,
            "state":       row.state.upper() if row.state else "",
            "title":       row.title,
            "notes":       row.notes,
            "tags":        row.tags,
        }
        try:
            db.table("docket").upsert(record, on_conflict="user_id,bill_id").execute()
            imported += 1
        except Exception as exc:
            err_str = str(exc).lower()
            if "unique" in err_str or "duplicate" in err_str or "conflict" in err_str:
                skipped += 1
            else:
                errors.append(f"{row.bill_id}: {exc}")

    return {"imported": imported, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------------
# Endpoint 3: AI landscape for bill CSV
# ---------------------------------------------------------------------------
_LANDSCAPE_SYSTEM = """\
You are a nonpartisan legislative analyst. A researcher has uploaded a CSV dataset of legislative bills.
Analyze the provided bill data and write a 2-4 paragraph landscape summary covering:
1. What policy areas or themes dominate the dataset
2. Geographic or jurisdictional patterns (if state data is present)
3. Status patterns — what proportion seems active, passed, or stalled
4. Any notable sponsors, trends, or outliers

Be factual, balanced, and concise. Do not take political sides.
"""


@router.post("/landscape", summary="AI landscape analysis of bill CSV data")
def landscape(body: LandscapeRequest, user=Depends(get_current_user)):
    user_id                      = user["user_id"]
    ai_provider, ai_model, ai_key = _get_ai_settings(user_id)

    mem_prefix = memory_system_prefix(user_id)

    context = (
        f"Dataset: {body.row_count} rows, columns: {', '.join(body.columns)}\n\n"
        f"CSV DATA (first {AI_CONTEXT_CHARS} chars):\n{body.raw_csv}"
    )

    try:
        resp = litellm.completion(
            model=ai_model,
            api_key=ai_key,
            messages=[
                {"role": "system", "content": mem_prefix + _LANDSCAPE_SYSTEM},
                {"role": "user",   "content": f"Analyze this bill dataset:\n\n{context}"},
            ],
            timeout=60,
        )
        usage = getattr(resp, "usage", None)
        total_tokens = getattr(usage, "total_tokens", 0) or 0
        if total_tokens:
            log_api_usage(user_id, ai_provider, calls=0, tokens=total_tokens)
        ai_summary = (resp.choices[0].message.content if resp.choices else "") or ""
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI error: {exc}")

    fire_memory_update(
        user_id, ai_provider, ai_model, ai_key,
        f"Ran AI landscape on bill CSV: {body.row_count} rows, columns: {', '.join(body.columns[:6])}",
    )

    return {"ai_summary": ai_summary}


# ---------------------------------------------------------------------------
# Endpoint 4: AI stats for generic CSV
# ---------------------------------------------------------------------------
_STATS_SYSTEM = """\
You are a data analysis assistant. A user has uploaded a generic CSV dataset.
Analyze it and produce a JSON object with exactly these keys:
  "abstract"    : 2-3 sentence plain-English description of what this dataset contains
  "stats_table" : list of objects {metric, value} — 5-10 interesting statistics about the data
  "insights"    : list of 3-5 plain-English insight strings

Output ONLY the JSON object, no markdown fences, no commentary.
"""


@router.post("/stats", summary="AI stats table and insights for generic CSV")
def stats(body: StatsRequest, user=Depends(get_current_user)):
    user_id                      = user["user_id"]
    ai_provider, ai_model, ai_key = _get_ai_settings(user_id)

    mem_prefix = memory_system_prefix(user_id)

    context = (
        f"Dataset: {body.row_count} rows, columns: {', '.join(body.columns)}\n\n"
        f"CSV DATA (first {AI_CONTEXT_CHARS} chars):\n{body.raw_csv}"
    )

    try:
        resp = litellm.completion(
            model=ai_model,
            api_key=ai_key,
            messages=[
                {"role": "system", "content": mem_prefix + _STATS_SYSTEM},
                {"role": "user",   "content": f"Analyze this dataset:\n\n{context}"},
            ],
            timeout=60,
        )
        usage = getattr(resp, "usage", None)
        total_tokens = getattr(usage, "total_tokens", 0) or 0
        if total_tokens:
            log_api_usage(user_id, ai_provider, calls=0, tokens=total_tokens)
        raw = (resp.choices[0].message.content if resp.choices else "") or ""
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI error: {exc}")

    fire_memory_update(
        user_id, ai_provider, ai_model, ai_key,
        f"Ran AI stats on generic CSV: {body.row_count} rows, columns: {', '.join(body.columns[:6])}",
    )

    # Robustly extract JSON (mirrors explain.py pattern)
    json_str = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", json_str, re.DOTALL)
    if m:
        json_str = m.group(0)

    try:
        result = json.loads(json_str)
    except Exception:
        result = {
            "abstract":    raw,
            "stats_table": [],
            "insights":    [],
        }

    return result


# ---------------------------------------------------------------------------
# Endpoint 5: Template download (no auth)
# ---------------------------------------------------------------------------
_TEMPLATE_CSV = """\
bill_id,bill_number,state,title,status,sponsor,notes,tags
HB-2024-001,HB 001,CA,Clean Energy Transition Act,Introduced,Smith J.,Priority bill,"energy,environment"
SB-2024-042,SB 042,TX,School Safety Funding Act,Passed Committee,Johnson R.,Watch closely,"education,safety"
HR-118-1234,HR 1234,US,Federal Infrastructure Investment Act,Passed House,Williams D.,Federal match available,"infrastructure,federal"
"""


@router.get("/template", summary="Download example bill CSV template (no auth required)")
def download_template():
    return StreamingResponse(
        io.BytesIO(_TEMPLATE_CSV.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="bill_surfer_template.csv"'},
    )
