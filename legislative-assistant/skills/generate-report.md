---
name: generate-report
description: Generate a formatted PDF policy impact report for any legislative bill. Usage: /generate-report <state> <bill_number> or <bill_id>
---

# generate-report

Generate a formatted PDF policy report for a legislative bill.

## Usage
`/generate-report [bill_identifier]`

Where `bill_identifier` is either:
- A bill number + state you already retrieved (e.g. "KS SB84")
- A description of the bill (e.g. "the Kansas sports gambling bill")
- A LegiScan bill_id (e.g. "1423040")

## What this skill does

1. **Retrieves bill data** from the LegiScan API using the `legiscan test.py` script at `c:\Users\bryce\OneDrive\Desktop\Claude\legiscan test.py`. If the bill has not already been looked up in the current conversation, call the API first using `getBill` or `getSearch` as appropriate.

2. **Analyzes policy impact** based on:
   - Full legislative history (timeline, vote counts, amendment record)
   - Key provisions and their structural implications
   - Economic impact (revenue, tax structure, fiscal note data)
   - Structural policy concerns and downstream legislation
   - Comparison to similar legislation in other states (use training knowledge)

3. **Generates a PDF report** by writing and running a Python script using ReportLab (`pip install reportlab` if needed). Save the script as `generate_report.py` in `c:\Users\bryce\OneDrive\Desktop\Claude\` and the PDF as `[STATE]_[BILLNUMBER]_Policy_Report.pdf` in the same folder.

## Report structure

The PDF must include all of the following sections:

- **Cover / Title block** — bill number, full title, state, signed date, report date
- **Executive Summary** — 2–3 paragraph overview of the bill and key findings
- **Legislative History** — milestone timeline table, vote analysis table with all roll calls
- **Key Provisions** — structured summary with comparison table where applicable
- **Economic Impact** — revenue/fiscal data table; note if estimates vs. actuals
- **Structural Policy Concerns** — numbered subsections for each major concern
- **Policy Scorecard** — color-coded table rating key policy dimensions (green = strong, yellow = mixed/ongoing, red = weak/below average)
- **Policy Recommendations** — numbered, actionable recommendations
- **Appendix: Methodology & Tools** — explain LegiScan API, Claude AI, Python/ReportLab, and any other tools used

## Design requirements

Use a modern, clean design:
- Primary color: `#1a3a5c` (dark navy) for headers and table headers
- Accent color: `#2c5f8a` (medium blue) for subheadings
- Background alternating rows: `#f0f4f8` and white
- Scorecard: green `#d4edda`, yellow `#fff3cd`, red `#f8d7da` by rating
- Use HRFlowable dividers under each section heading
- Use justified body text, centered metadata
- Tables should have clear column headers with white text on dark background
- Include a styled footer line at end of document

## Arguments

`$ARGUMENTS` — the bill identifier or description. If empty, ask the user which bill to report on.
