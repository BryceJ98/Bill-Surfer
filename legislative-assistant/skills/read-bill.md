---
name: read-bill
description: Fetch and display the actual statutory text of a bill with section navigation. Usage: /read-bill <state> <bill_number> or <bill_id>
---

# read-bill

Fetch and display the actual statutory text of a bill, with section-by-section navigation.

## Usage
`/read-bill $ARGUMENTS`

Where `$ARGUMENTS` is one of:
- `<bill_id>` — fetch the latest text version of a state bill (LegiScan ID)
- `<bill_id> <doc_id>` — fetch a specific text version of a state bill
- `<state> <bill_number>` — search then fetch (e.g. `KS SB84`)
- `<federal_bill>` — any federal bill identifier: `HR 1234`, `S. 456`, `H.J.Res. 7`
- `<federal_bill> <congress>` — with explicit congress number: `HR 1234 119`

## What this skill does

You are acting as a legislative document retrieval and navigation assistant.

### Step 0 — Detect source

**Federal bill** — if `$ARGUMENTS` starts with a federal bill-type prefix (HR, S., HRes, HJRes, SRes, SJRes, HConRes, SConRes):
1. Call `congress_client.parse_bill_identifier($ARGUMENTS)` → `{bill_type, bill_number, congress}`
2. Continue with the **Federal steps** below.

**State bill** — if `$ARGUMENTS` is a numeric ID, a state+bill_number, or a bill_id+doc_id, continue with the **State steps** below.

---

### Federal steps

#### Step F1 — Get bill metadata
Call `congress_client.get_bill(congress, bill_type, bill_number)` for title, sponsor, and status.

#### Step F2 — Fetch bill text
Call `congress_client.get_bill_text(congress, bill_type, bill_number)`.

- If `text` is non-empty: display the full text content.
- If `text` is empty (PDF-only): show the PDF link and Congress.gov URL prominently. Offer `/explain-bill` as an alternative using the CRS summary.

#### Step F3 — Present the text

---

## [Bill Label] — [Title]
**U.S. Congress, [Nth] | [Chamber] | Version: [version type] | Date: [date]**
**Congress.gov:** [congress_url]
**Direct text link:** [url]

### Bill Text

[Display the full text as retrieved]

---

If text was unavailable (PDF only):

> **PDF only** — the text of this bill is only available as a PDF.
> Direct PDF: [pdf_url]
> Congress.gov page: [congress_url]
>
> Use `/explain-bill [bill_label]` to get a plain-English summary using the CRS description.

After displaying, offer:
- `/explain-bill [bill_label]` — plain-English explanation
- `/my-rep-votes US [bill_label] [name]` — how a specific member voted
- `/compare-states [topic] [states]` — how states have approached this issue

---

### State steps

#### Step S1 — Identify the bill and doc_id

If given a bill_id directly, call `get_bill_text_latest` with that bill_id.

If given a state + bill number (e.g. "KS SB84"):
1. Call `search_bills` with the bill number as query, state, year=1
2. Get the bill_id from results
3. Call `get_bill_detail` to see all available text versions (check the `texts` list)
4. Call `get_bill_text_latest` for the best version, OR `get_bill_text` with a specific doc_id if the user asked for a particular version

If given a specific doc_id, call `get_bill_text` with that doc_id directly.

#### Step S2 — Present the text

---

## [Bill Number] — [Title]
**[State] | Version: [type] | Date: [date] | Size: [text_size] bytes**
**Direct link:** [state_link]

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

#### Step S3 — Offer navigation

After displaying the text, offer these follow-up options:
- `/explain-bill [bill_id]` — plain-English explanation
- `/compare-states [topic] [states]` — how other states handled this
- `/my-rep-votes [bill_id] [name]` — how a specific legislator voted
- Ask if they want to see a specific section or amendment version

---

## Notes
- For federal bills, the text is fetched directly from Congress.gov's Formatted Text endpoint
- Congress.gov text files can be very long — display in full unless the user asks for a specific section
- Always provide the direct Congress.gov or state link so the user can verify in context
