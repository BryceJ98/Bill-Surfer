---
name: export-csv
description: Export any Bill-Surfer query result to a CSV file — nominations, treaties, bills (state or federal), members, roll calls, CRS reports, docket, and more. Prompts for column selection. Usage: /export-csv <type> [query] [congress or state] [options]
---

# export-csv

Export data from Congress.gov (federal) or LegiScan (state) to a CSV file.
Supports computed columns like `days_to_confirmation`, `days_to_ratification`, and `pass_pct`.
Prompts you to choose exactly which columns you want before running.

## Usage
`/export-csv $ARGUMENTS`

Examples:
- `/export-csv nominations ambassador last 5 years`
- `/export-csv treaties extradition 100-119`
- `/export-csv state-bills "minimum wage" CA`
- `/export-csv federal-bills healthcare 119`
- `/export-csv members senate 119`
- `/export-csv roll-calls --bill-id 1234567`
- `/export-csv docket`
- `/export-csv crs-reports climate 2015-2020`
- `/export-csv house-votes 119`

## Available data types

### Federal (Congress.gov)
| Type | What it exports | Key options |
|------|----------------|-------------|
| `nominations` | Presidential nominations | `--congress N` or `N-M` range |
| `treaties` | Senate treaties | `--congress N` or `N-M` range |
| `federal-bills` | Federal legislation | `--congress N` or `N-M` range |
| `members` | Congress members | `--congress N`, `--chamber house\|senate` |
| `crs-reports` | CRS bill summaries | `--from YYYY-MM-DD`, `--to YYYY-MM-DD` |
| `house-votes` | House roll call votes (118th+) | `--congress N`, `--session 1\|2` |
| `committee-reports` | Committee reports | `--congress N`, `--report-type hrpt\|srpt\|erpt` |
| `hearings` | Committee hearings | `--congress N`, `--chamber house\|senate` |

### State (LegiScan)
| Type | What it exports | Key options |
|------|----------------|-------------|
| `state-bills` | State legislation | `--state XX` (required) |
| `roll-calls` | State roll call votes | `--bill-id N` (required) |
| `legislators` | State legislators | `--state XX` |
| `docket` | Personal docket entries | (none) |
| `monitor` | GAITS monitor list | (none) |

## Column catalog — available columns per type

### nominations
**Fast columns** (no extra API calls):
`congress`, `citation`, `description`, `organization`, `received_date`, `is_civilian`, `status`, `status_date`, `url`

**Enriched columns** (one extra API call per record):
| Column | What it contains |
|--------|----------------|
| `nominee_names` | Semicolon-separated full names of nominees |
| `position_title` | Job title(s) being nominated for |
| `confirmed` | True/False — was the nominee confirmed? |
| `confirmation_date` | Date the Senate voted to confirm (or reject/return) |
| `days_to_confirmation` | Calendar days from nomination received to confirmation vote |

### treaties
**Fast:** `congress`, `treaty_number`, `suffix`, `topic`, `transmitted_date`, `in_force_date`, `status`, `status_date`, `url`, `congress_url`

**Enriched:**
| Column | What it contains |
|--------|----------------|
| `countries` | Countries affected by the treaty |
| `index_terms` | Subject tags |
| `ratified` | True/False — was the treaty ratified? |
| `ratification_date` | Date Senate passed resolution of ratification |
| `days_to_ratification` | Days from transmitted to ratified |

### federal-bills
**Fast:** `congress`, `bill_id`, `bill_label`, `chamber`, `title`, `introduced_date`, `policy_area`, `status`, `status_date`, `sponsor`, `sponsor_party`, `sponsor_state`, `url`

**Enriched:** `cosponsor_count`, `action_count`, `subjects`

### members
**Fast:** `name`, `bioguide_id`, `party`, `state`, `district`, `chamber`, `url`

**Enriched:** `birth_year`, `office_address`, `phone`, `website`

### crs-reports
**Fast only:** `congress`, `bill_label`, `bill_type`, `bill_number`, `title`, `summary_date`, `summary_type`, `summary_text`, `url`

### house-votes
**Fast:** `roll_call`, `session`, `congress`, `date`, `question`, `vote_type`, `legislation`, `result`

**Enriched:** `republican_yea`, `republican_nay`, `democrat_yea`, `democrat_nay`, `independent_yea`, `independent_nay`

### committee-reports / hearings
**Fast only** — see column names in the script output header when you run it.

### state-bills
**Fast:** `bill_id`, `bill_number`, `state`, `title`, `status`, `status_date`, `last_action`, `last_action_date`, `url`

**Enriched:**
| Column | What it contains |
|--------|----------------|
| `sponsor_name` | Primary sponsor name |
| `sponsor_party` | Sponsor party |
| `sponsor_district` | Sponsor district |
| `introduced_date` | Date of first history action (introduction) |
| `subjects` | Semicolon-separated legislative subject tags |
| `days_since_introduction` | Days from introduced to today |
| `days_to_last_action` | Days from introduced to last action date |

### roll-calls
**Fast only:** `roll_call_id`, `bill_id`, `date`, `desc`, `yea`, `nay`, `nv`, `absent`, `passed`, `chamber`, `total_votes`, `pass_pct`

