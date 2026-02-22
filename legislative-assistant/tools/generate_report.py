"""
generate_report.py
------------------
Generates a PDF policy impact report for KS SB197 (STAR Bonds Financing Act Expansion).
Based on full statutory text of Senate v3 (K.S.A. 12-17,160 et seq.) and House v5 (current engrossed).
Requires: pip install reportlab
"""

from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable
from datetime import date
import os

# ── Colors ────────────────────────────────────────────────────────────────────
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

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "KS_SB197_Policy_Report.pdf")

# ── Styles ────────────────────────────────────────────────────────────────────
base_styles = getSampleStyleSheet()

def make_styles():
    s = {}
    s["title"] = ParagraphStyle(
        "ReportTitle", fontSize=22, leading=28, textColor=NAVY,
        alignment=TA_CENTER, spaceAfter=6, fontName="Helvetica-Bold"
    )
    s["subtitle"] = ParagraphStyle(
        "ReportSubtitle", fontSize=13, leading=16, textColor=BLUE,
        alignment=TA_CENTER, spaceAfter=4, fontName="Helvetica"
    )
    s["meta"] = ParagraphStyle(
        "Meta", fontSize=10, leading=13, textColor=colors.HexColor("#555555"),
        alignment=TA_CENTER, spaceAfter=2, fontName="Helvetica-Oblique"
    )
    s["section"] = ParagraphStyle(
        "Section", fontSize=14, leading=18, textColor=NAVY,
        spaceBefore=14, spaceAfter=2, fontName="Helvetica-Bold"
    )
    s["subsection"] = ParagraphStyle(
        "Subsection", fontSize=11, leading=14, textColor=BLUE,
        spaceBefore=8, spaceAfter=2, fontName="Helvetica-Bold"
    )
    s["body"] = ParagraphStyle(
        "Body", fontSize=10, leading=14, alignment=TA_JUSTIFY,
        spaceAfter=6, fontName="Helvetica"
    )
    s["quote"] = ParagraphStyle(
        "Quote", fontSize=9, leading=13, alignment=TA_JUSTIFY,
        spaceAfter=6, fontName="Helvetica-Oblique",
        leftIndent=18, rightIndent=18,
        textColor=colors.HexColor("#333333")
    )
    s["footer"] = ParagraphStyle(
        "Footer", fontSize=8, leading=10, textColor=colors.HexColor("#888888"),
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


def hr():
    return HRFlowable(width="100%", thickness=1.2, color=NAVY, spaceAfter=6, spaceBefore=2)


def section_heading(text):
    return [Paragraph(text, ST["section"]), hr()]


def alternating_table(header_row, data_rows, col_widths, wrap_cols=None):
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
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        ("ROWBACKGROUND", (0, 1), (-1, -1), [ROW_WHITE, ROW_LIGHT]),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("FONTSIZE",   (0, 1), (-1, -1), 9),
    ]
    return Table(rows, colWidths=col_widths, style=style, repeatRows=1)


def scorecard_table(items):
    color_map = {"green": (GRN_BG, GRN_TXT), "yellow": (YLW_BG, YLW_TXT), "red": (RED_BG, RED_TXT)}
    header = [Paragraph("Policy Dimension", ST["tbl_hdr"]),
              Paragraph("Rating", ST["tbl_hdr"]),
              Paragraph("Notes", ST["tbl_hdr"])]
    rows = [header]
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("FONTSIZE",   (0, 1), (-1, -1), 9),
    ]
    for i, (dim, rating, notes, ck) in enumerate(items, start=1):
        bg, fg = color_map[ck]
        rows.append([
            Paragraph(dim, ST["tbl_cell"]),
            Paragraph("<b>" + rating + "</b>",
                      ParagraphStyle("sc", fontSize=9, textColor=fg, fontName="Helvetica-Bold")),
            Paragraph(notes, ST["tbl_cell"])
        ])
        style_cmds.append(("BACKGROUND", (1, i), (1, i), bg))
    return Table(rows, colWidths=[2.2*inch, 1.2*inch, 3.6*inch], style=style_cmds, repeatRows=1)


