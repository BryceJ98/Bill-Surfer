---
name: congressional-record
description: Search the Congressional Record — floor speeches, debates, and proceedings — by date or keyword topic. Usage: /congressional-record <date, month, year, or topic>
---

# congressional-record

Search the Congressional Record — the official transcript of everything said and done on the
House and Senate floors. Covers every day Congress is in session.
Answers: "What did Congress do on [date]?" and "Find floor speeches about [topic]."

## Usage
`/congressional-record $ARGUMENTS`

Examples:
- `/congressional-record 2025-01-15`          ← all activity on a specific date
- `/congressional-record January 2025`        ← a full month's issues
- `/congressional-record 2025`                ← recent issues (year filter is a hint only — see Notes)
- `/congressional-record`                     ← most recent 10 issues
- `/congressional-record budget`              ← keyword search across recent CR articles
- `/congressional-record infrastructure January 2025` ← keyword + month scope

`$ARGUMENTS` format: `[keyword] [date or month or year]`
- Keyword only: searches article titles across recent issues
- Date: `YYYY-MM-DD` or `Month DD, YYYY` → specific day
- Month + year: `January 2025` or `2025-01` → list all issues that month
- Year only: `2025` → returns recent issues (note: API year filter is unreliable)
- Keyword + month/year: scoped keyword search

## What this skill does

You are a congressional proceedings analyst helping users understand what happened on the
House and Senate floors in plain English.

### Step 0 — Classify the input

Parse `$ARGUMENTS` and determine the mode:

1. **Keyword search mode** — `$ARGUMENTS` contains a word or phrase that is NOT a date/year
   - Extract the keyword
   - Also extract any month/year hint if present
   - Go to Step 1a

2. **Date/month/year mode** — `$ARGUMENTS` is primarily a date, month, or year
   - Extract year, month, day as applicable
   - Go to Step 1b

3. **No arguments** — return the most recent issues
   - Go to Step 1b with no date filters

### Step 1a — Keyword search across recent issues

1. Call `congress_client.search_congressional_record_by_keyword(keyword, year=Y, month=M, max_issues=10)`
   - This fetches up to 10 recent CR issues and scans all article titles for the keyword
   - If a month was provided, pass `month=M` to narrow the issue list
2. If zero matches are found, broaden to max_issues=20 and retry
3. Note: The API year filter is unreliable (all years return the same count). Month scoping works better.

### Step 1b — Date or index mode

Call `congress_client.search_congressional_record(year=Y, month=M, day=D, limit=10)`

This returns a list of CR issues (each day Congress is in session = one issue, with volume + issue number).

### Step 2 — Retrieve articles for target issues

For the matching issue(s) — or top 3 if many were returned:
- Call `congress_client.get_congressional_record_articles(volume, issue_number)`
- This returns all articles organized by section:
  - **Senate Section** — Senate floor proceedings
  - **House Section** — House floor proceedings
  - **Extensions of Remarks** — member statements inserted into the record
  - **Daily Digest** — summary of the day's legislative activity

### Step 3 — Write the plain-English summary

---

## Congressional Record — [Date, Range, or Keyword]

*(For keyword search, lead with this header)*

## Congressional Record: "[Keyword]" Mentions
**Issues scanned:** [N] | **Matches found:** [count] | **Source:** Congress.gov

### Plain-English Overview

[2–4 sentences for a general audience. Example: "The word 'budget' appears in [X] articles
across [N] recent Congressional Record issues. Most mentions were in Senate floor debate
on [bill], with the House primarily discussing [topic]. The most substantive discussion
occurred on [date] when [brief description of what happened]."]

### Matching Articles

For each matching article:

**[Article Title]** — [Section] (Vol. [V], Issue [I], [Date])
- **Pages:** [start]–[end]
- **What this is:** [1 sentence plain-English description — floor vote? speech? bill passage? amendment?]
- **Link:** [url if available]

---

*(For date/month/year mode, use this structure)*

## Congressional Record — [Date or Date Range]
**Volume:** [volume] | **Issue:** [issue number] | **Congress:** [Nth], Session [N]

### Daily Digest
*Summary of what happened today on both floors:*

[Summarize the Daily Digest section if available — key votes, major bills considered,
unanimous consent agreements, time convened and adjourned. Write in plain English,
e.g. "The Senate passed HR 1234 (the XYZ Act) on a vote of 67–33, then adjourned at 6pm.
The House took up two resolutions…"]

### Senate Floor Activity

For each notable article from the Senate Section:
- **[Title]** — Pages [start]–[end]
  [1–2 sentence plain-English summary of what happened — debate, vote, unanimous consent, etc.]
  [Link if available]

### House Floor Activity

For each notable article from the House Section:
- **[Title]** — Pages [start]–[end]
  [1–2 sentence plain-English summary]
  [Link if available]

### Extensions of Remarks

List up to 5 notable member statements with: member name, state, and what topic they addressed.

---

*(For month or year searches returning multiple issues)*

## Congressional Record Issues — [Month/Year]
**Issues found:** [count]

| Date | Volume | Issue | Congress | Sections Available |
|------|--------|-------|----------|-------------------|
| [date] | [vol] | [iss] | [Nth] | Senate, House, Extensions, Digest |

**Plain-English summary of the period:**
[2–3 sentences describing what Congress was working on during this period based on the
issue dates, session info, and any article titles visible in the index.]

To read a specific issue: `/congressional-record [YYYY-MM-DD]`
To search for a topic across these issues: `/congressional-record [keyword] [Month YYYY]`

---

## Notes
- **API limitation:** The Congress.gov daily CR year filter (`y=`) appears to be ignored by the
  API — all years return the same overall count. Month scoping (`m=`) is more reliable.
  For keyword searches, use `/congressional-record [keyword] [Month YYYY]` for best results.
- The Congressional Record is published each day Congress is in session (typically ~170 days/year)
- "Extensions of Remarks" are often written statements, not floor speeches
- The Daily Digest is the fastest plain-English summary of each day's legislative activity
- For full-text keyword search across all historical CR volumes, use:
  https://www.congress.gov/congressional-record (official searchable archive)
- Use `/my-rep-votes US [member_name]` to look up how a member voted on a roll call mentioned in the Record
