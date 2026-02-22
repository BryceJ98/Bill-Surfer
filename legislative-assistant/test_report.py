"""
test_report.py
--------------
Modern PDF policy impact report generator for any bill.
Uses legiscan_client.py for API access and generates clean, professional reports.

Usage:
    python test_report.py <bill_id>
    python test_report.py 1423040

Requires: pip install reportlab
"""

import sys
from datetime import date
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

# Import shared LegiScan client
import legiscan_client as lc


# ── MODERN COLOR PALETTE ─────────────────────────────────────────────────────
PRIMARY_NAVY   = colors.HexColor("#0F172A")    # Deep slate for authority
SECONDARY_BLUE = colors.HexColor("#1E40AF")    # Rich blue for headings
ACTION_MINT    = colors.HexColor("#10B981")    # Modern green for progress/success
NEUTRAL_GRAY   = colors.HexColor("#F8FAFC")    # Clean background
BORDER_GRAY    = colors.HexColor("#E2E8F0")    # Subtle dividers
TEXT_DARK      = colors.HexColor("#1E293B")    # Primary text
TEXT_MUTED     = colors.HexColor("#64748B")    # Secondary text

# Scorecard colors
GRN_BG  = colors.HexColor("#D1FAE5")
GRN_TXT = colors.HexColor("#065F46")
YLW_BG  = colors.HexColor("#FEF3C7")
YLW_TXT = colors.HexColor("#92400E")
RED_BG  = colors.HexColor("#FEE2E2")
RED_TXT = colors.HexColor("#991B1B")

ROW_LIGHT = colors.HexColor("#F8FAFC")
ROW_WHITE = colors.white


# ── STYLES ───────────────────────────────────────────────────────────────────
def make_styles():
    """Create custom paragraph styles for the report."""
    s = {}
    s["title"] = ParagraphStyle(
        "ReportTitle", fontSize=24, leading=30, textColor=PRIMARY_NAVY,
        alignment=TA_CENTER, spaceAfter=6, fontName="Helvetica-Bold"
    )
    s["subtitle"] = ParagraphStyle(
        "ReportSubtitle", fontSize=13, leading=16, textColor=SECONDARY_BLUE,
        alignment=TA_CENTER, spaceAfter=4, fontName="Helvetica"
    )
    s["meta"] = ParagraphStyle(
        "Meta", fontSize=10, leading=13, textColor=TEXT_MUTED,
        alignment=TA_CENTER, spaceAfter=2, fontName="Helvetica-Oblique"
    )
    s["section"] = ParagraphStyle(
        "Section", fontSize=14, leading=18, textColor=PRIMARY_NAVY,
        spaceBefore=14, spaceAfter=4, fontName="Helvetica-Bold"
    )
    s["subsection"] = ParagraphStyle(
        "Subsection", fontSize=11, leading=14, textColor=SECONDARY_BLUE,
        spaceBefore=10, spaceAfter=2, fontName="Helvetica-Bold"
    )
    s["body"] = ParagraphStyle(
        "Body", fontSize=10, leading=14, alignment=TA_JUSTIFY,
        spaceAfter=6, fontName="Helvetica", textColor=TEXT_DARK
    )
    s["quote"] = ParagraphStyle(
        "Quote", fontSize=9, leading=13, alignment=TA_JUSTIFY,
        spaceAfter=6, fontName="Helvetica-Oblique",
        leftIndent=18, rightIndent=18, textColor=TEXT_MUTED
    )
    s["center"] = ParagraphStyle(
        "Center", fontSize=10, leading=14, alignment=TA_CENTER,
        fontName="Helvetica"
    )
    s["footer"] = ParagraphStyle(
        "Footer", fontSize=8, leading=10, textColor=TEXT_MUTED,
        alignment=TA_CENTER, fontName="Helvetica-Oblique"
    )
    s["tbl_hdr"] = ParagraphStyle(
        "TblHdr", fontSize=9, leading=11, textColor=colors.white,
        fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    s["tbl_cell"] = ParagraphStyle(
        "TblCell", fontSize=9, leading=12, fontName="Helvetica"
    )
    return s


ST = make_styles()


# ── VISUAL COMPONENTS ────────────────────────────────────────────────────────

def hr():
    """Horizontal rule for section separation."""
    return HRFlowable(width="100%", thickness=1.5, color=PRIMARY_NAVY, spaceAfter=8, spaceBefore=2)


def section_heading(text):
    """Section heading with underline."""
    return [Paragraph(text, ST["section"]), hr()]


def get_status_stepper(status_code):
    """
    Convert status code to a visual progress indicator.
    LegiScan status codes: 1=Intro, 2=Engrossed, 3=Enrolled, 4=Passed, 5=Vetoed, 6=Failed
    """
    steps = ["Introduced", "Engrossed", "Enrolled", "Passed"]

    # Map status code to step index
    status_map = {1: 0, 2: 1, 3: 2, 4: 3, 5: 3, 6: 0, 7: 3, 8: 3}
    status_idx = status_map.get(status_code, 0)

    display_steps = []
    for i, step in enumerate(steps):
        if i < status_idx:
            # Completed step
            display_steps.append(f"<font color='#10B981'><b>+ {step}</b></font>")
        elif i == status_idx:
            # Current step
            display_steps.append(f"<font color='#1E40AF'><b>* {step}</b></font>")
        else:
            # Future step
            display_steps.append(f"<font color='#94A3B8'>o {step}</font>")

    return "   &rarr;   ".join(display_steps)


def create_tldr_box(description):
    """Create a high-contrast callout box for the report summary."""
    content = f"<b>THE QUICK TAKE</b><br/><br/>{description}"
    data = [[Paragraph(content, ST["body"])]]
    tldr_table = Table(data, colWidths=[6.3*inch])
    tldr_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NEUTRAL_GRAY),
        ('LEFTPADDING', (0,0), (-1,-1), 15),
        ('RIGHTPADDING', (0,0), (-1,-1), 15),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('LINEABOVE', (0,0), (-1,0), 4, ACTION_MINT),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_GRAY),
    ]))
    return tldr_table


