---
name: docket
description: Manage your personal legislative docket. Add, remove, update, or list bills you're tracking with priority, stance, notes, and tags. Usage: /docket <action> [arguments]
---

# docket

Manage your personal legislative docket — a curated list of bills you're actively tracking.

Bills added to your docket are automatically monitored for changes via LegiScan's GAITS system.

## Usage
`/docket $ARGUMENTS`

### Actions

**Add a bill to your docket:**
- `/docket add TX HB1234` — add with defaults (watch, medium priority)
- `/docket add CA SB567 support high` — add with stance and priority
- `/docket add 1423040 oppose low "Concerns about implementation"` — add with notes
- `/docket add KS HB2001 watch medium "" healthcare,budget` — add with tags

**Remove a bill from your docket:**
- `/docket remove TX HB1234`
- `/docket remove 1423040`
- `/docket remove TX HB1234 keep` — remove from docket but keep monitoring

**Update a docket entry:**
- `/docket update TX HB1234 stance support` — change stance
- `/docket update 1423040 priority high` — change priority
- `/docket update TX HB1234 notes "Committee hearing scheduled for March"` — update notes
- `/docket update TX HB1234 tags healthcare,priority` — update tags

**List your docket:**
- `/docket list` — show all bills
- `/docket list TX` — filter by state
- `/docket list high` — filter by priority
- `/docket list support` — filter by stance
- `/docket list #healthcare` — filter by tag

**View a specific bill:**
- `/docket view TX HB1234` — show docket entry with current status
- `/docket view 1423040`

## What this skill does

You are a legislative tracking assistant helping users manage their personal bill docket.

### Step 1 — Parse the command

Extract the action and arguments from `$ARGUMENTS`:
- **action**: `add`, `remove`, `update`, `list`, or `view`

For `add`:
- Bill identifier (state + number OR bill_id)
- Optional stance: watch (default), support, oppose
- Optional priority: high, medium (default), low
- Optional notes in quotes
- Optional comma-separated tags

For `remove`:
- Bill identifier
- Optional "keep" flag to keep monitoring

For `update`:
- Bill identifier
- Field to update: stance, priority, notes, or tags
- New value

For `list`:
- Optional filter: state code, priority level, stance, or #tag

For `view`:
- Bill identifier

### Step 2 — Resolve bill_id if needed

If the user provided a state and bill number (e.g., "TX HB1234"):
1. Call `search_bills` with the bill number as query and the state
2. Find the matching bill and extract its `bill_id`
3. If no match found, report the error

### Step 3 — Execute the action

**For `add`:**
1. Call `docket_add(bill_id, stance, priority, notes, tags)`
2. Bill is automatically added to GAITS monitor list
3. Confirm success and show the entry

**For `remove`:**
1. Call `docket_remove(bill_id, keep_monitoring=<keep_flag>)`
2. Confirm removal

**For `update`:**
1. Call `docket_update(bill_id, <field>=<value>)`
2. If updating stance, GAITS monitor is also updated
3. Confirm the update

**For `list`:**
1. Parse filter into appropriate filter_by dict
2. Call `docket_list(filter_by)`
3. Display results in a table

**For `view`:**
1. Call `docket_get(bill_id)`
2. Display the full entry with current status

### Step 4 — Present results

---

## For `add` action:

### Added to Docket

| Field | Value |
|-------|-------|
| **Bill** | [State] [Number] |
| **Title** | [Title] |
| **Stance** | [watch/support/oppose] |
| **Priority** | [high/medium/low] |
| **Notes** | [notes or "—"] |
| **Tags** | [tags or "—"] |
| **Current Status** | [status] |
| **Last Action** | [date] — [action] |
| **LegiScan** | [url] |

This bill is now being monitored. Run `/docket-report` to check for updates.

---

## For `remove` action:

### Removed from Docket

**[State] [Number]** has been removed from your docket.
[If keep_monitoring: "Still being monitored via GAITS."]
[If not: "Also removed from monitoring."]

---

## For `update` action:

### Docket Entry Updated

**[State] [Number]** — [field] changed to **[new value]**.

---

## For `list` action:

### Your Legislative Docket
**Filter:** [filter or "All"] | **Bills:** [count]

| # | State | Bill | Title | Stance | Priority | Status | Tags |
|---|-------|------|-------|--------|----------|--------|------|
| 1 | [ST] | [Number] | [Title truncated] | [stance] | [priority] | [status] | [tags] |
| 2 | ... | | | | | | |

### Summary
- **High priority:** [n] bills
- **Supporting:** [n] | **Opposing:** [n] | **Watching:** [n]

### Quick Actions
- `/docket-report` — full status report with change detection
- `/docket add [bill]` — add another bill
- `/docket view [bill]` — see details on a specific bill

---

## For `view` action:

### [State] [Bill Number]
**[Title]**

#### Docket Info
| Field | Value |
|-------|-------|
| **Stance** | [stance] |
| **Priority** | [priority] |
| **Added** | [date added] |
| **Notes** | [notes or "—"] |
| **Tags** | [tags or "—"] |

#### Current Status
| Field | Value |
|-------|-------|
| **Status** | [status] |
| **Last Action** | [date] — [description] |
| **Changed Since Added** | [Yes/No] |

#### Recent History
- [Date] — [Action]
- [Date] — [Action]
- [Date] — [Action]

**LegiScan:** [url]

### Quick Actions
- `/explain-bill [bill_id]` — plain-English explanation
- `/read-bill [bill_id]` — read the bill text
- `/docket update [bill] stance [new_stance]` — change your stance

---

## Stance meanings

| Stance | Use when... |
|--------|-------------|
| **watch** | Tracking neutrally, gathering information |
| **support** | You or your organization supports passage |
| **oppose** | You or your organization opposes passage |

## Priority levels

| Priority | Use for... |
|----------|------------|
| **high** | Bills requiring immediate attention or action |
| **medium** | Important bills to track regularly |
| **low** | Background monitoring, less urgent |

## Notes
- Your docket is stored locally in `~/.legiscan_cache/personal_docket.json`
- All docket bills are automatically added to your GAITS monitor list
- Use `/docket-report` for a comprehensive status check across all bills
- Tags help you categorize bills (e.g., healthcare, budget, education)
