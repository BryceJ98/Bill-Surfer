---
name: monitor-bill
description: Add, remove, or list bills on your GAITS monitor list. Track legislation with stance (watch/support/oppose). Usage: /monitor-bill <action> [arguments]
---

# monitor-bill

Manage your LegiScan GAITS monitor list to track bills you care about.

## Usage
`/monitor-bill $ARGUMENTS`

### Actions

**Add a bill to monitoring:**
- `/monitor-bill add TX HB1234` — add bill with default "watch" stance
- `/monitor-bill add 1423040 support` — add by bill_id with "support" stance
- `/monitor-bill add CA SB567 oppose` — add with "oppose" stance

**Remove a bill from monitoring:**
- `/monitor-bill remove TX HB1234`
- `/monitor-bill remove 1423040`

**List all monitored bills:**
- `/monitor-bill list` — show current monitored bills
- `/monitor-bill list archived` — show archived monitors
- `/monitor-bill list 2024` — show monitors from specific year

**Update stance on a monitored bill:**
- `/monitor-bill stance TX HB1234 support` — change stance to support
- `/monitor-bill stance 1423040 oppose` — change stance to oppose

## What this skill does

You are a legislative tracking assistant helping users manage their bill monitoring list.

### Step 1 — Parse the command

Extract the action and arguments from `$ARGUMENTS`:
- **action**: `add`, `remove`, `list`, or `stance`
- For `add`/`remove`/`stance`: extract bill identifier (state + number OR bill_id) and optional stance
- For `list`: extract optional filter (current/archived/year)

### Step 2 — Resolve bill_id if needed

If the user provided a state and bill number (e.g., "TX HB1234"):
1. Call `search_bills` with the bill number as query and the state
2. Find the matching bill and extract its `bill_id`
3. If no match found, report the error and suggest checking the bill number

If the user provided a numeric bill_id directly, use it as-is.

### Step 3 — Execute the action

**For `add`:**
1. Call `set_monitor([bill_id], action="monitor", stance=<stance>)`
2. Confirm success and show the bill details

**For `remove`:**
1. Call `set_monitor([bill_id], action="remove")`
2. Confirm removal

**For `stance`:**
1. Call `set_monitor([bill_id], action="set", stance=<stance>)`
2. Confirm the stance update

**For `list`:**
1. Call `get_monitor_list(record=<filter>)`
2. Display the monitored bills in a table

### Step 4 — Present results

---

## For `add` action:

### Bill Added to Monitor List

| Field | Value |
|-------|-------|
| **Bill** | [State] [Number] |
| **Title** | [Title] |
| **Stance** | [watch/support/oppose] |
| **Current Status** | [status] |
| **Last Action** | [date] — [action] |
| **LegiScan** | [url] |

You'll be notified of changes when you run `/check-updates`.

---

## For `remove` action:

### Bill Removed from Monitor List

**[State] [Number]** has been removed from your monitor list.

---

## For `list` action:

### Your Monitored Bills
**Filter:** [current/archived/year] | **Count:** [n]

| # | State | Bill | Title | Stance | Status | Last Action |
|---|-------|------|-------|--------|--------|-------------|
| 1 | [ST] | [Number] | [Title truncated] | [stance] | [status] | [date] |
| 2 | ... | | | | | |

### Quick Actions
- `/check-updates` — see what's changed on your monitored bills
- `/monitor-bill add [bill]` — add another bill
- `/explain-bill [bill_id]` — get details on any bill above

---

## For `stance` action:

### Stance Updated

**[State] [Number]** stance changed to **[stance]**.

---

## Stance meanings

| Stance | Meaning |
|--------|---------|
| **watch** | Neutral tracking — just monitoring for changes |
| **support** | You support this legislation |
| **oppose** | You oppose this legislation |

## Notes
- The monitor list is tied to your LegiScan API key
- Stances are for your own tracking — they don't affect anything publicly
- Use `/check-updates` regularly to see what's changed on monitored bills
- Bills are automatically archived when their session ends
