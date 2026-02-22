---
name: search-bills
description: Search for legislation by keyword across any U.S. state, all states, or U.S. Congress. Usage: /search-bills <keywords> [state] [year]
---

# search-bills

Search for legislation by keyword across any U.S. state, all states, or the U.S. Congress.

## Usage
`/search-bills $ARGUMENTS`

Examples:
- `/search-bills sports wagering KS`
- `/search-bills minimum wage TX 2`
- `/search-bills paid family leave`
- `/search-bills fentanyl penalties FL 1`
- `/search-bills infrastructure US`          ← federal bills (Congress.gov)
- `/search-bills healthcare federal 119`     ← federal, specific congress number

`$ARGUMENTS` format: `<keywords> [state] [year/congress]`
- keywords: required — one or more search terms
- state: optional — two-letter state code (TX, KS, CA), `ALL` for all states, or `US`/`federal`/`congress` for U.S. Congress
- year/congress: for state bills — 1=all years, 2=current session (default), 3=recent, 4=prior; for federal bills — a Congress number (e.g. 119)

## What this skill does

You are a legislative research assistant. Find and present relevant bills clearly.

### Step 1 — Parse arguments

Extract keywords, state (default: ALL), and year/congress from `$ARGUMENTS`.

### Step 2 — Route by source

**If state is `US`, `federal`, `congress`, or `usa`** → Federal path:
1. Determine congress number: use the provided number or call `current_congress()` from `congress_client`
2. Call `congress_client.search_bills(query, congress=N)` — searches House and Senate bills
3. If zero results, note that and suggest narrowing with bill type (e.g., "HR", "S")

**Otherwise** → State path (unchanged):
1. Call `legiscan_client.search_bills(query, state, year)`
2. If zero results for year=2, automatically retry with year=3 and note the expanded search

### Step 3 — Present results

---

## Search Results: "[keywords]"
**Source:** [State / All States / U.S. Congress (119th)] | **Session:** [description] | **Results:** [count]

| # | Chamber/State | Bill | Title | Last Action | Status |
|---|---------------|------|-------|-------------|--------|
| 1 | [House/Senate or ST] | [Number] | [Title truncated to ~60 chars] | [date] | [status] |
| 2 | ... | | | | |
...

### Top Result
For the highest-relevance bill, provide a brief paragraph:
- What the bill does in plain English
- Current status and last action
- Link (Congress.gov for federal, LegiScan URL for state)

### Refine your search
Suggest 2–3 follow-up commands based on what was found:
- `/explain-bill [bill_label]` — plain-English breakdown of the top result
- `/track-topic [keywords] [state]` — full situational briefing
- `/compare-states [keywords] [states]` — how multiple states have approached this
- `/read-bill [bill_label]` — read the actual bill text

---

## Notes
- Show up to 20 results in the table
- If count > 20, note how many additional results exist and suggest narrowing the query
- For federal results: the Chamber column shows House or Senate; bill label uses standard format (H.R. 1, S. 100, etc.)
- For state results: sort by relevance as returned by LegiScan
- If a bill number is provided as the keyword (e.g. "HR 1234" or "SB84"), treat it as a targeted lookup and suggest `/explain-bill` or `/read-bill`
