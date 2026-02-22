---
name: search-bills
description: Search for legislation by keyword across any U.S. state or all states. Usage: /search-bills <keywords> [state] [year]
---

# search-bills

Search for legislation by keyword across any U.S. state or all states.

## Usage
`/search-bills $ARGUMENTS`

Examples:
- `/search-bills sports wagering KS`
- `/search-bills minimum wage TX 2`
- `/search-bills paid family leave`
- `/search-bills fentanyl penalties FL 1`

`$ARGUMENTS` format: `<keywords> [state] [year]`
- keywords: required — one or more search terms
- state: optional two-letter code (e.g. TX, KS, CA) or omit for all states
- year: optional — 1=all years, 2=current session (default), 3=recent, 4=prior session

## What this skill does

You are a legislative research assistant. Find and present relevant bills clearly.

### Step 1 — Parse arguments

Extract keywords, state (default: ALL), and year (default: 2) from `$ARGUMENTS`.

### Step 2 — Run the search

Call `search_bills` with the parsed query, state, and year.

If zero results are returned for year=2 (current session), automatically retry with year=3 (recent) and note that you expanded the search.

### Step 3 — Present results

---

## Search Results: "[keywords]"
**State:** [state or All States] | **Session:** [year description] | **Results:** [count]

| # | State | Bill | Title | Last Action | Status |
|---|-------|------|-------|-------------|--------|
| 1 | [ST] | [Number] | [Title truncated to ~60 chars] | [date] | [status] |
| 2 | ... | | | | |
...

### Top Result
For the highest-relevance bill, provide a brief paragraph:
- What the bill does in plain English
- Current status and last action
- LegiScan URL

### Refine your search
Suggest 2–3 follow-up commands based on what was found:
- `/explain-bill [bill_id]` — plain-English breakdown of the top result
- `/track-topic [keywords] [state]` — full situational briefing
- `/compare-states [keywords] [states]` — how multiple states have approached this
- `/read-bill [bill_id]` — read the actual bill text

---

## Notes
- Show up to 20 results in the table
- If count > 20, note how many additional results exist and suggest narrowing the search with a more specific query or a state filter
- Sort by relevance (as returned by the API) — highest relevance first
- If a bill number is provided as the keyword (e.g. "SB84"), treat it as a targeted lookup and suggest `/explain-bill` or `/read-bill` for that bill
