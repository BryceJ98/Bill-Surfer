"""
legiscan test.py
----------------
CLI tool for testing the LegiScan API.
All API logic lives in legiscan_client.py — this file is the command-line interface.

Usage:
    python "legiscan test.py" search <query> [state] [year]
    python "legiscan test.py" bill <bill_id>
    python "legiscan test.py" text <bill_id>
    python "legiscan test.py" rollcall <roll_call_id>
    python "legiscan test.py" sessions <state>
    python "legiscan test.py" sponsor <people_id>

Docket commands:
    python "legiscan test.py" docket-add <bill_id> [stance] [priority]
    python "legiscan test.py" docket-remove <bill_id>
    python "legiscan test.py" docket-list [state|priority|stance]
    python "legiscan test.py" docket-report
    python "legiscan test.py" docket-view <bill_id>

Monitoring commands:
    python "legiscan test.py" monitor-list
    python "legiscan test.py" monitor-add <bill_id> [stance]
    python "legiscan test.py" monitor-remove <bill_id>
    python "legiscan test.py" check-updates

Examples:
    python "legiscan test.py" search "sports wagering" KS 1
    python "legiscan test.py" bill 1423040
    python "legiscan test.py" docket-add 1423040 support high
    python "legiscan test.py" docket-report
"""

import sys
import json
import legiscan_client as lc


def cmd_search(args):
    if not args:
        print("Usage: search <query> [state] [year]")
        sys.exit(1)
    query = args[0]
    state = args[1].upper() if len(args) > 1 else "ALL"
    year  = int(args[2]) if len(args) > 2 else 2
    result = lc.search_bills(query, state, year)
    print(json.dumps(result, indent=2))


def cmd_bill(args):
    if not args:
        print("Usage: bill <bill_id>")
        sys.exit(1)
    bill = lc.get_bill(int(args[0]))
    # Print a concise summary rather than the full raw record
    if "error" in bill:
        print(json.dumps(bill, indent=2))
        return
    summary = {
        "bill_id":      bill.get("bill_id"),
        "bill_number":  bill.get("bill_number"),
        "title":        bill.get("title"),
        "state":        bill.get("state"),
        "status":       lc.status_label(bill.get("status", 0)),
        "last_action":  bill.get("last_action"),
        "url":          bill.get("url"),
        "sponsors":     [s.get("name") for s in bill.get("sponsors", [])],
        "texts":        [{"doc_id": t["doc_id"], "type": t["type"]}
                         for t in bill.get("texts", [])],
        "votes":        [{"roll_call_id": v["roll_call_id"], "desc": v["desc"],
                          "yea": v["yea"], "nay": v["nay"]}
                         for v in bill.get("votes", [])],
        "fiscal_notes": [s.get("description") for s in bill.get("supplements", [])
                         if s.get("type_id") == 1],
    }
    print(json.dumps(summary, indent=2))


def cmd_text(args):
    if not args:
        print("Usage: text <bill_id>")
        sys.exit(1)
    result = lc.get_bill_text_latest(int(args[0]))
    if "error" in result:
        print(json.dumps(result, indent=2))
        return
    # Print metadata + first 3000 chars of text
    print(f"Type:       {result.get('type')}")
    print(f"Date:       {result.get('date')}")
    print(f"MIME:       {result.get('mime')}")
    print(f"Size:       {result.get('text_size', 0):,} bytes")
    print(f"State URL:  {result.get('state_link')}")
    print("-" * 60)
    text = result.get("text", "")
    print(text[:3000])
    if len(text) > 3000:
        print(f"\n... [{len(text) - 3000:,} more characters] ...")


def cmd_rollcall(args):
    if not args:
        print("Usage: rollcall <roll_call_id>")
        sys.exit(1)
    rc = lc.get_roll_call(int(args[0]))
    print(json.dumps(rc, indent=2))


def cmd_sessions(args):
    if not args:
        print("Usage: sessions <state>")
        sys.exit(1)
    sessions = lc.get_session_list(args[0])
    print(json.dumps(sessions, indent=2))


def cmd_sponsor(args):
    if not args:
        print("Usage: sponsor <people_id>")
        sys.exit(1)
    person = lc.get_sponsor(int(args[0]))
    print(json.dumps(person, indent=2))


# ── Docket commands ────────────────────────────────────────────────────────────

def cmd_docket_add(args):
    if not args:
        print("Usage: docket-add <bill_id> [stance] [priority]")
        print("  stance: watch, support, oppose (default: watch)")
        print("  priority: high, medium, low (default: medium)")
        sys.exit(1)
    bill_id = int(args[0])
    stance = args[1] if len(args) > 1 else "watch"
    priority = args[2] if len(args) > 2 else "medium"
    result = lc.docket_add(bill_id, stance=stance, priority=priority)
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    entry = result["entry"]
    bill = result["bill"]
    print(f"Added to docket: {entry['state']} {entry['bill_number']}")
    print(f"  Title:    {entry['title'][:60]}...")
    print(f"  Stance:   {entry['stance']}")
    print(f"  Priority: {entry['priority']}")
    print(f"  Status:   {bill['status']}")
    print(f"  URL:      {bill['url']}")


def cmd_docket_remove(args):
    if not args:
        print("Usage: docket-remove <bill_id>")
        sys.exit(1)
    bill_id = int(args[0])
    result = lc.docket_remove(bill_id)
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    print(f"Removed from docket: {result['state']} {result['bill_number']}")


