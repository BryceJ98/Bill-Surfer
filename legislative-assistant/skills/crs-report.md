---
name: crs-report
description: Find and summarize nonpartisan Congressional Research Service reports and bill summaries on any policy topic, with optional date range filtering. Usage: /crs-report <topic or report number> [YYYY-YYYY or YYYY-MM-DD:YYYY-MM-DD]
---

# crs-report

Find and summarize nonpartisan Congressional Research Service (CRS) reports and bill summaries.
CRS produces research exclusively for Congress — the most authoritative, nonpartisan policy
analysis documents in the U.S. government. Supports date range filtering back through all years.

## Usage
`/crs-report $ARGUMENTS`

Examples:
- `/crs-report healthcare`                        ← CRS summaries on healthcare bills (recent)
- `/crs-report minimum wage`
- `/crs-report immigration enforcement 2015-2020` ← filter by year range
- `/crs-report climate change 2010-2024`          ← decade of CRS climate summaries
- `/crs-report R40000`                            ← look up a specific CRS report by number
- `/crs-report IF10244`                           ← CRS "In Focus" brief by number

`$ARGUMENTS` format: `<topic keywords> [year_range]` or `<report_number>`
- topic keywords: anything to search for
- year_range: `YYYY-YYYY` (e.g., `2010-2020`) or `YYYY-MM-DD:YYYY-MM-DD` for precise dates
- report_number: starts with R, IF, IN, RL, RS, SG, or TE followed by digits

## What this skill does

You are a policy research librarian helping users find the best nonpartisan analysis available.
Your goal is to give a plain-English explanation of what CRS found, not just list results.

### Step 0 — Detect input type

**If `$ARGUMENTS` looks like a CRS report number** (starts with R, IF, IN, RL, RS, SG, TE, etc.):
- Call `congress_client.get_crs_report(report_number)` — returns the direct URL
- Present the direct link prominently and explain report type based on prefix

**If `$ARGUMENTS` is a topic keyword (with optional year range)**:
- Continue with Step 1

### Step 1 — Parse date range (if present)

From `$ARGUMENTS`, extract:
- Keywords: everything before the date range pattern
- Year range like `2010-2020` → `from_date="2010-01-01"`, `to_date="2020-12-31"`
- Precise range like `2015-03-01:2018-06-30` → use those dates directly
- No date → omit from_date and to_date (returns most recent summaries)

### Step 2 — Search bill summaries (CRS proxy)

The Congress.gov API does not expose a standalone CRS report search endpoint. Instead:
1. Call `congress_client.search_crs_reports(query=topic, limit=20, from_date=from_date, to_date=to_date)`
   - `from_date` and `to_date` map to the `fromDateTime`/`toDateTime` API parameters (confirmed working)
   - This searches CRS-authored bill summaries — the same CRS analysts' work applied to legislation
2. If zero results with a date range, retry without the range and note the limitation

### Step 3 — Supplement with direct report links

Always add: "For standalone CRS reports (full research reports, background papers, etc.),
search at **crsreports.congress.gov**"

### Step 4 — Write the plain-English summary

Begin with a **narrative paragraph** (3–5 sentences) that explains:
- What CRS found about the topic across the requested time period
- The main policy themes and how they evolved (if date range given)
- Which bills attracted the most CRS attention
- Whether CRS analysis reflects bipartisan concern or a contested area

Then present structured data:

---

## CRS Research: "[Topic]" [— Date Range if specified]

### Plain-English Overview

[3–5 sentences for a general audience. Example: "The Congressional Research Service has been
closely tracking [topic] legislation since at least [year]. CRS analysts have summarized
[X] bills in this space, focusing primarily on [themes]. The analysis shows that [observation —
e.g., 'bipartisan interest peaked in YYYY when Congress passed...' or 'debate has centered on
X vs. Y approaches']. The most recent CRS summary, from [date], addresses [bill] and
[key finding in 1 sentence]."]

### CRS Bill Summaries Found

For each result from `search_crs_reports()`:

**[Bill Label]** — [Title]
- **CRS Summary ([type], [date]):** [First 2–3 sentences of the summary, cleaned up]
- **What this means in plain English:** [1–2 sentence plain-language translation of what the bill does]
- **Current status:** [bill status]
- **Congress.gov:** [url]

### Access Full CRS Reports

For comprehensive CRS research papers on "[topic]":
- **Search:** [https://crsreports.congress.gov](https://crsreports.congress.gov) — official public archive
- **Direct search URL:** `https://crsreports.congress.gov/search/#/?terms=[topic-url-encoded]`
- **Third-party mirror with better search:** [https://everycrsreport.com](https://everycrsreport.com)

Common CRS report types:
| Prefix | Type | Description |
|--------|------|-------------|
| R | Report | In-depth policy analysis (20–100+ pages) |
| IF | In Focus | 2-page policy briefs |
| IN | Insight | Short analysis of current developments |
| RL | Report (legacy) | Older full reports |
| RS | Report Summary | Short summaries |

---

## If a specific report number was given

---

## CRS Report: [Report Number]
**Type:** [derive from prefix — R=Report, IF=In Focus, IN=Insight, RL=Legacy Report, RS=Summary]

This report is hosted directly at CRS's public site. It is not accessible via the Congress.gov API.

**Access it here:**
- **PDF:** [pdf url from `get_crs_report()`]
- **Details page:** [search_url from `get_crs_report()`]
- **crsreports.congress.gov:** `https://crsreports.congress.gov/product/details?code=[report_number]`

---

## Notes
- CRS does not have a public API — this skill uses the `/summaries` endpoint as the closest proxy
- The date range filter (`fromDateTime`/`toDateTime`) is confirmed working in the Congress.gov API
- For standalone CRS reports (R-series, IF-series, etc.), crsreports.congress.gov is the authoritative source
- everycrsreport.com is a useful third-party mirror with better search and older archives
- For legal and constitutional analysis, CRS reports are considered the gold standard
