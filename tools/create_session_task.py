#!/usr/bin/env python3
"""Create a Notion session-recap task in the Progress Tasks DB.

Called by the session-close ritual (Step 6b) after the Google Calendar recap
entry is created. The task appears on the olymp_capital Notion page because the
Class relation is set to the olymp_capital class page.

USAGE
    python tools/create_session_task.py \\
        --title "olymp_capital — Session 8: T13/T15/T16" \\
        --date 2026-06-18 \\
        --link "https://calendar.google.com/calendar/event?eid=..." \\
        --notes "T13: sector pills; T15: percentile cols; T16: composite score"

ENV
    NOTION_TOKEN         internal integration token (secret_xxx)
    NOTION_TASKS_DB_ID   32-char ID of the Progress Tasks database
"""
from __future__ import annotations
import argparse, json, os, sys

try:
    import requests
except ImportError:
    sys.exit("requests not installed -> pip install requests")

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"


def _headers() -> dict:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        sys.exit("NOTION_TOKEN not set")
    return {"Authorization": f"Bearer {token}",
            "Notion-Version": VERSION,
            "Content-Type": "application/json"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a Notion session-recap task.")
    ap.add_argument("--title", required=True, help="Calendar event summary string")
    ap.add_argument("--date", required=True, help="Session date YYYY-MM-DD")
    ap.add_argument("--class-id", required=True, help="Notion page ID of the project's Class entry")
    ap.add_argument("--link", default="", help="Google Calendar event htmlLink URL")
    ap.add_argument("--notes", default="", help="One-line summary of tasks shipped")
    ap.add_argument("--dry-run", action="store_true", help="Print payload, create nothing")
    args = ap.parse_args()

    db = os.environ.get("NOTION_TASKS_DB_ID")
    if not db:
        sys.exit("NOTION_TASKS_DB_ID not set")

    props: dict = {
        "title":              {"title": [{"text": {"content": args.title}}]},
        "Class":              {"relation": [{"id": args.class_id}]},
        "Datum":              {"date": {"start": args.date}},
        "Kontrollkästchen":   {"checkbox": False},
    }
    if args.link:
        props["Links"] = {"url": args.link}
    if args.notes:
        props["Notes"] = {"rich_text": [{"text": {"content": args.notes}}]}

    payload = {"parent": {"database_id": db}, "properties": props}

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    r = requests.post(f"{API}/pages", headers=_headers(), json=payload, timeout=30)
    if r.status_code == 200:
        print(f"Created: {r.json().get('url', '—')}")
        return 0
    print(f"Error [{r.status_code}]: {r.text[:500]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