def build_report():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=LETTER,
        leftMargin=0.85*inch,
        rightMargin=0.85*inch,
        topMargin=0.85*inch,
        bottomMargin=0.85*inch,
        title="KS SB197 Policy Impact Report",
        author="Claude AI / LegiScan"
    )

    story = []
    W = 6.8 * inch

    # ── COVER ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4*inch))
    story.append(Paragraph("POLICY IMPACT REPORT", ST["subtitle"]))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Kansas Senate Bill 197", ST["title"]))
    story.append(Spacer(1, 0.08*inch))
    story.append(Paragraph("STAR Bonds Financing Act Expansion", ST["subtitle"]))
    story.append(HRFlowable(width="60%", thickness=2, color=BLUE, spaceAfter=10, spaceBefore=10))
    story.append(Paragraph(
        "State: Kansas (KS)  |  Session: 2025-2026  |  Status: Engrossed / Advancing in House",
        ST["meta"]
    ))
    story.append(Paragraph(
        "Senate Vote: February 19, 2025 (32-8)  |  Report Date: " + date.today().strftime("%B %d, %Y"),
        ST["meta"]
    ))
    story.append(Paragraph(
        "Sponsor: Senate Committee on Commerce, Labor and Economic Development",
        ST["meta"]
    ))
    story.append(Spacer(1, 0.3*inch))

    title_text = (
        "House Substitute for Substitute for SB 197 - An act concerning economic development; "
        "relating to port authorities; providing that a port authority may be authorized by enactment "
        "of a bill and authorizing the establishment of a port authority by the unified government of "
        "Wyandotte County and Kansas City, Kansas; relating to the STAR bonds financing act; authorizing "
        "redevelopment of certain mall facilities as eligible STAR bond projects; authorizing vertical "
        "construction within certain STAR bond project districts; authorizing STAR bond projects in "
        "certain counties in certain MSAs as rural redevelopment projects; setting visitor origin "
        "requirements and enforcement; prohibiting state general fund pledge and eminent domain for "
        "STAR bond projects; extending the STAR bonds financing act to July 1, 2031."
    )
    title_box = Table(
        [[Paragraph(title_text, ParagraphStyle(
            "TitleBox", fontSize=9, leading=13, alignment=TA_JUSTIFY,
            fontName="Helvetica-Oblique", textColor=colors.HexColor("#333333")
        ))]],
        colWidths=[W],
        style=[
            ("BACKGROUND", (0,0), (-1,-1), ROW_LIGHT),
            ("BOX", (0,0), (-1,-1), 0.8, BLUE),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]
    )
    story.append(title_box)
    story.append(PageBreak())

    # ── EXECUTIVE SUMMARY ─────────────────────────────────────────────────────
    story += section_heading("1. Executive Summary")
    story.append(Paragraph(
        "Kansas Senate Bill 197 is a comprehensive expansion of the state's Sales Tax and Revenue "
        "(STAR) Bond financing program. The bill originated as a simple sunset extension (v1, 1,210 "
        "characters) and grew through five successive drafts into a 95,000-character statute touching "
        "six Kansas Statutes Annotated sections. The current engrossed House version (v5) is the "
        "controlling text and differs materially from the Senate-passed version (v3) on several "
        "critical provisions. The Senate passed v3 on February 19, 2025, by a 32-8 margin. The House "
        "Commerce Committee recommended passage of v5 on February 10, 2026; a House floor vote is pending.",
        ST["body"]
    ))
    story.append(Paragraph(
        "The House substitute makes the bill substantially stronger on accountability than the Senate "
        "version. Where the Senate version only required quarterly visitor data collection, the House "
        "version adds hard numeric visitor origin thresholds (30% of visitors from 100+ miles; 20% from "
        "out-of-state) and an enforcement mechanism: developers who fail to meet these thresholds are "
        "barred from participating in any future STAR bond project until compliance is restored. The "
        "House version also adds the port authority mechanism for Wyandotte County/KCK, which was "
        "absent from the Senate text, and extends the sunset from July 1, 2028 to July 1, 2031.",
        ST["body"]
    ))
    story.append(Paragraph(
        "Both versions share two significant taxpayer protections that the original report incorrectly "
        "characterized as gaps: (1) state general fund moneys are explicitly prohibited from being "
        "pledged to repay any special obligation bonds under this act (K.S.A. 12-17,169(a)(6)); and "
        "(2) cities and counties are explicitly prohibited from using eminent domain to acquire real "
        "property for STAR bond projects (K.S.A. 12-17,172). These are meaningful structural safeguards "
        "not present in older STAR bond legislation. The primary remaining fiscal risk is the KDFA "
        "bond issuance authority, which has no aggregate cap, and the mall redevelopment tier, which "
        "applies the program to declining-demand commercial assets for the first time.",
        ST["body"]
    ))

    # ── LEGISLATIVE HISTORY ───────────────────────────────────────────────────
    story += section_heading("2. Legislative History")
    story.append(Paragraph("2.1 Version Evolution", ST["subsection"]))

    version_data = [
        ["Version", "Doc ID", "Size", "Key Addition"],
        ["v1 - Introduced", "3103109", "1,210 chars",
         "Simple sunset extension to July 1, 2030. Nothing else."],
        ["v2 - Senate Comm Sub", "3129552", "66,423 chars",
         "Full rewrite: adds mall redevelopment, quarterly visitor data, transparency, "
         "no state general fund pledge, no eminent domain, sunset to 2028."],
        ["v3 - Senate Floor Amended", "3132087", "67,138 chars",
         "Adds vertical construction (in curly brackets = committee amendment markup). "
         "This is the version passed 32-8 on Feb 19, 2025."],
        ["v4 - House Comm Sub", "3181263", "94,283 chars",
         "Adds port authority for Unified Government of Wyandotte County/KCK "
         "(K.S.A. 12-3402). Expands rural redevelopment definition to include "
         "counties under 100,000 pop in KC/Wichita MSAs."],
        ["v5 - House Amended", "3356862", "95,473 chars",
         "Adds hard visitor origin thresholds (30%/100 miles; 20% out-of-state) and "
         "enforcement mechanism. Creates two mall project tiers (large metropolitan vs. "
         "rural). Extends sunset to July 1, 2031. Current engrossed version."],
    ]
    story.append(alternating_table(
        version_data[0], version_data[1:],
        col_widths=[1.4*inch, 0.8*inch, 0.9*inch, 3.7*inch],
        wrap_cols=[3]
    ))
    story.append(Spacer(1, 0.15*inch))

    story.append(Paragraph("2.2 Legislative Milestone Timeline", ST["subsection"]))
    timeline_data = [
        ["Date", "Chamber", "Action"],
        ["Feb 5, 2025",   "Senate", "v1 introduced - simple sunset extension only"],
        ["~Feb 12, 2025", "Senate", "v2 committee substitute adopted - comprehensive rewrite"],
        ["~Feb 17, 2025", "Senate", "v3 floor amendment - vertical construction added"],
        ["Feb 19, 2025",  "Senate", "Emergency Final Action - v3 passed 32 Yea / 8 Nay (80%)"],
        ["~Mar-Apr 2025", "House",  "Referred to House Committee on Commerce, Labor and Economic Development"],
        ["~Late 2025",    "House",  "v4 House committee substitute - port authority and MSA county expansion added"],
        ["~Jan-Feb 2026", "House",  "v5 House amendment - visitor origin thresholds, enforcement, dual mall tiers, 2031 sunset"],
        ["Feb 10, 2026",  "House",  "House Committee Report: recommends v5 pass as amended - advancing to House floor"],
        ["Pending",       "House",  "Full House floor vote not yet taken as of report date"],
    ]
    story.append(alternating_table(
        timeline_data[0], timeline_data[1:],
        col_widths=[1.1*inch, 0.85*inch, 4.85*inch],
        wrap_cols=[2]
    ))
    story.append(Spacer(1, 0.15*inch))

    story.append(Paragraph("2.3 Senate Vote Analysis (Roll Call 1494345)", ST["subsection"]))
    vote_data = [
        ["Roll Call ID", "Date", "Chamber", "Description", "Yea", "Nay", "NV", "Total", "Result"],
        ["1494345", "Feb 19, 2025", "Senate",
         "Emergency Final Action - Substitute (v3) passed as amended",
         "32", "8", "0", "40", "PASSED"],
        ["-", "Pending", "House",
         "Full House floor vote on v5 - not yet recorded",
         "-", "-", "-", "125", "PENDING"],
    ]
    story.append(alternating_table(
        vote_data[0], vote_data[1:],
        col_widths=[0.75*inch, 0.85*inch, 0.75*inch, 2.4*inch, 0.35*inch, 0.35*inch, 0.3*inch, 0.45*inch, 0.7*inch],
        wrap_cols=[3]
    ))
    story.append(Paragraph(
        "The 80% Senate support (32-8) indicates broad bipartisan consensus. The 8 dissenting votes "
        "are consistent with fiscal conservative objections to program scope expansion. The House "
        "committee recommendation signals continued legislative support for the expanded v5 text.",
        ST["body"]
    ))

    # ── KEY PROVISIONS ────────────────────────────────────────────────────────
    story.append(PageBreak())
    story += section_heading("3. Key Provisions (Based on Enacted Statutory Text)")

    story.append(Paragraph(
        "The following analysis is grounded in the actual statutory text of the Senate-passed version "
        "(v3, doc_id 3132087) and the current House-engrossed version (v5, doc_id 3356862), retrieved "
        "via the LegiScan API. Where the two versions differ materially, both are described.",
        ST["body"]
    ))

    story.append(Paragraph("3.1 Port Authority - Unified Government of Wyandotte County/KCK (House v5 only)", ST["subsection"]))
    story.append(Paragraph(
        "Section 1 of the House substitute (New Section 1) authorizes the Unified Government of "
        "Wyandotte County and Kansas City, Kansas, to create a port authority with all powers under "
        "article 34 of chapter 12 of the Kansas Statutes Annotated. This provision was absent from the "
        "Senate-passed text and was added by the House committee. The authorization operates via "
        "K.S.A. 12-3402, which requires a port authority to be approved by enactment of a bill - SB197 "
        "itself serves as that legislative authorization. The port authority is established by appropriate "
        "resolutions or ordinances of the UG governing body.",
        ST["body"]
    ))
    story.append(Paragraph(
        'Statutory language: "The legislature approves the creation of a port authority by the governing '
        'body of the unified government of Wyandotte county and Kansas City, Kansas, with all the powers, '
        'duties, limitations and obligations provided for in article 34 of chapter 12 of the Kansas '
        'Statutes Annotated..."',
        ST["quote"]
    ))

    story.append(Paragraph("3.2 Mall Redevelopment - Two-Tier Project Structure (House v5)", ST["subsection"]))
    story.append(Paragraph(
        "The House version creates two distinct categories of mall STAR bond projects, each with "
        "different eligibility thresholds and construction cost allowances. This two-tier structure "
        "replaced the Senate version's single flat eligibility standard ($10M capital investment, 50% "
        "vacancy threshold).",
        ST["body"]
    ))
    mall_tiers = [
        ["Criterion", "Large Metropolitan Mall", "Rural Mall"],
        ["Visitor origin (distance)", "30% from 100+ miles", "20% from 100+ miles"],
        ["Out-of-state visitors", "20% from outside Kansas", "Not required"],
        ["Economic decline required?", "Yes (2+ measurable indicators, 10-year lookback)", "Yes (same standard)"],
        ["Min. capital investment", "$50,000,000", "Not specified in v5 (rural standards apply)"],
        ["Min. projected gross sales", "$50,000,000", "Not specified"],
        ["Application deadline", "Dec 31, 2025", "Dec 31, 2026"],
        ["One-per-county limit?", "Yes", "Yes"],
        ["Construction costs eligible?", "Yes (interior/exterior, parking) - first app only", "Yes, if sports/entertainment or education tourism"],
        ["Vacancy threshold", "50%+ leasable area unoccupied", "50%+ leasable area unoccupied"],
    ]
    story.append(alternating_table(
        mall_tiers[0], mall_tiers[1:],
        col_widths=[2.0*inch, 2.4*inch, 2.4*inch],
        wrap_cols=[0, 1, 2]
    ))

    story.append(Paragraph("3.3 Visitor Origin Requirements and Enforcement (House v5, K.S.A. 12-17,164(k) and (l))", ST["subsection"]))
    story.append(Paragraph(
        "The House version codifies specific, numeric visitor origin thresholds as a prerequisite for "
        "project approval by the Secretary of Commerce. For standard STAR bond projects, the Secretary "
        "shall not approve any project unless the project is likely to attract at least 30% of visitors "
        "from a distance of at least 100 miles AND at least 20% of visitors from outside the state. "
        "For rural redevelopment projects and rural mall projects, the threshold is lower: at least "
        "20% of visitors from at least 100 miles.",
        ST["body"]
    ))
    story.append(Paragraph(
        'Statutory enforcement mechanism (K.S.A. 12-17,164(l)): "Beginning with the third calendar year '
        'following the year that the STAR bond project district was established, the secretary shall '
        'review visitor origin data...If the secretary determines that the STAR bond project has not '
        'met such visitor origin requirements, the developer or developers shall be prohibited from '
        'participating in any other STAR bond project approved by the secretary subsequent to such '
        'determination until the secretary finds upon annual review of a succeeding year that such '
        'requirements have been met."',
        ST["quote"]
    ))
    story.append(Paragraph(
        "The enforcement mechanism is meaningful but has a 3-year grace period before compliance "
        "review begins, and the sanction (exclusion from future projects) does not affect the existing "
        "project's bond obligations. A developer who has already received bond financing faces no "
        "direct financial penalty beyond loss of future project eligibility.",
        ST["body"]
    ))

    story.append(Paragraph("3.4 Vertical Construction (Both Versions, New Section 2/3)", ST["subsection"]))
    story.append(Paragraph(
        "Both Senate v3 (in markup brackets indicating committee amendment) and House v5 authorize the "
        "Secretary of Commerce to approve vertical construction within STAR bond project districts in "
        "cities with a population under 60,000, provided approval is granted prior to December 31, 2025. "
        "This is a time-limited provision applicable only to small-city districts. It does not authorize "
        "vertical construction in the Kansas City or Wichita metro areas.",
        ST["body"]
    ))

    story.append(Paragraph("3.5 Rural Redevelopment - MSA County Expansion (House v5, K.S.A. 12-17,162(x))", ST["subsection"]))
    story.append(Paragraph(
        "The House version expands the definition of 'rural redevelopment project' to include two "
        "categories: (1) the existing definition - areas outside metro areas over 50,000 population, "
        "with $3M minimum capital investment; and (2) a new category - counties with a population "
        "under 100,000 within the Kansas City or Wichita metropolitan statistical areas, also requiring "
        "$3M minimum capital investment and regional importance. This is the mechanism that extends "
        "STAR bond eligibility to smaller MSA counties.",
        ST["body"]
    ))

    story.append(Paragraph("3.6 State General Fund Prohibition (Both Versions, K.S.A. 12-17,169(a)(6))", ST["subsection"]))
    story.append(Paragraph(
        "Both Senate v3 and House v5 contain an explicit prohibition: state general fund moneys may "
        "not be pledged for repayment of any special obligation bond issued by a city or county to "
        "finance a STAR bond project. KDFA bonds are similarly structured as revenue-only obligations "
        "not constituting a debt of the state. This is a hard statutory firewall protecting the state's "
        "general credit.",
        ST["body"]
    ))
    story.append(Paragraph(
        'Statutory language: "Under no circumstance shall state general fund moneys be pledged for '
        'the repayment of any special obligation bond issued by a city or county to finance a STAR '
        'bond project pursuant to subsection (a)(1) or (a)(2)."',
        ST["quote"]
    ))

    story.append(Paragraph("3.7 Eminent Domain Prohibition (Both Versions, K.S.A. 12-17,172)", ST["subsection"]))
    story.append(Paragraph(
        "Both versions repeal the prior condemnation authority and replace it with an absolute "
        "prohibition: no city or county shall exercise eminent domain power to acquire real property "
        "for a STAR bond project. This reverses prior law, which allowed condemnation upon a 2/3 "
        "governing body vote. This is a significant property rights protection added by SB197.",
        ST["body"]
    ))

    story.append(Paragraph("3.8 Transparency and Reporting (Both Versions, K.S.A. 12-17,166(i) and 12-17,169(c))", ST["subsection"]))
    story.append(Paragraph(
        "The bill mandates the Secretary of Commerce to make the following publicly available on the "
        "Department of Commerce website: (A) feasibility study; (B) STAR bond project plan; (C) "
        "financial guarantees of the prospective developer; (D) continuing updates; and (E) visitor "
        "data on a continuing basis. Visitor data must be published within 90 days of receipt and "
        "must include a calculation of in-state vs. out-of-state visitors per quarter. Annual "
        "legislative reports must include gross annual sales, bond balances, visitor origin data, "
        "and - per House v5 - information on business movement into/out of districts and local sales "
        "tax revenues lost due to such movement.",
        ST["body"]
    ))

    story.append(Paragraph("3.9 Sunset Extension", ST["subsection"]))
    story.append(Paragraph(
        "Senate v3 extends the STAR bonds financing act sunset from July 1, 2026 to July 1, 2028 "
        "(K.S.A. 12-17,179(b)). House v5 further extends this to July 1, 2031. The 5-year extension "
        "in the House version significantly expands the window for new project applications and "
        "authorization. Related bill HB2292 would establish a food sales tax revenue replacement "
        "fund for pre-2022 STAR bond districts affected by Kansas's food sales tax elimination.",
        ST["body"]
    ))

    story.append(Paragraph("3.10 Comparison to Similar State Programs", ST["subsection"]))
    comp_data = [
        ["State", "Program", "Comparable Feature", "Key Difference vs. SB197"],
        ["Missouri", "TIF / Chapter 100 Bonds",
         "Mall/retail redevelopment",
         "Missouri TIF broader scope but lacks numeric visitor origin thresholds; no eminent domain prohibition"],
        ["Iowa", "Urban Renewal TIF",
         "Vertical mixed-use construction",
         "Iowa program has no visitor origin requirements; focused on assessed value increment, not sales tax"],
        ["Nebraska", "Enhanced Employment Areas",
         "MSA-adjacent county eligibility",
         "Nebraska requires wage recapture metrics; KS SB197 has no wage standards"],
        ["Colorado", "DURA Bonds + Enterprise Zones",
         "State-level bond authority (KDFA analog)",
         "Colorado uses existing EZ infrastructure; KS creates new port authority layer"],
        ["Oklahoma", "Quality Jobs + TIF",
         "Visitor origin tracking for tourism projects",
         "Oklahoma tracks job creation/quality; KS tracks visitor origin - different accountability metric"],
    ]
    story.append(alternating_table(
        comp_data[0], comp_data[1:],
        col_widths=[0.7*inch, 1.5*inch, 1.8*inch, 2.8*inch],
        wrap_cols=[1, 2, 3]
    ))

    # ── ECONOMIC IMPACT ───────────────────────────────────────────────────────
    story.append(PageBreak())
    story += section_heading("4. Economic Impact")
    story.append(Paragraph(
        "The LegiScan fiscal note records 'Fiscal Note: As introduced' - i.e., the KLRD note was "
        "prepared against v1, the simple sunset extension. No fiscal note has been published for "
        "the comprehensive v2-v5 versions. This is a material transparency gap: the bill grew from "
        "1,210 to 95,473 characters between introduction and current engrossment, yet the only "
        "available fiscal note covers the trivial original version.",
        ST["body"]
    ))

    econ_data = [
        ["Fiscal Dimension", "Status / Estimate", "Basis"],
        ["KLRD Fiscal Note",
         "Applies to v1 only (sunset extension)",
         "No KLRD note published for v2-v5. Material gap given 78x expansion of bill scope."],
        ["Direct State Sales Tax Revenue",
         "Net neutral if baseline held",
         "STAR bonds capture only incremental revenue above pre-district base year. "
         "K.S.A. 12-17,162(hh) defines tax increment as above-base-year revenue only."],
        ["KDFA Contingent Liability",
         "Potentially $100M-$1B+ (no cap)",
         "KDFA bonds are revenue-only (not state debt) per K.S.A. 12-17,169(a)(2)(B), "
         "but no aggregate cap on issuance exists in SB197. Exposure bounded only by "
         "Secretary's discretion and market demand."],
        ["State General Fund Exposure",
         "Prohibited by statute",
         "K.S.A. 12-17,169(a)(6) explicitly bars state general fund pledge. "
         "Stronger protection than prior law."],
        ["Mall Redevelopment Projects",
         "2-5 major sites likely (est.)",
         "50%+ vacancy threshold + $50M capital minimum for large metropolitan tier "
         "limits eligible sites. Large format mall vacancies in KC and Wichita metros "
         "are the primary targets."],
        ["Local Sales Tax Displacement",
         "Possible; tracked in reports",
         "House v5 adds requirement to report business movement into/out of districts "
         "and local sales tax revenues lost. This is a meaningful new accountability requirement."],
        ["Food Sales Tax Revenue Gap",
         "Partially addressed by HB2292",
         "Kansas food sales tax elimination (Jan 1, 2024) reduced revenues in pre-2022 STAR "
         "districts. HB2292 proposes state replacement fund. SB197 does not address this gap."],
        ["Port Authority Capitalization",
         "TBD; not in SB197",
         "Port authority is authorized by New Section 1 of House v5 but capital "
         "structure and bonding authority addressed separately under K.S.A. 12-3402."],
    ]
    story.append(alternating_table(
        econ_data[0], econ_data[1:],
        col_widths=[1.7*inch, 1.6*inch, 3.5*inch],
        wrap_cols=[0, 1, 2]
    ))
    story.append(Paragraph(
        "IMPORTANT: Fiscal estimates above are analyst estimates. No official KLRD fiscal note "
        "covering the comprehensive bill provisions (v2-v5) was available via the LegiScan API "
        "at the time of this report.",
        ParagraphStyle(
            "Disclaimer", fontSize=8, leading=11, textColor=colors.HexColor("#666666"),
            fontName="Helvetica-Oblique", spaceBefore=4
        )
    ))

    # ── STRUCTURAL POLICY CONCERNS ────────────────────────────────────────────
    story.append(PageBreak())
    story += section_heading("5. Structural Policy Concerns")

    concerns = [
        ("No KLRD Fiscal Note on Comprehensive Provisions",
         "The only published KLRD fiscal note covers SB197 as introduced - a one-provision sunset "
         "extension. The bill was comprehensively rewritten in committee before Senate passage, "
         "adding mall redevelopment, KDFA bond authority, port authority, and visitor origin "
         "enforcement. The Legislature is voting on a 95,000-character bill with fiscal analysis "
         "that covers a 1,210-character bill. A supplemental fiscal note on v5 should be required "
         "before House floor action."),
        ("Visitor Origin Enforcement - 3-Year Grace Period and No Financial Penalty",
         "The enforcement mechanism in K.S.A. 12-17,164(l) is structural - it bars non-compliant "
         "developers from future projects - but does not commence until the third calendar year after "
         "district establishment. A developer who receives KDFA bond financing on Day 1 faces no "
         "compliance review until Year 3. If found non-compliant, the sanction is exclusion from "
         "future projects; existing bond obligations are unaffected. No clawback, penalty payment, "
         "or bond acceleration mechanism exists for chronic non-compliance."),
        ("KDFA Bond Issuance - No Aggregate Cap",
         "K.S.A. 12-17,169(a)(2)(B) authorizes KDFA to issue special obligation bonds for major "
         "professional sports complex projects. While these bonds are explicitly not state debt and "
         "cannot be backed by the state general fund, no aggregate cap on outstanding KDFA STAR "
         "bond issuance exists. KDFA's statutory borrowing capacity under this section is bounded "
         "only by the Secretary's discretion and the state finance council's oversight role. "
         "Without a cap, the program can scale to any size the Secretary and council approve."),
        ("Mall Redevelopment - Declining Demand Markets",
         "The 'large metropolitan mall STAR bond project' definition requires 50%+ vacancy AND "
         "$50M capital investment AND a finding of economic decline (two measurable indicators "
         "over 10 years). This is a reasonable set of criteria. However, the underlying premise "
         "of STAR bond financing - that incremental sales tax revenue will exceed bond costs - is "
         "harder to satisfy in a 50%+ vacant mall than in the tourism destinations the program "
         "was designed for. The feasibility study requirement (K.S.A. 12-17,166(b)) applies, but "
         "the Secretary retains substantial discretion over consultant selection and methodology."),
        ("Vertical Construction - Time-Limited and Narrow Applicability",
         "The vertical construction provision (New Section 2/3) authorizes the Secretary to approve "
         "vertical construction only in cities with population under 60,000, and only if approval "
         "is granted prior to December 31, 2025. The deadline has already passed as of this report "
         "date. This provision is either already operative (if any approvals were granted before "
         "year-end 2025) or is already expired. The Legislature should clarify whether any "
         "approvals were granted and whether the deadline should be extended."),
        ("Rural MSA County Expansion - No Visitor Origin Enforcement for Rural Projects",
         "The rural redevelopment expansion (K.S.A. 12-17,162(x)(2)) adds counties under 100,000 "
         "population in the KC/Wichita MSAs as eligible for rural redevelopment projects. Rural "
         "projects face a lower visitor origin threshold (20% from 100+ miles; no out-of-state "
         "requirement). This lower threshold reflects the reality of smaller markets but also "
         "means projects in these areas face less rigorous accountability standards than standard "
         "STAR bond projects, despite the fact that the lower-demand environment makes revenue "
         "projections less reliable."),
        ("Port Authority Governance - Transparency Requirements Not Explicitly Extended",
         "New Section 1 of House v5 authorizes the port authority under K.S.A. 12-3402 article 34 "
         "powers. The STAR bond transparency provisions (website publication, legislative reporting, "
         "visitor data) are tied to the STAR bonds financing act and apply to cities and counties "
         "issuing STAR bonds. Whether these transparency requirements extend to port authority "
         "operations - including property acquisition, bond issuance, and project selection - "
         "depends on how the port authority structures its activities. If the port authority "
         "issues bonds under its own K.S.A. 12-3402 authority rather than under the STAR bonds "
         "act, the STAR bond transparency requirements may not apply."),
    ]

    for i, (title, body) in enumerate(concerns, start=1):
        story.append(Paragraph(str(i) + ". " + title, ST["subsection"]))
        story.append(Paragraph(body, ST["body"]))

    # ── POLICY SCORECARD ──────────────────────────────────────────────────────
    story.append(PageBreak())
    story += section_heading("6. Policy Scorecard")
    story.append(Paragraph(
        "Ratings based on the current House-engrossed version (v5, doc_id 3356862) as retrieved "
        "from the LegiScan API and read in full. The scorecard reflects the actual statutory text, "
        "not the bill's long title.",
        ST["body"]
    ))

    scorecard_items = [
        ("Economic Development Potential", "Strong",
         "Port authority, two-tier mall redevelopment, vertical construction, MSA county expansion, "
         "and sunset to 2031 create significant new development pathways.",
         "green"),
        ("Fiscal Accountability - State GF Protection", "Strong",
         "Explicit statutory prohibition on state general fund pledge (K.S.A. 12-17,169(a)(6)). "
         "KDFA bonds are revenue-only, not state debt. Clear constitutional firewalls.",
         "green"),
        ("Visitor Origin Enforcement", "Mixed",
         "Numeric thresholds (30%/20%) are meaningful. 3-year grace period and no financial "
         "penalty (only future project exclusion) limit deterrent effect.",
         "yellow"),
        ("Mall Redevelopment Accountability", "Mixed",
         "Two-tier structure with $50M minimum and decline criteria is reasonable. Feasibility "
         "study required. But Secretary has broad discretion over methodology and consultants.",
         "yellow"),
        ("Eminent Domain Protection", "Strong",
         "Absolute statutory prohibition on eminent domain for STAR bond projects reverses "
         "prior condemnation authority. Strong property rights protection.",
         "green"),
        ("Fiscal Note Completeness", "Weak",
         "KLRD note covers only v1 (1,210 chars). No note published for comprehensive v2-v5 "
         "provisions covering KDFA bonding, port authority, and mall redevelopment.",
         "red"),
        ("KDFA Bonding Cap", "Weak",
         "No aggregate cap on KDFA STAR bond issuance. Exposure bounded only by Secretary "
         "discretion and state finance council oversight.",
         "red"),
        ("Transparency and Reporting", "Strong",
         "Quarterly visitor data, 90-day public posting, annual legislative reports with "
         "sales, bond, and visitor data. House v5 adds business movement and local tax "
         "loss reporting.",
         "green"),
        ("Vertical Construction Viability", "Weak",
         "Approval deadline of Dec 31, 2025 has passed. Applicability limited to cities "
         "under 60,000 population. May be already expired or extremely narrow.",
         "red"),
        ("Legislative Bipartisan Support", "Strong",
         "32-8 Senate vote; House committee recommendation. Strong momentum.",
         "green"),
    ]
    story.append(scorecard_table(scorecard_items))

    # ── POLICY RECOMMENDATIONS ────────────────────────────────────────────────
    story += section_heading("7. Policy Recommendations")

    recs = [
        ("Require a Supplemental KLRD Fiscal Note on v5 Before House Floor Vote",
         "The existing fiscal note was prepared against v1, a simple sunset extension. The House "
         "should require KLRD to prepare and publish a fiscal note on the current House-engrossed "
         "text (v5) before the bill proceeds to a floor vote. This is a basic transparency "
         "requirement given the scale of the bill's expansion."),
        ("Establish an Aggregate Cap on KDFA STAR Bond Issuance",
         "Amend K.S.A. 12-17,169(a)(2)(B) to include a maximum aggregate outstanding balance "
         "of KDFA-issued STAR bonds (e.g., $500M or $1B). While these bonds cannot be backed "
         "by state general funds, KDFA's overall credit exposure and the state's implicit "
         "reputational risk warrant a legislative cap."),
        ("Add Financial Consequences to Visitor Origin Non-Compliance",
         "The current enforcement mechanism (K.S.A. 12-17,164(l)) bars non-compliant developers "
         "from future projects but does not affect existing bond obligations. Amend to add a "
         "revenue recapture mechanism for projects that chronically fail to meet visitor origin "
         "thresholds - for example, requiring additional developer contributions to a reserve "
         "fund if a project misses thresholds for three or more consecutive years."),
        ("Clarify or Reset the Vertical Construction Approval Deadline",
         "The December 31, 2025 deadline for vertical construction approvals (New Section 3) "
         "has passed as of the report date. The Legislature should either: (a) confirm that "
         "approvals were made before the deadline and the provision is operative; or (b) extend "
         "the deadline to a future date if no approvals were issued, to preserve the provision's "
         "intended effect."),
        ("Extend Port Authority Transparency Requirements Explicitly",
         "Amend the bill to explicitly require the Wyandotte County/KCK port authority to "
         "comply with the STAR bond transparency and reporting requirements (K.S.A. 12-17,166(i) "
         "and 12-17,169(c)) for any project financed with STAR bond proceeds, regardless of "
         "which bonding mechanism the authority uses. This closes the potential transparency "
         "gap created by the K.S.A. 12-3402 article 34 authority."),
        ("Require an Independent Feasibility Review for Mall Projects with KDFA Financing",
         "For any mall STAR bond project seeking KDFA bond financing, require an independent "
         "(Secretary-independent) feasibility review by a consultant not on the Secretary's "
         "pre-approved list. The Secretary's current authority to select and oversee feasibility "
         "consultants (K.S.A. 12-17,166(b)) creates a potential conflict of interest when the "
         "Secretary is also acting as the project approval authority."),
        ("Sunset the Rural MSA County Expansion with a Data-Triggered Review",
         "The expansion of rural redevelopment eligibility to MSA counties under 100,000 "
         "population is a significant new extension of the program. Set a 4-year sunset with "
         "reauthorization contingent on KLRD data showing that projects in these markets have "
         "met their visitor origin thresholds and are generating sufficient sales tax increment "
         "to service debt. If no projects are approved in the first 4 years, allow the "
         "provision to expire automatically."),
        ("Link New District Authorizations to HB2292 Revenue Replacement Framework",
         "SB197's new districts may face the same food sales tax revenue shortfall that affects "
         "pre-2022 districts. If HB2292 is enacted creating a state replacement fund, amend "
         "SB197 to cap the replacement fund's exposure to new post-SB197 districts, or require "
         "new projects to demonstrate revenue sufficiency without food sales tax revenues before "
         "approval."),
    ]

    for i, (title, body) in enumerate(recs, start=1):
        story.append(Paragraph(str(i) + ". " + title, ST["subsection"]))
        story.append(Paragraph(body, ST["body"]))

    # ── APPENDIX ──────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story += section_heading("Appendix: Methodology and Tools")

    story.append(Paragraph("Data Sources", ST["subsection"]))
    appendix_data = [
        ["Tool / Source", "Role in Report", "Details"],
        ["LegiScan API",
         "Primary data source",
         "Bill metadata, amendment history, roll call votes (roll_call_id 1494345), sponsor "
         "information, and fiscal note descriptions retrieved via LegiScan REST API. "
         "Full text of all 5 bill versions (doc_ids 3103109, 3129552, 3132087, 3181263, 3356862) "
         "retrieved via getBillText endpoint. LegiScan aggregates from official Kansas legislative sources."],
        ["legiscan_client.py",
         "API client library",
         "Custom Python client wrapping LegiScan API endpoints: getBill, getSearch, getRollCall, "
         "getBillText. Located at C:\\Users\\bryce\\OneDrive\\Desktop\\Claude\\"],
        ["sb197_v3_amended_senate.txt",
         "Senate-passed text (67,138 chars)",
         "Full statutory text of K.S.A. 12-17,160, 12-17,162, 12-17,166, 12-17,169, "
         "12-17,172, and 12-17,179 as amended by Senate v3. Read and analyzed in full."],
        ["sb197_v5_amended_house.txt",
         "House-engrossed text (95,473 chars)",
         "Full statutory text of House Substitute for Substitute for SB 197 as amended "
         "by House Committee. Includes New Sections 1-3 (port authority, mall provisions, "
         "vertical construction) and amended K.S.A. 12-17,164 (visitor origin/enforcement). "
         "Read and analyzed in full."],
        ["Claude AI (Sonnet)",
         "Policy analysis",
         "Anthropic's Claude AI (claude-sonnet-4-5) used for statutory analysis, policy "
         "assessment, and report drafting. Analysis grounded in actual bill text retrieved "
         "via LegiScan API. Knowledge cutoff January 2025; real-time data via API."],
        ["Python / ReportLab",
         "PDF generation",
         "Python 3 with ReportLab library. Script: generate_report.py"],
    ]
    story.append(alternating_table(
        appendix_data[0], appendix_data[1:],
        col_widths=[1.3*inch, 1.4*inch, 4.1*inch],
        wrap_cols=[0, 1, 2]
    ))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Limitations and Corrections to Prior Version", ST["subsection"]))
    story.append(Paragraph(
        "This report supersedes the prior version, which was based solely on bill metadata and the "
        "long title. The following material corrections have been made after reading the full "
        "statutory text: (1) The state general fund pledge prohibition is in both versions - it is "
        "not a gap. (2) The eminent domain prohibition is in both versions - it is not a gap. "
        "(3) The port authority is in House v5 only, not the Senate-passed text. (4) Visitor origin "
        "requirements are numeric thresholds with enforcement in House v5, not merely data collection. "
        "(5) The sunset dates differ between Senate (2028) and House (2031) versions. (6) The "
        "vertical construction provision is time-limited to cities under 60,000 and has an approval "
        "deadline of December 31, 2025, which has now passed.",
        ST["body"]
    ))
    story.append(Paragraph(
        "Fiscal impact figures remain analyst estimates. The only official KLRD fiscal note covers "
        "SB197 as introduced (v1), not the comprehensive provisions of v2-v5. This report is "
        "intended for informational and policy research purposes only and does not constitute legal, "
        "financial, or investment advice.",
        ST["body"]
    ))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=6))
    story.append(Paragraph(
        "KS SB197 Policy Impact Report  |  Generated " + date.today().strftime("%B %d, %Y") +
        "  |  Data: LegiScan API (full bill text)  |  Analysis: Claude AI (Anthropic)  |  PDF: Python/ReportLab",
        ST["footer"]
    ))

    doc.build(story)
    print("Report saved to: " + OUTPUT_PATH)


if __name__ == "__main__":
    build_report()