### legislators / docket / monitor
**Fast only** — all key fields included by default.

---

## What this skill does

You are a data export assistant. Your job is to understand what the user wants to export,
ask them which columns they want, then run the export and report the result.

### Step 0 — Parse the export request

From `$ARGUMENTS`, extract:
- **Data type**: one of the types listed above
- **Query keyword**: any non-date, non-number words before flags
- **Congress range or number**: a number like `119` or range like `115-119`
  - "last 2 years" ≈ 119th; "last 4–6 years" ≈ 118–119; "last 8–10 years" ≈ 116–119
  - Formula: `from_congress = 119 - ceil(years / 2)`
- **State code**: two-letter code like `CA`, `TX`
- **Date range**: `2015-2020` → `--from 2015-01-01 --to 2020-12-31`

### Step 1 — Show available columns and ask

Display the two-section column menu for the detected data type (fast vs. enriched),
then ask the user:

> "Here are the available columns for **[type]** exports:
>
> **Fast columns** (no extra API calls):
> [list base columns]
>
> **Enriched columns** (one extra API call per record — slower for large datasets):
> [list enriched columns with brief description]
>
> Which columns would you like in your CSV? You can name them directly, describe what
> you want in plain English (e.g., 'I want the nominee name, whether they were confirmed,
> and how long it took'), or say **all columns** to include everything."

### Step 2 — Map the user's answer to column names

Translate natural language to column names:
- "nominee name" → `nominee_names`
- "position" or "job title" or "role" → `position_title`
- "confirmed?" or "was it confirmed" → `confirmed`
- "confirmation date" → `confirmation_date`
- "days to confirm" or "how long did it take" → `days_to_confirmation`
- "organization" or "agency" or "department" → `organization`
- "countries" or "which countries" → `countries`
- "ratified?" → `ratified`
- "days to ratify" → `days_to_ratification`
- "sponsor" → `sponsor`, `sponsor_party`, `sponsor_state`
- "how long it's been alive" → `days_since_introduction`
- "vote breakdown" or "party breakdown" → `republican_yea`, `republican_nay`, `democrat_yea`, `democrat_nay`
- "all" or "everything" → use `--all-columns`

### Step 3 — Build the command

Construct the full Python command, mapping the collected parameters:

```
python legislative-assistant/tools/csv_export.py <type> [query] \
    [--congress N-M] [--state XX] [--from DATE] [--to DATE] \
    [--chamber X] [--session N] [--report-type X] [--bill-id N] \
    --columns col1,col2,col3 \
    [--enrich]  ← added automatically if enriched columns were requested \
    [--limit 250] \
    --output <type>_<query>_export.csv
```

Default output filename: `<type>_<query_or_timestamp>_export.csv`

### Step 4 — Run the command

Run the command via Bash from the repo root:
```bash
cd c:\Users\bryce\Bill-Surfer && python legislative-assistant/tools/csv_export.py ...
```

### Step 5 — Report results

After the script completes:
1. Show the **absolute path** of the output file
2. Display the **5-row preview table** from the script's stdout
3. State the **total number of records** exported
4. Note if enrichment was used and how many API calls were made

---

## Examples of complete commands

**Ambassador nominations, last 5 years, with computed confirmation timing:**
```bash
python legislative-assistant/tools/csv_export.py nominations ambassador \
    --congress 117-119 \
    --columns citation,nominee_names,position_title,organization,received_date,confirmed,confirmation_date,days_to_confirmation \
    --output ambassadors_117_119.csv
```

**All extradition treaties, full history:**
```bash
python legislative-assistant/tools/csv_export.py treaties extradition \
    --congress 100-119 --all-columns \
    --output extradition_treaties.csv
```

**California healthcare bills with sponsor info:**
```bash
python legislative-assistant/tools/csv_export.py state-bills healthcare \
    --state CA \
    --columns bill_id,bill_number,title,status,sponsor_name,sponsor_party,introduced_date,days_since_introduction \
    --output ca_healthcare_bills.csv
```

**119th Congress Senate members with contact info:**
```bash
python legislative-assistant/tools/csv_export.py members \
    --congress 119 --chamber senate --enrich \
    --output senate_119_members.csv
```

**House votes with party breakdown:**
```bash
python legislative-assistant/tools/csv_export.py house-votes \
    --congress 119 --session 1 \
    --columns roll_call,date,legislation,question,result,republican_yea,republican_nay,democrat_yea,democrat_nay \
    --output house_votes_119.csv
```

**Roll call votes for a specific state bill:**
```bash
python legislative-assistant/tools/csv_export.py roll-calls \
    --bill-id 1234567 \
    --output rollcalls_bill_1234567.csv
```

---

## Notes
- Enrichment makes one extra API call per record — for large exports (100+ records) this can take a minute
- Congress.gov data: nominations from ~100th Congress (1987); treaties from ~90th Congress (1967)
- LegiScan state data: coverage varies by state; most have data from 2010 onward
- The `--limit` flag caps records per congress (default 250, API max 250)
- For very large historical ranges, consider narrowing with a keyword to keep results manageable
- Output is UTF-8 CSV, compatible with Excel (open with Data → From Text/CSV in Excel for best results)
