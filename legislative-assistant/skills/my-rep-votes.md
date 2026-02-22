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
- `/my-rep-votes KS SB84`                        ← show all member votes on a state bill
- `/my-rep-votes KS SB84 Barker`                 ← find a specific rep's vote on a state bill
- `/my-rep-votes KS Barker`                      ← show what bills a state rep has sponsored
- `/my-rep-votes 1423040`                        ← by LegiScan bill_id
- `/my-rep-votes US HR1234`                      ← all votes on a federal bill
- `/my-rep-votes US HR1234 Sanders`              ← one member's vote on a federal bill
- `/my-rep-votes federal S456 Warren`            ← Senate member vote lookup
- `/my-rep-votes US Sanders`                     ← federal member's sponsored legislation

`$ARGUMENTS` format (flexible):
- `<state> <bill_number>` — all votes on that state bill
- `<state> <bill_number> <legislator_name>` — one person's vote record on a state bill
- `<state> <legislator_name>` — that legislator's sponsorship history (state)
- `<bill_id>` — all votes by LegiScan bill_id
- `US <federal_bill>` — all votes on a federal bill (e.g., `US HR1234`)
- `US <federal_bill> <member_name>` — one member's vote on a federal bill
- `US <member_name>` — a Congress member's vote history and sponsored legislation
- `federal <federal_bill> <member_name>` — same as US path

## What this skill does

You are a civic transparency assistant helping a constituent understand their representative's record.

### Step 0 — Detect source

**Federal path** — if state is `US`, `federal`, or `congress`, OR if the bill identifier matches a federal pattern (HR, S., HRes, etc.):
- Continue with the **Federal steps** below.

**State path** — otherwise:
- Continue with the **State steps** below.

---

### Federal steps

#### Step F1 — Identify the bill and/or member

**If a federal bill was given:**
1. Call `congress_client.parse_bill_identifier(bill_identifier)` → `{bill_type, bill_number, congress}`
2. Call `congress_client.get_bill(congress, bill_type, bill_number)` for title, sponsors, status

**If a member name was given:**
1. Parse state hint if present (e.g., "VT" from "Sanders VT")
2. Call `congress_client.search_members(name=member_name, state=state_hint)` to find the member
3. Note the `bioguide_id` for the matched member

#### Step F2 — Get vote data

**If a bill was given:**
- Congress.gov API provides roll call vote data via the `/bill/{congress}/{type}/{number}` endpoint's related amendments and actions
- Call `congress_client.get_bill_actions(congress, bill_type, bill_number)` to find recorded votes
- Note: detailed member-level roll call data may require accessing congress.gov/roll-call-votes directly; report what is available and provide the direct link

**If a member name was given (no specific bill):**
- Call `congress_client.get_member_votes(bioguide_id)` for their recent vote history
- Call `congress_client.get_member_sponsored(bioguide_id)` for their sponsored legislation

#### Step F3 — Write the response

**When a specific member + bill was requested:**

---

## [Member Name] ([Party]-[State]) — Federal Vote Record on [Bill Label]

**Bill:** [title]
**[Member]'s relationship to this bill:**

[If primary sponsor]: Primary sponsor — they introduced this bill.
[If cosponsor]: Cosponsor — they formally supported this bill.
[If neither]: Did not sponsor or cosponsor this bill.

### Vote History
*(Note: detailed roll call votes on federal bills are recorded by chamber; show what's available from the API. If a specific roll call URL is available, provide it.)*

| Date | Action / Vote | Their Position | Result |
|------|--------------|----------------|--------|
| [date] | [description] | [Yea/Nay/NV/Sponsor] | [Passed/Failed] |

### Congress.gov links
- Bill page: [congress_url]
- Member page: [member_url if available]

---

**When a member name only (no bill) was requested:**

---

## Congress Member Profile: [Member Name] ([Party]-[State])
**Chamber:** [House/Senate] | **District:** [district or state-wide]

### Recent Votes
| Date | Bill / Description | Their Vote | Result |
|------|--------------------|-----------|--------|
| [date] | [description] | [Yea/Nay/NV] | [Passed/Failed] |

### Sponsored Legislation
| Bill | Title | Status |
|------|-------|--------|
| [label] | [title] | [status] |

---

---

### State steps

#### Step S1 — Identify the bill and/or legislator

**If given state + bill number:**
1. Call `search_bills` with the bill number as query, the state, year=1
2. Get the bill_id
3. Call `get_bill_detail` to get vote stubs and sponsor list

**If given a bill_id directly:**
1. Call `get_bill_detail` with the bill_id

**If a legislator name was provided:**
- Scan the bill's sponsors list for a name match
- Note the people_id if found

#### Step S2 — Get vote data

Call `get_all_roll_calls` with the bill_id to retrieve every roll call with individual member votes.

#### Step S3a — If a specific legislator was named

Search through all roll call `votes` arrays for entries where `name` contains the legislator's name (case-insensitive partial match).

For each roll call where they appear, record:
- Roll call description and date
- Their vote (Yea / Nay / NV / Absent)
- Whether the motion passed
- Their party

If the legislator is also a sponsor, note that prominently.

If not found in votes, check if they appear as a sponsor. Note that sponsoring a bill means they authored/introduced it, which is a stronger signal than a floor vote.

#### Step S3b — If no specific legislator (show all votes)

Summarize the vote breakdown for each roll call:
- Yea/Nay/NV counts by party (if party data available in roll call)
- Which chamber and what the motion was
- Whether it passed

Then list every member's vote in a table.

#### Step S4 — Write the response

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

**When showing all votes on a state bill:**

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
- For federal bills: Congress.gov roll call detail may be limited via API; always provide the direct Congress.gov link to the full roll call record
