"""
report_generator.py — AI-powered policy report generator.

Flow:
  1. Fetch bill data using user's API keys (congress_client or legiscan_client)
  2. Call the user's chosen AI model via LiteLLM with a structured prompt
  3. Parse the AI's JSON response into report sections
  4. Render a formatted PDF with ReportLab
  5. Return the PDF bytes + the structured JSON content
"""

import sys
import json
import io
from pathlib import Path
from datetime import date

import litellm
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)

# Legislative tools
_tools_path = Path(__file__).resolve().parents[3] / "legislative-assistant" / "tools"
if str(_tools_path) not in sys.path:
    sys.path.insert(0, str(_tools_path))

import congress_client as cc
import legiscan_client as lc

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
NAVY      = colors.HexColor("#1a3a5c")
BLUE      = colors.HexColor("#2c5f8a")
ROW_LIGHT = colors.HexColor("#f0f4f8")
ROW_WHITE = colors.white
GRN_BG    = colors.HexColor("#d4edda")
YLW_BG    = colors.HexColor("#fff3cd")
RED_BG    = colors.HexColor("#f8d7da")
GRN_TXT   = colors.HexColor("#155724")
YLW_TXT   = colors.HexColor("#856404")
RED_TXT   = colors.HexColor("#721c24")

# ---------------------------------------------------------------------------
# PDF styles
# ---------------------------------------------------------------------------
def _make_styles() -> dict:
    s = {}
    s["title"]      = ParagraphStyle("T",  fontSize=22, leading=28, textColor=NAVY, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=6)
    s["subtitle"]   = ParagraphStyle("ST", fontSize=13, leading=16, textColor=BLUE, alignment=TA_CENTER, fontName="Helvetica", spaceAfter=4)
    s["meta"]       = ParagraphStyle("M",  fontSize=10, leading=13, textColor=colors.HexColor("#555555"), alignment=TA_CENTER, fontName="Helvetica-Oblique", spaceAfter=2)
    s["section"]    = ParagraphStyle("S",  fontSize=14, leading=18, textColor=NAVY, spaceBefore=14, spaceAfter=2, fontName="Helvetica-Bold")
    s["subsection"] = ParagraphStyle("SS", fontSize=11, leading=14, textColor=BLUE, spaceBefore=8, spaceAfter=2, fontName="Helvetica-Bold")
    s["body"]       = ParagraphStyle("B",  fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=6, fontName="Helvetica")
    s["bullet"]     = ParagraphStyle("BL", fontSize=10, leading=14, leftIndent=18, spaceAfter=4, fontName="Helvetica")
    s["footer"]     = ParagraphStyle("F",  fontSize=8,  leading=10, textColor=colors.HexColor("#888888"), alignment=TA_CENTER, fontName="Helvetica-Oblique")
    s["tbl_hdr"]    = ParagraphStyle("TH", fontSize=9,  leading=11, textColor=colors.white, fontName="Helvetica-Bold", alignment=TA_CENTER)
    s["tbl_cell"]   = ParagraphStyle("TC", fontSize=9,  leading=12, fontName="Helvetica")
    return s

ST = _make_styles()


def _hr():
    return HRFlowable(width="100%", thickness=1.2, color=NAVY, spaceAfter=6, spaceBefore=2)


def _section(text: str) -> list:
    return [Paragraph(text, ST["section"]), _hr()]


