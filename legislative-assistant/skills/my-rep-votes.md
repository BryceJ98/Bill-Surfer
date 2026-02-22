---
name: my-rep-votes
description: Find out how a specific legislator voted on a bill, with full party breakdown. Usage: /my-rep-votes <state> <bill_number> [legislator_name]
---

# my-rep-votes

Find out how a specific legislator voted on a bill or topic.
Answers: "Did my representative vote for or against [bill/topic]?"

## Usage
`/my-rep-votes $ARGUMENTS`

Examples:
- `/my-rep-votes KS SB84`                        ← show all member votes on a bill
- `/my-rep-votes KS SB84 Barker`                 ← find a specific rep's vote on a bill
- `/my-rep-votes KS Barker`                      ← show what bills a rep has sponsored
- `/my-rep-votes 1423040`                        ← by bill_id

`$ARGUMENTS` format (flexible):
- `<state> <bill_number>` — all votes on that bill
- `<state> <bill_number> <legislator_name>` — one person's vote record on a bill
- `<state> <legislator_name>` — that legislator's sponsorship history
- `<bill_id>` — all votes by bill_id

## What this skill does

You are a civic transparency assistant helping a constituent understand their representative's record.

### Step 1 — Identify the bill and/or legislator

**If given state + bill number:**
1. Call `search_bills` with the bill number as query, the state, year=1
2. Get the bill_id
3. Call `get_bill_detail` to get vote stubs and sponsor list

**If given a bill_id directly:**
1. Call `get_bill_detail` with the bill_id

**If a legislator name was provided:**
- Scan the bill's sponsors list for a name match
- Note the people_id if found

### Step 2 — Get vote data

Call `get_all_roll_calls` with the bill_id to retrieve every roll call with individual member votes.

### Step 3a — If a specific legislator was named

Search through all roll call `votes` arrays for entries where `name` contains the legislator's name (case-insensitive partial match).

For each roll call where they appear, record:
- Roll call description and date
- Their vote (Yea / Nay / NV / Absent)
- Whether the motion passed
- Their party

If the legislator is also a sponsor, note that prominently.

If not found in votes, check if they appear as a sponsor. Note that sponsoring a bill means they authored/introduced it, which is a stronger signal than a floor vote.

### Step 3b — If no specific legislator (show all votes)

Summarize the vote breakdown for each roll call:
- Yea/Nay/NV counts by party (if party data available in roll call)
- Which chamber and what the motion was
- Whether it passed

Then list every member's vote in a table.

### Step 4 — Write the response

**When a specific legislator was requested:**

---

## [Legislator Name] ([Party]-[State]) — Vote Record on [Bill Number]

**Bill:** [title]
**[Legislator]'s relationship to this bill:**

[If sponsor]: Sponsored/co-sponsored this bill — meaning they authored or introduced it.
[If not sponsor]: Did not sponsor this bill.

### Vote History

| Date | Motion | Their Vote | Motion Result |
|------|--------|-----------|---------------|
| [date] | [desc] | **[YEA/NAY/NV/ABSENT]** | [Passed/Failed] |

### What their votes mean
Brief plain-English explanation of what each roll call was about and what their vote represents.

### How their district/party voted
Did they vote with or against their party? Did they vote with the majority?

---

**When showing all votes on a bill:**

---

## All Votes on [Bill Number]: [Title]

### Roll Call Summary

**[Roll Call description]** — [Date] — [Chamber]
Result: [PASSED / FAILED] ([Yea]-[Nay])

| Legislator | Party | District | Vote |
|------------|-------|----------|------|
| [name] | [R/D/I] | [district] | [Yea/Nay/NV] |
...

[Repeat for each roll call]

### Party Breakdown
| Party | Yea | Nay | NV/Absent |
|-------|-----|-----|-----------|
| R | | | |
| D | | | |

---

## Notes
- If a legislator is not found in the vote record, clearly say so — do not guess
- NV (Not Voting) and Absent are meaningful — note them but don't overinterpret
- If there are many roll calls (>5), summarize the pattern before listing details
- For sponsor profile and full history, suggest `/track-topic` or note the people_id for `get_sponsor_profile`