def cmd_docket_list(args):
    filter_by = None
    if args:
        arg = args[0].lower()
        if arg in ("high", "medium", "low"):
            filter_by = {"priority": arg}
        elif arg in ("watch", "support", "oppose"):
            filter_by = {"stance": arg}
        elif len(arg) == 2:
            filter_by = {"state": arg.upper()}

    result = lc.docket_list(filter_by)
    print(f"Docket: {result['count']} bills")
    if result.get("last_checked"):
        print(f"Last checked: {result['last_checked'][:19]}")
    print("-" * 80)
    for entry in result["bills"]:
        print(f"[{entry['priority'].upper():6}] {entry['state']} {entry['bill_number']:10} "
              f"({entry['stance']:7}) - {entry['title'][:40]}...")
    if not result["bills"]:
        print("  (empty)")


def cmd_docket_report(args):
    result = lc.docket_report()
    if result["count"] == 0:
        print("Your docket is empty. Add bills with: docket-add <bill_id>")
        return

    summary = result["summary"]
    print(f"DOCKET REPORT — {result['count']} bills, {summary['changed']} changed")
    print(f"Checked: {result['checked_at'][:19]}")
    print("=" * 80)

    for item in result["bills"]:
        entry = item["entry"]
        current = item.get("current", {})
        changed = "***" if item["has_changed"] else "   "

        print(f"\n{changed} [{entry['priority'].upper()}] {entry['state']} {entry['bill_number']} ({entry['stance']})")
        print(f"    {entry['title'][:65]}")
        if current:
            print(f"    Status: {current['status']} | Last: {current['last_action_date']} - {current['last_action'][:40]}")
        if entry.get("notes"):
            print(f"    Notes: {entry['notes']}")

    print("\n" + "=" * 80)
    print(f"By priority: high={summary['by_priority']['high']}, "
          f"medium={summary['by_priority']['medium']}, low={summary['by_priority']['low']}")
    print(f"By stance: support={summary['by_stance']['support']}, "
          f"oppose={summary['by_stance']['oppose']}, watch={summary['by_stance']['watch']}")


def cmd_docket_view(args):
    if not args:
        print("Usage: docket-view <bill_id>")
        sys.exit(1)
    bill_id = int(args[0])
    result = lc.docket_get(bill_id)
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    entry = result["entry"]
    current = result.get("current", {})
    changed = "YES" if result["has_changed"] else "No"

    print(f"{entry['state']} {entry['bill_number']}")
    print(f"Title: {entry['title']}")
    print("-" * 60)
    print(f"Stance:   {entry['stance']}")
    print(f"Priority: {entry['priority']}")
    print(f"Added:    {entry['added_date'][:10]}")
    print(f"Notes:    {entry.get('notes') or '—'}")
    print(f"Tags:     {', '.join(entry.get('tags', [])) or '—'}")
    print("-" * 60)
    if current:
        print(f"Status:      {current['status']}")
        print(f"Last Action: {current['last_action_date']} - {current['last_action']}")
        print(f"Changed:     {changed}")
        print(f"URL:         {current['url']}")


# ── Monitor commands ───────────────────────────────────────────────────────────

def cmd_monitor_list(args):
    result = lc.get_monitor_list()
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    print(f"Monitor list: {result['count']} bills")
    print("-" * 60)
    for bill in result.get("bills", []):
        b = bill.get("bill", bill)
        stance = lc.stance_label(b.get("stance", 0))
        print(f"  {b.get('state', '??')} {b.get('number', '?'):10} ({stance:7}) - {b.get('title', '?')[:40]}...")


def cmd_monitor_add(args):
    if not args:
        print("Usage: monitor-add <bill_id> [stance]")
        print("  stance: watch, support, oppose (default: watch)")
        sys.exit(1)
    bill_id = int(args[0])
    stance = args[1] if len(args) > 1 else "watch"
    result = lc.set_monitor([bill_id], action="monitor", stance=stance)
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    print(f"Added bill {bill_id} to monitor list with stance: {stance}")


def cmd_monitor_remove(args):
    if not args:
        print("Usage: monitor-remove <bill_id>")
        sys.exit(1)
    bill_id = int(args[0])
    result = lc.set_monitor([bill_id], action="remove")
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    print(f"Removed bill {bill_id} from monitor list")


def cmd_check_updates(args):
    result = lc.check_monitor_changes()
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    print(f"Monitor check: {result['total']} bills")
    print(f"  Changed: {len(result['changed'])}")
    print(f"  New:     {len(result['new'])}")
    print(f"  Unchanged: {result['unchanged_count']}")

    if result["changed"]:
        print("\nChanged bills:")
        for bill in result["changed"]:
            print(f"  - {bill.get('state')} {bill.get('number')} (status: {bill.get('status')})")

    if result["new"]:
        print("\nNewly tracked:")
        for bill in result["new"]:
            print(f"  - {bill.get('state')} {bill.get('number')}")


COMMANDS = {
    "search":   cmd_search,
    "bill":     cmd_bill,
    "text":     cmd_text,
    "rollcall": cmd_rollcall,
    "sessions": cmd_sessions,
    "sponsor":  cmd_sponsor,
    # Docket commands
    "docket-add":    cmd_docket_add,
    "docket-remove": cmd_docket_remove,
    "docket-list":   cmd_docket_list,
    "docket-report": cmd_docket_report,
    "docket-view":   cmd_docket_view,
    # Monitor commands
    "monitor-list":   cmd_monitor_list,
    "monitor-add":    cmd_monitor_add,
    "monitor-remove": cmd_monitor_remove,
    "check-updates":  cmd_check_updates,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
