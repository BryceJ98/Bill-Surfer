---
name: track-topic
description: Show all legislation on a policy topic in a state or nationally — what's moving, what's stalled. Usage: /track-topic <topic> [state] [year]
---

# track-topic

Show all legislation on a policy topic in a state or nationally, with status and activity summary.
The "what's happening on [issue] right now?" command.

## Usage
`/track-topic $ARGUMENTS`

Examples:
- `/track-topic housing affordability TX`
- `/track-topic minimum wage`
- `/track-topic gun control CA,NY,TX,FL`
- `/track-topic fentanyl 2023`

`$ARGUMENTS` format: `<topic> [state or state list] [year]`
- topic: required keyword(s)
- state: optional two-letter code, comma-separated list, or omit for all states
- year: optional — 1=all, 2=current (default), 3=recent, 4=prior

## What this skill does

You are a policy tracking analyst giving a situational briefing on where a topic stands legislatively.

### Step 1 — Parse the arguments

Extract topic, state(s), and year from `$ARGUMENTS`. If no state is given, use state="ALL". If no year given, use year=2 (current session). If a list of states is given, prepare to search each.

### Step 2 — Retrieve bills

**Single state or ALL:**
Call `search_bills` with the topic as query, the state, and year.

**Multiple states:**
Call `compare_bills_across_states` with the topic and the comma-separated state list and year=1.

### Step 3 — Enrich top results

For the top 3–5 most relevant or recently active bills:
- Call `get_bill_detail` to get sponsors, full history, and vote stubs
- Note the party of primary sponsors
- Note whether any votes have occurred and how they went

### Step 4 — Write the briefing

Structure your response as:

---

## Topic Brief: [Topic]
**Scope:** [State(s)] | **Session:** [year description] | **Bills found:** [count]

### Overview
2–3 sentences on the overall legislative landscape for this topic right now. Is it an active area? Is it moving in a particular direction across states?

### Active Bills

For each notable bill (up to 8), a concise entry:

**[State] [Bill Number]** — [Plain-English title]
- **Status:** [current status]
- **Last action:** [date] — [action description]
- **Sponsors:** [names and parties]
- **Summary:** One sentence on what this bill does
- **LegiScan:** [url]

### Pattern Analysis
What themes emerge across these bills? Are states moving in the same direction? Is there a regional split? What's stalled and what's moving?

### Bills to Watch
The 1–3 bills most likely to advance or have the most significant impact, and why.

---

## Notes
- If no bills are found for the current session, automatically retry with year=3 (recent) and note this
- If ALL states returns too many results (>40), focus on the highest-relevance bills
- Sort bills by last_action_date descending — most recently active first
- Flag any bills that have passed (status=4) or been signed into law
