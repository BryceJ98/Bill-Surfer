"""
search.py — Search bills, nominations, and treaties using the user's own API keys.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user
from app.routers.keys import get_user_key
from app.tools import congress_client as cc
from app.tools import legiscan_client as lc

router = APIRouter()


def _require_key(user_id: str, provider: str) -> str:
    key = get_user_key(user_id, provider)
    if not key:
        raise HTTPException(
            status_code=402,
            detail=f"No {provider} API key stored. Add it in Settings.",
        )
    return key


# ---------------------------------------------------------------------------
# Federal: bills
# ---------------------------------------------------------------------------
@router.get("/federal/bills", summary="Search federal bills (Congress.gov)")
def search_federal_bills(
    q:        str  = Query(..., description="Search keywords"),
    congress: int  = Query(None, description="Congress number (default: current)"),
    limit:    int  = Query(20,   ge=1, le=250),
    user      = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "congress")
    result = cc.search_bills(q, congress=congress, limit=limit, api_key=api_key)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# Federal: nominations
# ---------------------------------------------------------------------------
@router.get("/federal/nominations", summary="Search presidential nominations")
def search_nominations(
    q:        str | None = Query(None),
    congress: int        = Query(None),
    limit:    int        = Query(20, ge=1, le=250),
    user      = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "congress")
    result = cc.search_nominations(congress=congress, query=q, limit=limit, api_key=api_key)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# Federal: treaties
# ---------------------------------------------------------------------------
@router.get("/federal/treaties", summary="Search Senate treaties")
def search_treaties(
    congress: int = Query(None),
    limit:    int = Query(20, ge=1, le=250),
    user      = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "congress")
    result = cc.search_treaties(congress=congress, limit=limit, api_key=api_key)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# State: bills via LegiScan
# ---------------------------------------------------------------------------
@router.get("/state/bills", summary="Search state bills (LegiScan)")
def search_state_bills(
    q:     str       = Query(...),
    state: str       = Query(..., min_length=2, max_length=2),
    year:  int       = Query(None),
    limit: int       = Query(20, ge=1, le=50),
    user   = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "legiscan")
    result = lc.search_bills(q, state=state.upper(), year=year or 2, api_key=api_key)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    bills = (result.get("bills") or result) if isinstance(result, dict) else result
    return {"bills": bills[:limit], "query": q, "state": state.upper()}


# ---------------------------------------------------------------------------
# Bill detail
# ---------------------------------------------------------------------------
@router.get("/federal/bill", summary="Get federal bill detail")
def get_federal_bill(
    congress:    int = Query(...),
    bill_type:   str = Query(...),
    bill_number: int = Query(...),
    user         = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "congress")
    result = cc.get_bill(congress, bill_type, bill_number, api_key=api_key)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/state/bill", summary="Get state bill detail (LegiScan)")
def get_state_bill(
    bill_id: int = Query(...),
    user     = Depends(get_current_user),
):
    api_key = _require_key(user["user_id"], "legiscan")
    result = lc.get_bill(bill_id, api_key=api_key)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result
