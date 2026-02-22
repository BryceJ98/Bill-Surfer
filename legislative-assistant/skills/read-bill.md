---
name: read-bill
description: Fetch and display the actual statutory text of a bill with section navigation. Usage: /read-bill <state> <bill_number> or <bill_id>
---

# read-bill

Fetch and display the actual statutory text of a bill, with section-by-section navigation.

## Usage
`/read-bill $ARGUMENTS`

Where `$ARGUMENTS` is one of:
- `<bill_id>` — fetch the latest text version
- `<bill_id> <doc_id>` — fetch a specific text version
- `<state> <bill_number>` — search then fetch (e.g. `KS SB84`)

## What this skill does

You are acting as a legislative document retrieval and navigation assistant.

### Step 1 — Identify the bill and doc_id

If given a bill_id directly, call `get_bill_text_latest` with that bill_id.

If given a state + bill number (e.g. "KS SB84"):
1. Call `search_bills` with the bill number as query, state, year=1
2. Get the bill_id from results
3. Call `get_bill_detail` to see all available text versions (check the `texts` list)
4. Call `get_bill_text_latest` for the best version, OR `get_bill_text` with a specific doc_id if the user asked for a particular version

If given a specific doc_id, call `get_bill_text` with that doc_id directly.

### Step 2 — Present the text

Present the retrieved text with this structure:

---

## [Bill Number] — [Title]
**[State] | Version: [type] | Date: [date] | Size: [text_size] bytes**
**Direct link:** [state_link]

---

### Bill Text

[Display the full text as retrieved]

---

If the text was truncated (truncated=true in the response):
- Show how many bytes remain
- Offer to retrieve a specific section if the user tells you what section they want
- Provide the state_link so they can read the full document

If the document is a PDF (mime contains "pdf"):
- Do not attempt to display binary content
- Show the direct state_link prominently
- Show whatever metadata is available (title, date, type)
- Offer to explain the bill using metadata via `/explain-bill` instead

### Step 3 — Offer navigation

After displaying the text, offer these follow-up options:
- `/explain-bill [bill_id]` — plain-English explanation
- `/compare-states [topic] [states]` — how other states handled this
- `/my-rep-votes [bill_id] [name]` — how a specific legislator voted
- Ask if they want to see a specific section or amendment version
