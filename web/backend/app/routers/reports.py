"""
reports.py — Generate and retrieve policy reports.
PDFs are stored in Supabase Storage under reports/{user_id}/{report_id}.pdf
"""

import io
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_db, log_api_usage
from app.routers.keys import get_user_key

router = APIRouter()


class ReportRequest(BaseModel):
    bill_id:     str
    bill_number: str
    state:       str
    title:       str
    report_type: str = "policy_impact"  # policy_impact | summary | vote_analysis | comparison


# ---------------------------------------------------------------------------
# Generate a new report (async via background task)
# ---------------------------------------------------------------------------
@router.post("", status_code=status.HTTP_202_ACCEPTED, summary="Request a new report")
def create_report(
    body:               ReportRequest,
    background_tasks:   BackgroundTasks,
    user                = Depends(get_current_user),
):
    db      = get_db()
    user_id = user["user_id"]

    # Verify user has an AI key + at least one data key
    settings = db.table("user_settings").select("ai_provider, ai_model").eq("user_id", user_id).execute()
    if not settings.data:
        raise HTTPException(status_code=400, detail="Complete your AI settings first")

    ai_provider = settings.data[0]["ai_provider"]
    ai_model    = settings.data[0]["ai_model"]
    ai_key      = get_user_key(user_id, ai_provider)
    if not ai_key:
        raise HTTPException(status_code=402, detail=f"No {ai_provider} API key stored")

    # Insert report row with status=generating
    result = db.table("reports").insert({
        "user_id":     user_id,
        "bill_id":     body.bill_id,
        "bill_number": body.bill_number,
        "state":       body.state.upper(),
        "title":       body.title,
        "report_type": body.report_type,
        "ai_provider": ai_provider,
        "ai_model":    ai_model,
        "status":      "generating",
    }).execute()

    report_id = result.data[0]["id"]

    # Run generation in background
    background_tasks.add_task(
        _run_report_generation,
        report_id, user_id,
        body.bill_id, body.bill_number, body.state, body.title, body.report_type,
        ai_provider, ai_model, ai_key,
        get_user_key(user_id, "congress"),
        get_user_key(user_id, "legiscan"),
    )

    return {"report_id": report_id, "status": "generating"}


def _run_report_generation(
    report_id, user_id,
    bill_id, bill_number, state, title, report_type,
    ai_provider, ai_model, ai_key,
    congress_key, legiscan_key,
):
    """Background task: generate report, upload PDF, update DB row."""
    from app.report_generator import generate_report
    db = get_db()
    try:
        content_json, pdf_bytes, total_tokens = generate_report(
            bill_id=bill_id, bill_number=bill_number, state=state,
            title=title, report_type=report_type,
            ai_provider=ai_provider, ai_model=ai_model, ai_api_key=ai_key,
            congress_api_key=congress_key, legiscan_api_key=legiscan_key,
        )
        if total_tokens:
            log_api_usage(user_id, ai_provider, calls=0, tokens=total_tokens)

        # Upload PDF to Supabase Storage
        pdf_path = f"{user_id}/{report_id}.pdf"
        db.storage.from_("reports").upload(
            pdf_path, pdf_bytes, {"content-type": "application/pdf"}
        )

        db.table("reports").update({
            "status":           "complete",
            "content_json":     content_json,
            "pdf_storage_path": pdf_path,
        }).eq("id", report_id).execute()

    except Exception as exc:
        db.table("reports").update({
            "status":        "error",
            "error_message": str(exc)[:500],
        }).eq("id", report_id).execute()


# ---------------------------------------------------------------------------
# List reports
# ---------------------------------------------------------------------------
@router.get("", summary="List user's report library")
def list_reports(user=Depends(get_current_user)):
    db = get_db()
    rows = (
        db.table("reports")
        .select("id, bill_id, bill_number, state, title, report_type, ai_model, status, is_public, created_at, error_message")
        .eq("user_id", user["user_id"])
        .order("created_at", desc=True)
        .execute()
    )
    return rows.data or []


# ---------------------------------------------------------------------------
# Get report detail (JSON content)
# ---------------------------------------------------------------------------
@router.get("/{report_id}", summary="Get report content (JSON)")
def get_report(report_id: str, user=Depends(get_current_user)):
    db = get_db()
    rows = (
        db.table("reports")
        .select("*")
        .eq("id", report_id)
        .execute()
    )
    if not rows.data:
        raise HTTPException(status_code=404, detail="Report not found")

    report = rows.data[0]
    # Allow access if owner or public
    if report["user_id"] != user["user_id"] and not report["is_public"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return report


# ---------------------------------------------------------------------------
# Download PDF
# ---------------------------------------------------------------------------
@router.get("/{report_id}/pdf", summary="Download report PDF")
def download_report_pdf(report_id: str, user=Depends(get_current_user)):
    db = get_db()
    rows = db.table("reports").select("user_id, pdf_storage_path, status, bill_number, state, is_public").eq("id", report_id).execute()
    if not rows.data:
        raise HTTPException(status_code=404, detail="Report not found")

    report = rows.data[0]
    if report["user_id"] != user["user_id"] and not report["is_public"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if report["status"] != "complete":
        raise HTTPException(status_code=409, detail=f"Report is not ready (status: {report['status']})")

    path = report["pdf_storage_path"]
    pdf_bytes = db.storage.from_("reports").download(path)
    filename = f"{report['state']}_{report['bill_number']}_report.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Toggle public / delete
# ---------------------------------------------------------------------------
@router.patch("/{report_id}/visibility", summary="Toggle report public visibility")
def set_visibility(report_id: str, is_public: bool, user=Depends(get_current_user)):
    db = get_db()
    db.table("reports").update({"is_public": is_public}).eq("id", report_id).eq("user_id", user["user_id"]).execute()
    return {"report_id": report_id, "is_public": is_public}


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a report")
def delete_report(report_id: str, user=Depends(get_current_user)):
    db = get_db()
    rows = db.table("reports").select("pdf_storage_path").eq("id", report_id).eq("user_id", user["user_id"]).execute()
    if rows.data and rows.data[0].get("pdf_storage_path"):
        try:
            db.storage.from_("reports").remove([rows.data[0]["pdf_storage_path"]])
        except Exception:
            pass
    db.table("reports").delete().eq("id", report_id).eq("user_id", user["user_id"]).execute()
