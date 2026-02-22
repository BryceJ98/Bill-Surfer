# AGENTS.md - Claude Code Configuration

This file provides context for AI agents working with this codebase.

## Project Overview

Legislative Skills is a collection of AI agent skills for legislative research and policy analysis. It's designed for use with Claude Code and other AI coding assistants.

## Architecture

### Skills Layer (`skills/`)

Markdown files that define prompts and workflows for specific tasks. Each skill:
- Has YAML frontmatter with `name` and `description`
- Contains step-by-step instructions for the AI
- Specifies output formats and error handling
- References functions from `legiscan_client.py`

### Tools Layer (`tools/`)

Python utilities that interface with the LegiScan API:

**legiscan_client.py** - Core API client
- All API calls go through `_request()` which handles caching
- Responses cached in `~/.legiscan_cache/` to reduce API quota usage
- Monitor hashes stored in `monitor_hashes.json` for change detection
- Personal docket stored in `personal_docket.json`

**generate_dashboard.py** - Flask web dashboard
- Single-page app with Jinja2 templating
- Fetches vote details including individual legislator votes
- Identifies stakeholders based on bill content

**generate_report.py** - PDF report generator
- Uses ReportLab for PDF generation
- Modern styling with status stepper visualization

## Key Functions in legiscan_client.py

### Core API
- `search_bills(query, state, year)` - Search legislation
- `get_bill(bill_id)` - Full bill details
- `get_bill_text(doc_id)` - Bill text content
- `get_roll_call(roll_call_id)` - Vote details
- `get_person(people_id)` - Legislator info

### Monitoring
- `get_monitor_list()` - Bills on GAITS monitor
- `set_monitor(bill_ids, action, stance)` - Add/remove monitoring
- `check_monitor_changes()` - Detect bill changes via hash comparison

### Personal Docket
- `docket_add(bill_id, stance, priority, notes, tags)` - Track a bill
- `docket_remove(bill_id)` - Stop tracking
- `docket_list(filter_by)` - List tracked bills
- `docket_report()` - Status report with change detection

## Environment Variables

- `LEGISCAN_API_KEY` - Required for API access

## Caching Behavior

- API responses cached by request hash
- Cache location: `~/.legiscan_cache/`
- No automatic expiration (manual cache clear if needed)
- Monitor hashes persisted for change detection

## Common Patterns

### Fetching Bill Data
```python
import legiscan_client as lc
bill = lc.get_bill(1423040)
if "error" in bill:
    # Handle error
    pass
```

### Resolving State + Bill Number to ID
```python
results = lc.search_bills("HB1234", "TX", 2)
# Find matching bill in results
```

### Getting Vote Details with Legislator Info
```python
roll_call = lc.get_roll_call(roll_call_id)
for vote in roll_call.get("votes", []):
    person = lc.get_person(vote["people_id"])
    # person has name, party, district
```

## Testing

Use `legiscan test.py` for CLI testing:
```bash
python "legiscan test.py" search "cannabis" CO
python "legiscan test.py" bill 1423040
python "legiscan test.py" docket-list
```

## Style Guidelines

- Skills use clear, structured output formats (tables, sections)
- Python code follows PEP 8
- Error messages are user-friendly
- API errors are handled gracefully with fallbacks
