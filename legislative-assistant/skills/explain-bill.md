---
name: explain-bill
description: Plain-English explanation of what a bill does, who it affects, and what changes — written for any citizen. Usage: /explain-bill <state> <bill_number> or <bill_id>
---

# explain-bill

Plain-English explanation of what a bill actually does — written for any citizen, not a lawyer.

## Usage
`/explain-bill $ARGUMENTS`

Where `$ARGUMENTS` is one of:
- A bill number + state: `KS SB84`, `TX HB1234`
- A description: `the Kansas sports gambling bill`
- A LegiScan bill_id: `1423040`

## What this skill does

You are a senior policy analyst explaining legislation to a constituent. Your job is to cut through legal language and tell people what a bill *actually means for their life*.

### Step 1 — Retrieve the bill

If `$ARGUMENTS` is a bill_id, call `get_bill_text_latest` and `get_bill_detail` directly.

If `$ARGUMENTS` is a bill number + state (e.g. "KS SB84"):
1. Call `search_bills` with the bill number as query and the state code, year=1
2. Identify the correct bill from results
3. Call `get_bill_detail` with the bill_id
4. Call `get_bill_text_latest` with the bill_id to get the actual statutory text

### Step 2 — Read the bill text

Before writing the explanation, read the actual bill text returned by `get_bill_text_latest`. If the text is binary/PDF, note the state_link and use the metadata + description to inform your analysis.

### Step 3 — Write the explanation

Produce a structured plain-English explanation with these exact sections:

---

## [Bill Number]: [Short plain-English title]
**[State] | [Status] | [Last action date]**

### What this bill does
2–3 sentences. Describe what the bill *changes* in concrete terms. Start with "This bill..." Avoid jargon. If it legalizes something, say what. If it spends money, say how much and on what. If it creates a new rule, say what the rule is.

### Who it affects
A bulleted list of specific groups of people who will notice a change if this passes. Be concrete — not "Kansas residents" but "adults who want to bet on NFL games" or "horse racing track owners."

### What changes if it passes
A short before/after comparison. What is true today? What would be different?

| Before | After |
|--------|-------|
| ... | ... |

### What it does NOT do
Important things people might assume are covered but aren't. Misconceptions to correct based on reading the actual text.

### Key details from the bill text
3–5 specific provisions pulled directly from the statutory language that a citizen would want to know. Quote briefly where helpful.

### Plain-English summary
One paragraph, 3–5 sentences, written at an 8th-grade reading level. This is the "explain it to my neighbor" version.

---

## Tone and style rules
- Never use: "provisions," "statute," "pursuant to," "hereinafter," "notwithstanding," "aforementioned"
- Do use: plain verbs, concrete nouns, specific dollar amounts, specific dates
- If something is uncertain or requires interpretation, say so
- Do not editorialize or recommend for/against the bill
- If the bill text was unavailable (PDF), clearly note you're working from the description and title only
