---
name: track-topic
description: Show all legislation on a policy topic in a state, nationally, or in U.S. Congress — what's moving, what's stalled. Usage: /track-topic <topic> [state] [year]
---

# track-topic

Show all legislation on a policy topic in a state, nationally, or in the U.S. Congress — what's active, what's stalled, and what to watch.

## Usage
`/track-topic $ARGUMENTS`

Examples:
- `/track-topic housing affordability TX`
- `/track-topic minimum wage`
- `/track-topic gun control CA,NY,TX,FL`
- `/track-topic fentanyl 2023`
- `/track-topic infrastructure US`              ← federal bills only
- `/track-topic healthcare US,TX,CA`            ← federal + two states
- `/track-topic cannabis US,CO,CA 119`          ← federal (119th Congress) + states

`$ARGUMENTS` format: `<topic> [state or state list] [year or congress number]`
- topic: required keyword(s)
- state: optional — two-letter code(s), comma-separated list, or omit for all states; include `US` or `federal` to include Congress
- year/congress: for state bills — 1=all, 2=current (default), 3=recent, 4=prior; for federal — a congress number (e.g. 119)

## What this skill does

You are a policy tracking analyst giving a situational briefing on where a topic stands legislatively.

### Step 1 — Parse the arguments

Extract topic, state(s), and year/congress. Separate `US`/`federal`/`congress` from state codes. If no state is given, use state="ALL" for LegiScan. If no year given, use year=2 (current session).

### Step 2 — Retrieve bills

**Federal search** (if `US`, `federal`, or `congress` is in the state list):
- Call `congress_client.search_bills(topic, congress=N)` for the relevant Congress
- Covers both House and Senate bills

**Single state or ALL states:**
- Call `legiscan_client.search_bills(topic, state, year)`

**Multiple states:**
- Call `compare_bills_across_states(topic, state_list, year=1)`

If no results found for current session/congress, auto-retry with year=3 (recent) or the prior Congress and note the expanded search.

### Step 3 — Enrich top results

For the top 3–5 most relevant or recently active bills:

**Federal bills:**
- Call `congress_client.get_bill(congress, bill_type, bill_number)` for sponsors and status
- Call `congress_client.get_bill_actions(congress, bill_type, bill_number)` for recent history
- Note primary sponsor party, cosponsor count, and committee activity

**State bills:**
- Call `get_bill_detail` to get sponsors, full history, and vote stubs
- Note the party of primary sponsors and whether any votes have occurred

### Step 4 — Write the briefing

---

## Topic Brief: [Topic]
**Scope:** [State(s) and/or U.S. Congress] | **Session:** [year/congress description] | **Bills found:** [count]

### Overview
2–3 sentences on the overall legislative landscape for this topic right now. Is there federal momentum? Are states ahead of Congress or behind?

### Federal Activity
*(include only if federal bills were retrieved)*

For each notable federal bill (up to 5):

**[Chamber] [Bill Label]** — [Plain-English title]
- **Status:** [current status / last action]
- **Last action:** [date] — [action description]
- **Sponsor:** [name] ([Party]-[State]) | **Cosponsors:** [count]
- **Summary:** One sentence on what this bill does
- **Congress.gov:** [url]

### State Activity
*(include only if state bills were retrieved)*

For each notable bill (up to 8):

**[State] [Bill Number]** — [Plain-English title]
- **Status:** [current status]
- **Last action:** [date] — [action description]
- **Sponsors:** [names and parties]
- **Summary:** One sentence on what this bill does
- **LegiScan:** [url]

### Pattern Analysis
What themes emerge across federal and state activity? Are states moving faster or slower than Congress? Is there a partisan pattern? What's stalled and what's moving?

### Bills to Watch
The 1–3 bills (federal or state) most likely to advance or have the most significant impact, and why.

---

## Notes
- If no bills are found for the current session, automatically retry with year=3 (recent) and note this
- If ALL states returns too many results (>40), focus on the highest-relevance bills
- Sort bills by last_action_date descending — most recently active first
- Flag any bills that have passed (status=4) or been signed into law
- Clearly label federal vs. state bills throughout; never mix them in the same table row
