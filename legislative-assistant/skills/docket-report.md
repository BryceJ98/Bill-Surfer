---
name: docket-report
description: Generate a comprehensive status report for all bills in your personal docket. Shows changes, current status, and actionable insights. Usage: /docket-report
---

# docket-report

Generate a comprehensive status report for all bills in your personal legislative docket.

## Usage
`/docket-report`

No arguments needed — reports on all bills in your docket.

## What this skill does

You are a senior policy analyst delivering a briefing on the user's tracked legislation.

### Step 1 — Generate the report

Call `docket_report()` to get:
- All bills in the docket with current status
- Change detection (which bills have been updated)
- Summary statistics by status, priority, and stance

### Step 2 — Analyze the data

For each bill, especially those that have changed:
- Identify significant status changes (passed committee, floor vote, signed, etc.)
- Note any new votes or text amendments
- Flag bills requiring attention based on priority and recent activity

### Step 3 — Present the executive briefing

---

## Legislative Docket Report
**Generated:** [timestamp] | **Bills tracked:** [count] | **Changes detected:** [count]

---

### If there are bills with changes:

## Bills Requiring Attention

For each bill with `has_changed: true`, sorted by priority:

### [Priority] | [State] [Bill Number]
**[Title]**
**Your stance:** [stance]

#### What Changed
Analyze the recent history and identify what's new:
- [Date] — [Significant action]
- [Date] — [Another action if relevant]

#### Current State
- **Status:** [status]
- **Last action:** [date] — [description]

#### Recommended Actions
Based on the change and the user's stance:
- If the bill advanced and user supports: "Consider contacting your representative to voice support"
- If there's a new committee hearing: "Committee hearing scheduled — testimony opportunity"
- If the bill is stalled: "No action in [X] days — may be dead for this session"

---

## Full Docket Status

### High Priority Bills

| State | Bill | Title | Stance | Status | Last Action | Changed |
|-------|------|-------|--------|--------|-------------|---------|
| [ST] | [Number] | [Title] | [stance] | [status] | [date] | [Yes/—] |

### Medium Priority Bills

| State | Bill | Title | Stance | Status | Last Action | Changed |
|-------|------|-------|--------|--------|-------------|---------|
| [ST] | [Number] | [Title] | [stance] | [status] | [date] | [Yes/—] |

### Low Priority Bills

| State | Bill | Title | Stance | Status | Last Action | Changed |
|-------|------|-------|--------|--------|-------------|---------|
| [ST] | [Number] | [Title] | [stance] | [status] | [date] | [Yes/—] |

---

## Summary

### By Status
| Status | Count |
|--------|-------|
| Introduced | [n] |
| In Committee | [n] |
| Passed Chamber | [n] |
| Enrolled | [n] |
| Signed/Chaptered | [n] |
| Failed/Dead | [n] |

### By Your Stance
| Stance | Count | Recent Wins | Recent Losses |
|--------|-------|-------------|---------------|
| Support | [n] | [bills that passed] | [bills that failed] |
| Oppose | [n] | [bills that failed] | [bills that passed] |
| Watch | [n] | — | — |

### Activity Summary
- **Most active bill:** [State Bill] — [n] actions in last 30 days
- **Stalled bills:** [n] bills with no action in 30+ days
- **Upcoming deadlines:** [if detectable from status]

---

## Recommendations

Based on your docket, here are suggested next steps:

1. **[State Bill]** — [Specific recommendation based on status and stance]
2. **[State Bill]** — [Another recommendation]
3. **Review stalled bills** — Consider removing [n] bills with no recent activity

---

### If the docket is empty:

## Your Docket is Empty

You haven't added any bills to your docket yet.

### Get Started
1. Search for bills: `/search-bills [topic] [state]`
2. Add to your docket: `/docket add [state] [bill_number] [stance] [priority]`
3. Run this report again to see your tracked legislation

### Example Workflow
```
/search-bills education funding TX
/docket add TX HB1234 support high "Key education bill"
/docket add TX SB567 watch medium "" education
/docket-report
```

---

## Notes
- Bills with changes are highlighted and shown first
- The report compares current state against the initial state when you added the bill
- Change detection uses LegiScan's change_hash — any modification triggers a change
- Run this report regularly (daily or weekly) to stay informed
- For detailed info on any bill, use `/docket view [bill]` or `/explain-bill [bill_id]`
