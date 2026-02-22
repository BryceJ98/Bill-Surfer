---
name: compare-states
description: Side-by-side comparative policy analysis of how multiple states have approached a legislative topic. Usage: /compare-states <topic> <state1,state2,...>
---

# compare-states

Side-by-side comparative policy analysis of how multiple states have approached a legislative topic.
Answers: "What have other states done about X, and what can we learn from them?"

## Usage
`/compare-states $ARGUMENTS`

Examples:
- `/compare-states sports betting KS,NJ,NY,CO,IN`
- `/compare-states paid family leave CA,NY,WA,MA,CT`
- `/compare-states assault weapons ban TX,CA,IL,FL`
- `/compare-states marijuana legalization`  ← omit states for a national survey

`$ARGUMENTS` format: `<topic> [state1,state2,...stateN]`
- topic: required
- states: optional comma-separated list; if omitted, survey top 8 states with most activity

## What this skill does

You are a senior comparative policy analyst producing a state-by-state policy brief.

### Step 1 — Retrieve cross-state data

Call `compare_bills_across_states` with the topic, states (or a representative set if none given), and year=1 (all years — comparative analysis needs historical context).

If no states were specified, use: `CA,NY,TX,FL,IL,OH,PA,WA` as a representative cross-section, then note the user can request specific states.

### Step 2 — Enrich the top bill per state

For the single most relevant bill in each state (highest relevance or most recent activity):
- Call `get_bill_detail` to get sponsors, full history, and vote counts
- Note passage status (passed, vetoed, failed, pending)
- Note the primary sponsor's party
- Note key vote margins if available

### Step 3 — Retrieve text for any enacted laws

For any bill with status=4 (Passed/Enacted), call `get_bill_text_latest` and extract 2–3 key provisions for the comparison table.

### Step 4 — Write the comparative brief

---

## Comparative Policy Brief: [Topic]
**States analyzed:** [list] | **Date:** [today]

### National Landscape
2–3 sentences on where this issue stands nationally. How many states have acted? What direction are they moving? Is there federal activity?

### State-by-State Comparison

| State | Bill | Status | Approach | Key Details | Sponsor Party |
|-------|------|--------|----------|-------------|---------------|
| [State] | [Number] | [Status] | [1-phrase approach] | [1-2 key provisions] | [R/D/I] |
| ... | | | | | |

### Detailed State Profiles

For each state, a paragraph covering:
- What their bill does (or did)
- How it differs from other states' approaches
- Whether it passed, failed, or is pending — and why
- Any notable provisions, tax rates, regulatory structures, or implementation details
- Relevant quote from the bill text if enacted

### Key Differences

A structured comparison of the most policy-significant dimensions where states diverge:

**[Dimension 1, e.g. "Tax Rate"]:**
- State A: X% / State B: Y% / State C: Z%

**[Dimension 2]:**
- etc.

### What Works / What Doesn't
Based on the legislative record and outcomes, what approaches appear to be working? What has stalled or been repealed? Note any states with multiple attempts (indicates contested terrain).

### Takeaways for Policymakers
3–5 concrete lessons a policymaker designing new legislation should take from this comparative analysis.

---

## Federal context

In the **National Landscape** section, always check whether there is active federal legislation on the topic by calling `congress_client.search_bills(topic, congress=current_congress())`. If federal bills exist:
- Mention them in the National Landscape paragraph (e.g., "At the federal level, H.R. X would...")
- Note whether state legislation is ahead of, behind, or aligned with federal activity
- If the user explicitly includes `US` in their state list (e.g., `/compare-states minimum wage US,CA,NY`), add a **Federal** row to the comparison table and a full Federal Profile in the Detailed State Profiles section

## Notes
- Be explicit about what is based on bill text vs. metadata vs. your training knowledge
- If a state has no relevant legislation, say so explicitly — absence of legislation is itself a data point
- Flag bills that are very recent vs. well-established law — recency matters for outcome assessment
- If the user asked about a state pair (e.g. KS vs. NJ for sports betting), lead with a direct head-to-head comparison before the broader survey
- For the Federal row, use "U.S. Congress" as the state name and include the bill's Chamber