def _alt_table(header: list, rows: list, col_widths: list, wrap_cols: list | None = None) -> Table:
    wrap_cols = wrap_cols or []
    rendered_header = [Paragraph(str(c), ST["tbl_hdr"]) for c in header]
    rendered_rows = [rendered_header]
    for row in rows:
        rendered_rows.append([
            Paragraph(str(cell), ST["tbl_cell"]) if i in wrap_cols else str(cell)
            for i, cell in enumerate(row)
        ])
    style = [
        ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  9),
        ("ROWBACKGROUND", (0, 1), (-1, -1), [ROW_WHITE, ROW_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
    ]
    return Table(rendered_rows, colWidths=col_widths, style=style, repeatRows=1)


# ---------------------------------------------------------------------------
# Step 1: Fetch bill data
# ---------------------------------------------------------------------------
def _fetch_bill_data(
    bill_id: str,
    state: str,
    congress_api_key: str | None,
    legiscan_api_key: str | None,
) -> dict:
    """Fetch bill metadata, text summary, and vote data."""
    data: dict = {"bill_id": bill_id, "state": state}

    if state.upper() == "US":
        # Federal bill — parse bill_id like "us-hr-1234" or congress_client format
        parts = bill_id.lower().replace("us-", "").split("-")
        if len(parts) >= 2:
            bill_type, bill_number = parts[0], int(parts[-1])
            congress = cc.current_congress()
            if congress_api_key:
                bill = cc.get_bill(congress, bill_type, bill_number, api_key=congress_api_key)
                data["bill"] = bill
                summaries = cc.get_bill_summaries(congress, bill_type, bill_number, api_key=congress_api_key)
                data["summary"] = summaries.get("latest", "")
                actions = cc.get_bill_actions(congress, bill_type, bill_number, api_key=congress_api_key)
                data["actions"] = actions.get("actions", [])
    else:
        # State bill via LegiScan
        if legiscan_api_key:
            try:
                bill_int = int(bill_id)
                bill = lc.get_bill(bill_int, api_key=legiscan_api_key)
                data["bill"] = bill
                # Get vote summaries
                roll_calls = bill.get("votes", [])
                data["votes"] = roll_calls
            except (ValueError, Exception):
                pass

    return data


# ---------------------------------------------------------------------------
# Step 2: Generate report content via AI
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are a nonpartisan policy analyst generating a structured policy impact report.
Return ONLY valid JSON matching this exact schema — no markdown, no extra text:

{
  "executive_summary": "2-4 sentence overview",
  "key_provisions": [
    {"title": "Section name", "text": "What this provision does"}
  ],
  "stakeholders": [
    {"group": "Who is affected", "impact": "How they are affected", "severity": "positive|neutral|negative"}
  ],
  "fiscal_impact": "Plain-English fiscal analysis (2-3 sentences)",
  "policy_concerns": [
    {"title": "Concern name", "text": "Description of the concern"}
  ],
  "scorecard": [
    {"dimension": "Policy area", "rating": "Strong|Mixed|Weak", "notes": "1 sentence", "color": "green|yellow|red"}
  ],
  "recommendations": [
    {"title": "Short recommendation title", "text": "Detailed recommendation"}
  ],
  "methodology": "Brief note on data sources used"
}"""


def _call_ai(
    bill_data: dict,
    ai_provider: str,
    ai_model: str,
    ai_api_key: str,
    report_type: str = "policy_impact",
) -> dict:
    """Call the user's AI model and return structured report JSON."""
    bill_info = json.dumps(bill_data, default=str, indent=2)
    user_msg = (
        f"Generate a {report_type} report for this bill. "
        f"Use only the data provided.\n\nBill Data:\n{bill_info[:8000]}"
    )

    try:
        response = litellm.completion(
            model=ai_model,
            api_key=ai_api_key,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=4096,
        )
        raw = response.choices[0].message.content.strip()
        # Strip any accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI returned invalid JSON: {exc}")
    except Exception as exc:
        raise ValueError(f"AI call failed: {exc}")


# ---------------------------------------------------------------------------
# Step 3: Render PDF
# ---------------------------------------------------------------------------
def _render_pdf(content: dict, bill_info: dict) -> bytes:
    """Render the AI-generated structured content to a PDF. Returns PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        topMargin=0.85 * inch,  bottomMargin=0.85 * inch,
        title=bill_info.get("title", "Policy Impact Report"),
        author="Bill-Surfer / AI",
    )

    story = []
    W = 6.8 * inch
    bill_label  = bill_info.get("bill_number", bill_info.get("bill_id", ""))
    bill_state  = bill_info.get("state", "")
    bill_title  = bill_info.get("title", "")
    report_type = bill_info.get("report_type", "Policy Impact Report").replace("_", " ").title()

    # ── Cover ─────────────────────────────────────────────────────────────────
    story += [
        Spacer(1, 0.4 * inch),
        Paragraph("POLICY IMPACT REPORT", ST["subtitle"]),
        Spacer(1, 0.1 * inch),
        Paragraph(f"{bill_state} {bill_label}", ST["title"]),
        Spacer(1, 0.08 * inch),
        Paragraph(bill_title[:120] if bill_title else report_type, ST["subtitle"]),
        HRFlowable(width="60%", thickness=2, color=BLUE, spaceAfter=10, spaceBefore=10),
        Paragraph(f"Report Date: {date.today().strftime('%B %d, %Y')}  |  Powered by Bill-Surfer", ST["meta"]),
        Spacer(1, 0.5 * inch),
        PageBreak(),
    ]

    # ── Executive Summary ─────────────────────────────────────────────────────
    story += _section("1. Executive Summary")
    story.append(Paragraph(content.get("executive_summary", ""), ST["body"]))

    # ── Key Provisions ────────────────────────────────────────────────────────
    story += _section("2. Key Provisions")
    for i, prov in enumerate(content.get("key_provisions", []), 1):
        story.append(Paragraph(f"{i}. {prov.get('title', '')}", ST["subsection"]))
        story.append(Paragraph(prov.get("text", ""), ST["body"]))

    # ── Stakeholder Impact ────────────────────────────────────────────────────
    stakeholders = content.get("stakeholders", [])
    if stakeholders:
        story += _section("3. Stakeholder Impact")
        rows = [[s.get("group",""), s.get("impact",""), s.get("severity","").title()] for s in stakeholders]
        story.append(_alt_table(
            ["Group", "Impact", "Severity"], rows,
            [1.8*inch, 3.6*inch, 1.4*inch], wrap_cols=[0, 1]
        ))

    # ── Fiscal Impact ─────────────────────────────────────────────────────────
    story += _section("4. Fiscal Impact")
    story.append(Paragraph(content.get("fiscal_impact", "No fiscal analysis available."), ST["body"]))

    # ── Policy Concerns ───────────────────────────────────────────────────────
    story.append(PageBreak())
    story += _section("5. Policy Concerns")
    for i, concern in enumerate(content.get("policy_concerns", []), 1):
        story.append(Paragraph(f"{i}. {concern.get('title', '')}", ST["subsection"]))
        story.append(Paragraph(concern.get("text", ""), ST["body"]))

    # ── Scorecard ─────────────────────────────────────────────────────────────
    story += _section("6. Policy Scorecard")
    color_map = {
        "green":  (GRN_BG, GRN_TXT),
        "yellow": (YLW_BG, YLW_TXT),
        "red":    (RED_BG, RED_TXT),
    }
    scorecard = content.get("scorecard", [])
    if scorecard:
        sc_header = [Paragraph(h, ST["tbl_hdr"]) for h in ["Dimension", "Rating", "Notes"]]
        sc_rows   = [sc_header]
        sc_style  = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING",   (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ]
        for i, item in enumerate(scorecard, 1):
            ck     = item.get("color", "yellow")
            bg, fg = color_map.get(ck, (YLW_BG, YLW_TXT))
            sc_rows.append([
                Paragraph(item.get("dimension", ""), ST["tbl_cell"]),
                Paragraph(f"<b>{item.get('rating','')}</b>",
                          ParagraphStyle("sc", fontSize=9, textColor=fg, fontName="Helvetica-Bold")),
                Paragraph(item.get("notes", ""), ST["tbl_cell"]),
            ])
            sc_style.append(("BACKGROUND", (1, i), (1, i), bg))
        story.append(Table(sc_rows, colWidths=[2.2*inch, 1.2*inch, 3.4*inch], style=sc_style, repeatRows=1))

    # ── Recommendations ───────────────────────────────────────────────────────
    story += _section("7. Recommendations")
    for i, rec in enumerate(content.get("recommendations", []), 1):
        story.append(Paragraph(f"{i}. {rec.get('title', '')}", ST["subsection"]))
        story.append(Paragraph(rec.get("text", ""), ST["body"]))

    # ── Footer ────────────────────────────────────────────────────────────────
    story += [
        Spacer(1, 0.3 * inch),
        HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=6),
        Paragraph(
            f"Generated {date.today().strftime('%B %d, %Y')}  |  Bill-Surfer  |  "
            f"Data: Congress.gov / LegiScan  |  AI-assisted analysis",
            ST["footer"],
        ),
    ]

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def generate_report(
    bill_id:          str,
    bill_number:      str,
    state:            str,
    title:            str,
    report_type:      str,
    ai_provider:      str,
    ai_model:         str,
    ai_api_key:       str,
    congress_api_key: str | None = None,
    legiscan_api_key: str | None = None,
) -> tuple[dict, bytes]:
    """
    Generate a policy impact report for a bill.

    Returns:
        (content_json: dict, pdf_bytes: bytes)
    """
    # 1. Fetch bill data
    bill_data = _fetch_bill_data(bill_id, state, congress_api_key, legiscan_api_key)
    bill_data["title"] = title
    bill_data["bill_number"] = bill_number

    # 2. AI-generated content
    content = _call_ai(bill_data, ai_provider, ai_model, ai_api_key, report_type)

    # 3. Render PDF
    bill_info = {
        "bill_id":     bill_id,
        "bill_number": bill_number,
        "state":       state,
        "title":       title,
        "report_type": report_type,
    }
    pdf_bytes = _render_pdf(content, bill_info)

    return content, pdf_bytes
