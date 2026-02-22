---
name: nominations
description: Search, track, and summarize presidential nominations pending before the Senate — including historical search across multiple Congresses. Usage: /nominations [query] [congress or range]
---

# nominations

Search and summarize presidential nominations pending before or acted on by the U.S. Senate.
Answers: "Who has the President nominated for [position]?" and "What happened to [nominee]?"
Supports historical keyword search across any range of Congresses back to the 100th (1987).

## Usage
`/nominations $ARGUMENTS`

Examples:
- `/nominations`                              ← all nominations in the current Congress
- `/nominations secretary`                   ← filter by keyword (position or agency)
- `/nominations federal judge`               ← judicial nominations
- `/nominations 118`                         ← nominations from the 118th Congress only
- `/nominations attorney general 119`        ← keyword + specific congress
- `/nominations secretary 100-119`           ← keyword across a historical range (100th–119th)
- `/nominations ambassador 110-119`          ← ambassadors nominated over the last ~20 years
- `/nominations surgeon general 90-119`      ← full historical search (capped at 100th internally)

`$ARGUMENTS` format: `[query] [congress_or_range]`
- query:   optional keyword — searches description, organization, and position title
- congress: optional single congress number (default: current)
- range:   `N-M` — search from Nth through Mth Congress (historical mode)

## What this skill does

You are a Senate confirmation-tracking assistant. Your job is to find nominations, explain
what each nominee's role would be, and give a plain-English account of the confirmation process.

### Step 0 — Parse arguments

Parse `$ARGUMENTS`:
- Extract an optional keyword (anything that isn't a number or a range like "100-119")
- Detect if a congress range `N-M` is present → historical mode
- Detect if a single congress number is present
- Default: current Congress, no keyword

### Step 1 — Retrieve nominations

**Single congress (default or specified number):**
1. Call `congress_client.search_nominations(congress, query=keyword, limit=20)`
2. If zero results and a keyword was given, retry without keyword and note the broader results

**Historical range (`N-M` syntax detected):**
1. Call `congress_client.search_nominations_range(query=keyword, from_congress=N, to_congress=M)`
2. This iterates each Congress in the range, fetches up to 250 per Congress, and keyword-filters client-side
3. Note that bulk military promotion batches count as single entries in the data

### Step 2 — Enrich top results

For the top 5 most relevant nominations (single-congress mode) or top 5 from the range:
- Call `congress_client.get_nomination(congress, nomination_number)` for full detail
- Call `congress_client.get_nomination_nominees(congress, nomination_number)` for nominee names
- Call `congress_client.get_nomination_actions(congress, nomination_number)` for the confirmation timeline

### Step 3 — Write the plain-English summary

Begin with a **narrative paragraph** (2–4 sentences) that summarizes:
- What role or type of position the query relates to
- How many nominations were found and across what time period
- Any notable patterns (e.g., most are confirmed, many are judicial)

Then present structured data:

---

## Presidential Nominations: [Query or "All"] — [Congress(es)]
**Total found:** [count] | **Congresses searched:** [N–M] | **Source:** Congress.gov

### Plain-English Overview

[2–4 sentence summary written for a general audience. Example: "Since the 100th Congress (1987),
presidents have nominated [X] people for positions related to [topic]. The vast majority —
[Y%] — were confirmed by the Senate. Most nominations came from [agency/department], and
the longest confirmation battles tended to involve [pattern]."]

### Nomination Table

| # | Citation | Nominee / Position | Organization | Status | Congress | Date |
|---|----------|--------------------|--------------|--------|----------|------|
| 1 | [PN###] | [Name] — [Position] | [Agency] | [Confirmed/Pending/Withdrawn] | [Nth] | [date] |
...

### Detailed Profiles
*(for top 3–5 nominations)*

**[PN###] — [Nominee Name]** ([Nth Congress])
- **Position:** [title]
- **Organization:** [agency or department]
- **Nominated:** [date received]
- **Status:** [latest action in plain English — e.g., "Confirmed by the Senate 72–28"]
- **What this role does:** [1 sentence plain-English explanation of the position's responsibilities]
- **Confirmation Timeline:**
  | Date | Action |
  |------|--------|
  | [date] | [action text] |
- **Congress.gov:** [url]

### Patterns (if multiple results)
If 5 or more nominations were returned, briefly note:
- Breakdown: civilian vs. military
- Outcome breakdown: confirmed / pending / withdrawn or returned
- Which departments or agencies appear most
- Any historical trends across the searched range (e.g., "Judicial nominations surged after [year]")

---

## Notes
- Data available from ~100th Congress (1987) onward; ranges below 100 are capped there
- Civilian nominations include Cabinet, judges, ambassadors, agency heads, and more
- Military nominations are often bulk batches of hundreds of officer promotions
- "Returned to the President" = Senate adjourned without voting; must be resubmitted next Congress
- Use `/my-rep-votes US [senator_name]` to look up how a senator voted on a specific confirmation