def alternating_table(header_row, data_rows, col_widths, wrap_cols=None):
    """Create a table with alternating row colors."""
    wrap_cols = wrap_cols or []
    header = [Paragraph(str(c), ST["tbl_hdr"]) for c in header_row]
    rows = [header]

    for row in data_rows:
        rendered = []
        for i, cell in enumerate(row):
            if i in wrap_cols:
                rendered.append(Paragraph(str(cell), ST["tbl_cell"]))
            else:
                rendered.append(str(cell))
        rows.append(rendered)

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [ROW_WHITE, ROW_LIGHT]),
        ("GRID",       (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("FONTSIZE",   (0, 1), (-1, -1), 9),
    ]
    return Table(rows, colWidths=col_widths, style=style, repeatRows=1)


def scorecard_row(dimension, rating, notes, color_key):
    """Create a scorecard row with colored rating cell."""
    color_map = {
        "green": (GRN_BG, GRN_TXT),
        "yellow": (YLW_BG, YLW_TXT),
        "red": (RED_BG, RED_TXT)
    }
    bg, fg = color_map.get(color_key, (ROW_LIGHT, TEXT_DARK))
    return (dimension, rating, notes, bg, fg)


# ── REPORT GENERATOR ─────────────────────────────────────────────────────────

def generate_report(bill_id: int, output_path: str = None):
    """
    Generate a comprehensive PDF policy report for a bill.

    Args:
        bill_id: LegiScan bill ID
        output_path: Optional output file path. Defaults to {bill_number}_Report.pdf

    Returns:
        Path to generated PDF file, or None on error.
    """
    # Fetch bill data
    bill_data = lc.get_bill(bill_id)
    if not bill_data or "error" in bill_data:
        print(f"Error: Could not fetch bill {bill_id}")
        print(bill_data.get("error", "Unknown error"))
        return None

    # Extract key fields
    bill_number = bill_data.get("bill_number", f"Bill_{bill_id}")
    state = bill_data.get("state", "US")
    title = bill_data.get("title", "Untitled Bill")
    description = bill_data.get("description", title)
    status_code = bill_data.get("status", 1)
    status_text = lc.status_label(status_code)
    session = bill_data.get("session", {})
    session_name = session.get("session_name", "") if isinstance(session, dict) else ""

    # Sponsors
    sponsors = bill_data.get("sponsors", [])
    primary_sponsor = sponsors[0].get("name", "Unknown") if sponsors else "Unknown"
    sponsor_party = sponsors[0].get("party", "") if sponsors else ""

    # Texts (versions)
    texts = bill_data.get("texts", [])
    version_count = len(texts)
    v1_size = texts[0].get("text_size", 0) if texts else 0
    latest_size = texts[-1].get("text_size", 0) if texts else 0

    # Votes
    votes = bill_data.get("votes", [])

    # History
    history = bill_data.get("history", [])
    last_action = bill_data.get("last_action", "No action recorded")
    last_action_date = bill_data.get("last_action_date", "")

    # URL
    legiscan_url = bill_data.get("url", "")

    # Output path
    if not output_path:
        safe_number = bill_number.replace(" ", "_").replace("/", "-")
        output_path = f"{state}_{safe_number}_Report.pdf"

    # Setup document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        title=f"{state} {bill_number} Policy Impact Report",
        author="Legislative Assistant / LegiScan"
    )

    story = []

    # ── COVER / HEADER ───────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("POLICY IMPACT REPORT", ST["subtitle"]))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(f"{state} {bill_number}", ST["title"]))
    story.append(Spacer(1, 0.05*inch))

    # Truncate title if too long
    display_title = title[:100] + "..." if len(title) > 100 else title
    story.append(Paragraph(display_title, ST["subtitle"]))

    story.append(HRFlowable(width="50%", thickness=2, color=SECONDARY_BLUE, spaceAfter=12, spaceBefore=12))

    # Metadata line
    meta_parts = [f"State: {state}"]
    if session_name:
        meta_parts.append(f"Session: {session_name}")
    meta_parts.append(f"Status: {status_text}")
    story.append(Paragraph("  |  ".join(meta_parts), ST["meta"]))

    # Sponsor and date
    sponsor_text = f"Sponsor: {primary_sponsor}"
    if sponsor_party:
        sponsor_text += f" ({sponsor_party})"
    sponsor_text += f"  |  Report Date: {date.today().strftime('%B %d, %Y')}"
    story.append(Paragraph(sponsor_text, ST["meta"]))

    story.append(Spacer(1, 0.2*inch))

    # Status stepper
    story.append(Paragraph(get_status_stepper(status_code), ST["center"]))
    story.append(Spacer(1, 0.3*inch))

    # TL;DR Box
    story.append(create_tldr_box(description))
    story.append(Spacer(1, 0.3*inch))

    # ── LEGISLATIVE EVOLUTION ────────────────────────────────────────────────
    story += section_heading("1. Legislative Evolution")

    if version_count > 0:
        if version_count == 1:
            evolution_msg = (
                f"This bill has <b>1 text version</b> on record, totaling "
                f"{latest_size:,} characters."
            )
        else:
            growth = ((latest_size - v1_size) / v1_size * 100) if v1_size > 0 else 0
            evolution_msg = (
                f"This bill has evolved through <b>{version_count} versions</b>, "
                f"growing from {v1_size:,} characters to {latest_size:,} characters "
                f"in the current draft"
            )
            if growth > 0:
                evolution_msg += f" (<b>+{growth:.0f}%</b> expansion)."
            else:
                evolution_msg += "."
        story.append(Paragraph(evolution_msg, ST["body"]))

    # Version table
    if texts:
        version_data = [["Version", "Type", "Date", "Size"]]
        for i, t in enumerate(texts, 1):
            version_data.append([
                f"v{i}",
                t.get("type", "Unknown"),
                t.get("date", "-"),
                f"{t.get('text_size', 0):,} chars"
            ])
        story.append(Spacer(1, 0.1*inch))
        story.append(alternating_table(
            version_data[0], version_data[1:],
            col_widths=[0.6*inch, 2.0*inch, 1.2*inch, 1.0*inch],
            wrap_cols=[1]
        ))

    story.append(Spacer(1, 0.15*inch))

    # ── RECENT ACTIVITY ──────────────────────────────────────────────────────
    story += section_heading("2. Recent Activity")

    story.append(Paragraph(f"<b>Last Action:</b> {last_action_date} - {last_action}", ST["body"]))

    if history:
        story.append(Paragraph("2.1 Action Timeline", ST["subsection"]))
        # Show last 10 history items
        recent_history = history[-10:] if len(history) > 10 else history
        recent_history.reverse()  # Most recent first

        history_data = [["Date", "Chamber", "Action"]]
        for h in recent_history:
            history_data.append([
                h.get("date", "-"),
                h.get("chamber", "-"),
                h.get("action", "-")[:80]
            ])
        story.append(alternating_table(
            history_data[0], history_data[1:],
            col_widths=[1.0*inch, 0.8*inch, 5.0*inch],
            wrap_cols=[2]
        ))

    # ── VOTES ────────────────────────────────────────────────────────────────
    if votes:
        story.append(Spacer(1, 0.15*inch))
        story += section_heading("3. Roll Call Votes")

        vote_data = [["Date", "Chamber", "Description", "Yea", "Nay", "Result"]]
        for v in votes:
            passed = "PASSED" if v.get("passed", 0) == 1 else "FAILED"
            vote_data.append([
                v.get("date", "-"),
                v.get("chamber", "-"),
                v.get("desc", "-")[:50],
                str(v.get("yea", 0)),
                str(v.get("nay", 0)),
                passed
            ])
        story.append(alternating_table(
            vote_data[0], vote_data[1:],
            col_widths=[0.9*inch, 0.7*inch, 2.8*inch, 0.5*inch, 0.5*inch, 0.8*inch],
            wrap_cols=[2]
        ))

    # ── SPONSORS ─────────────────────────────────────────────────────────────
    if sponsors:
        story.append(Spacer(1, 0.15*inch))
        story += section_heading("4. Sponsors")

        sponsor_data = [["Name", "Party", "Role", "District"]]
        for s in sponsors[:10]:  # Limit to 10
            sponsor_data.append([
                s.get("name", "-"),
                s.get("party", "-"),
                "Primary" if s.get("sponsor_type_id") == 1 else "Co-sponsor",
                s.get("district", "-")
            ])
        story.append(alternating_table(
            sponsor_data[0], sponsor_data[1:],
            col_widths=[2.5*inch, 0.8*inch, 1.0*inch, 1.0*inch],
            wrap_cols=[0]
        ))

    # ── FOOTER ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY_BLUE, spaceAfter=8))

    footer_text = (
        f"{state} {bill_number} Policy Impact Report  |  "
        f"Generated {date.today().strftime('%B %d, %Y')}  |  "
        f"Data: LegiScan API  |  Analysis: Legislative Assistant"
    )
    story.append(Paragraph(footer_text, ST["footer"]))

    if legiscan_url:
        story.append(Paragraph(f"LegiScan: {legiscan_url}", ST["footer"]))

    # Build PDF
    doc.build(story)
    print(f"Report saved to: {output_path}")
    return output_path


# Keep legacy function name for backwards compatibility
def generate_automated_report(bill_id):
    """Legacy function name - calls generate_report."""
    return generate_report(bill_id)


# ── CLI ENTRY POINT ──────────────────────────────────────────────────────────

def main():
    """Command-line interface for report generation."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage: python test_report.py <bill_id>")
        print("\nExamples:")
        print("  python test_report.py 1423040")
        print("  python test_report.py 1856789")
        sys.exit(1)

    try:
        bill_id = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid bill ID (must be an integer)")
        sys.exit(1)

    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    result = generate_report(bill_id, output_path)

    if result:
        print(f"Success: Report generated at {result}")
    else:
        print("Failed to generate report.")
        sys.exit(1)


if __name__ == "__main__":
    main()
