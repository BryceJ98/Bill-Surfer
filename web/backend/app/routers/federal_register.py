"""
federal_register.py — Federal Register API endpoints.

Endpoints:
  GET /federal-register/digest?date=YYYY-MM-DD  — today's top regulatory actions w/ RBS scores
  GET /federal-register/search?q=keyword         — keyword search across FR documents
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user
from app.tools import federal_register_client as fr

router = APIRouter()


@router.get("/digest", summary="Daily Federal Register digest with Regulatory Burden Scores")
def daily_digest(
    date: str | None = Query(default=None, description="YYYY-MM-DD, defaults to today"),
    limit: int       = Query(default=10,   ge=1, le=50),
    user=Depends(get_current_user),
):
    try:
        docs = fr.get_daily_digest(date=date, limit=limit)
        return {
            "date":      date or "today",
            "count":     len(docs),
            "documents": docs,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Federal Register API error: {exc}")


@router.get("/search", summary="Search Federal Register documents by keyword")
def search(
    q:          str            = Query(..., description="Search keyword"),
    doc_types:  list[str]      = Query(default=["RULE", "PRORULE", "PRESDOCU"]),
    limit:      int            = Query(default=10, ge=1, le=50),
    user=Depends(get_current_user),
):
    try:
        docs = fr.search_documents(keyword=q, doc_types=doc_types, limit=limit)
        return {
            "query":     q,
            "count":     len(docs),
            "documents": docs,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Federal Register API error: {exc}")
