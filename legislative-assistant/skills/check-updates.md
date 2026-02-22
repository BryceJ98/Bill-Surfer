---
name: check-updates
description: Check for changes on your monitored bills since your last check. Uses change_hash detection. Usage: /check-updates
---

# check-updates

Check what's changed on your monitored bills since you last checked.

## Usage
`/check-updates`

No arguments needed — checks all bills on your monitor list.

## What this skill does

You are a legislative tracking assistant alerting the user to changes on bills they're monitoring.

### Step 1 — Check for changes

Call `check_monitor_changes()` to compare current change_hash values against stored values.

This returns:
- `changed`: bills whose change_hash differs from last check
- `new`: bills added to monitor list since last check
- `unchanged_count`: number of bills with no changes
- `has_changes`: boolean indicating if any updates exist

### Step 2 — Get details on changed bills

For each bill in `changed` and `new` lists:
1. Call `get_bill_changes(bill_id)` to get the latest details
2. Extract recent history, status changes, new votes, and new text versions

### Step 3 — Present the update report

---

## Legislative Update Report
**Checked:** [timestamp] | **Monitored bills:** [total] | **Changes detected:** [count]

---

### If changes exist:

## Bills with Updates

For each changed bill:

### [State] [Bill Number] — [Title]
**Status:** [current status] | **Stance:** [your stance]

#### What Changed
- **[Date]** — [Action description from history]
- **[Date]** — [Another recent action]

#### Current State
- **Last action:** [date] — [description]
- **Status:** [Introduced/Engrossed/Enrolled/Passed/etc.]

#### New Activity (if applicable)
- **New vote:** [Chamber] — [Yea]-[Nay] on [date] ([passed/failed])
- **New text version:** [type] added [date]

**LegiScan:** [url]

---

### If no changes:

## No Updates

All [n] monitored bills are unchanged since your last check on [date if known].

Your monitored bills:
| State | Bill | Title | Status | Stance |
|-------|------|-------|--------|--------|
| [ST] | [Number] | [Title] | [status] | [stance] |

---

### Summary section (always include):

## Summary

| Category | Count |
|----------|-------|
| Bills with updates | [n] |
| Newly added bills | [n] |
| Unchanged | [n] |
| **Total monitored** | [n] |

### What's Moving
Highlight 1-2 sentences about the most significant changes:
- Which bills advanced to a new stage?
- Any bills that passed or failed?
- Any new votes recorded?

### Suggested Actions
Based on the changes detected:
- `/explain-bill [bill_id]` — deep dive on a bill that changed significantly
- `/read-bill [bill_id]` — read new text version if one was added
- `/my-rep-votes [state] [bill]` — see how legislators voted on new roll calls

---

## Notes
- Change detection uses LegiScan's `change_hash` field — any modification to a bill (status, text, votes, amendments) updates the hash
- The first time you run this, all monitored bills will show as "new" since there's no baseline
- Hash comparisons are stored locally in `~/.legiscan_cache/monitor_hashes.json`
- Run this command regularly (daily or weekly) to stay informed on your tracked legislation
