#!/usr/bin/env python3
"""
notion_sync.py  ·  One-way projection of the ready frontier into Notion.

WHAT IT DOES
    Reads docs/ready_set.json and reconciles the ready frontier into a Notion
    database (your "Progress Tasks" DB):
      · creates a Notion page for each ready task not already there,
      · archives Notion pages whose task left the frontier (done or newly blocked).
    It NEVER reads task status back from Notion. ROADMAPs are the only truth.
    (Completion of your own tasks comes back via the checkbox-relay in the
    session-close ritual, not from this script.)

SETUP
    pip install requests
    export NOTION_TOKEN="secret_xxx"              # internal integration token (global)
    export NOTION_TASKS_DB_ID="<database id>"     # 32-char id of Progress Tasks DB (global)
    export NOTION_CLASS_PAGE_ID="<page id>"       # per-project class page — also in .claude/project.env
    The integration must be shared with the DB: open the DB in Notion ->
    ··· menu -> Connections -> add your integration.

USAGE
    python tools/notion_sync.py --inspect     # print the DB schema (also a connection test)
    python tools/notion_sync.py --dry-run      # show what would change, change nothing
    python tools/notion_sync.py                # reconcile for real

CONFIGURE the PROPERTY_MAP below to match your DB's exact property names.
Run --inspect first to see them.
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests not installed -> pip install requests")

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"

# --- Map your Notion DB property names here (see --inspect output) -------------
PROPERTY_MAP = {
    "title":       "title",       # the title property
    "task_key":    "task_key",    # rich_text: stores the global task id (gid) for matching
    "sub_project": "",            # relation in this DB — skipped (can't write page IDs)
    "status":      "",             # select with no options configured — skipped
    "blocks":      "blocks",      # rich_text (optional; set to "" to skip)
    "class":       "Class",       # relation → olymp_capital class page (makes tasks visible on project page)
}
READY_STATUS_VALUE = "Ready"      # the Status value projected tasks get
# ------------------------------------------------------------------------------


def headers() -> dict:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        sys.exit("NOTION_TOKEN not set")
    return {"Authorization": f"Bearer {token}",
            "Notion-Version": VERSION,
            "Content-Type": "application/json"}


def db_id() -> str:
    v = os.environ.get("NOTION_TASKS_DB_ID")
    if not v:
        sys.exit("NOTION_TASKS_DB_ID not set")
    return v


def class_id() -> str:
    v = os.environ.get("NOTION_CLASS_PAGE_ID")
    if not v:
        sys.exit("NOTION_CLASS_PAGE_ID not set — add to .claude/project.env")
    return v


def inspect() -> None:
    r = requests.get(f"{API}/databases/{db_id()}", headers=headers(), timeout=30)
    if r.status_code != 200:
        sys.exit(f"connection failed [{r.status_code}]: {r.text[:300]}")
    props = r.json().get("properties", {})
    print("Connection OK. DB properties:")
    for name, meta in props.items():
        print(f"  · {name}  ({meta.get('type')})")
    print("\nSet PROPERTY_MAP at the top of this file to match these names.")


def query_existing() -> dict[str, str]:
    """Return {task_key: page_id} for non-archived pages, paginating fully."""
    out: dict[str, str] = {}
    payload: dict = {"page_size": 100}
    key_prop = PROPERTY_MAP["task_key"]
    while True:
        r = requests.post(f"{API}/databases/{db_id()}/query",
                          headers=headers(), json=payload, timeout=30)
        if r.status_code != 200:
            sys.exit(f"query failed [{r.status_code}]: {r.text[:300]}")
        data = r.json()
        for page in data["results"]:
            rt = page["properties"].get(key_prop, {}).get("rich_text", [])
            key = rt[0]["plain_text"] if rt else None
            if key:
                out[key] = page["id"]
        if not data.get("has_more"):
            return out
        payload["start_cursor"] = data["next_cursor"]


def task_properties(task: dict) -> dict:
    p = {
        PROPERTY_MAP["title"]: {"title": [{"text": {"content": task["title"] or task["gid"]}}]},
        PROPERTY_MAP["task_key"]: {"rich_text": [{"text": {"content": task["gid"]}}]},
    }
    if PROPERTY_MAP.get("status"):
        p[PROPERTY_MAP["status"]] = {"select": {"name": READY_STATUS_VALUE}}
    if PROPERTY_MAP.get("sub_project"):
        p[PROPERTY_MAP["sub_project"]] = {"select": {"name": task["sub_project"]}}
    if PROPERTY_MAP.get("blocks"):
        unlocks = ", ".join(task.get("blocks", []))
        p[PROPERTY_MAP["blocks"]] = {"rich_text": [{"text": {"content": unlocks}}]}
    if PROPERTY_MAP.get("class"):
        p[PROPERTY_MAP["class"]] = {"relation": [{"id": class_id()}]}
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="Project the ready frontier into Notion.")
    ap.add_argument("--inspect", action="store_true", help="print DB schema and exit")
    ap.add_argument("--dry-run", action="store_true", help="show changes, make none")
    ap.add_argument("--ready", default="docs/ready_set.json")
    args = ap.parse_args()

    if args.inspect:
        inspect()
        return 0

    data = json.loads(Path(args.ready).read_text(encoding="utf-8"))
    frontier = {t["gid"]: t for t in data["ready"]}
    existing = query_existing()

    to_create = [t for gid, t in frontier.items() if gid not in existing]
    to_archive = [(gid, pid) for gid, pid in existing.items() if gid not in frontier]

    print(f"frontier={len(frontier)}  in_notion={len(existing)}  "
          f"create={len(to_create)}  archive={len(to_archive)}")

    if args.dry_run:
        for t in to_create:
            print(f"  + create {t['gid']}  {t['title']}")
        for gid, _ in to_archive:
            print(f"  - archive {gid}")
        return 0

    for t in to_create:
        r = requests.post(f"{API}/pages", headers=headers(), timeout=30, json={
            "parent": {"database_id": db_id()},
            "properties": task_properties(t)})
        print(f"  + {t['gid']}: {'ok' if r.status_code == 200 else r.text[:200]}")

    for gid, pid in to_archive:
        r = requests.patch(f"{API}/pages/{pid}", headers=headers(), timeout=30,
                           json={"archived": True})
        print(f"  - {gid}: {'archived' if r.status_code == 200 else r.text[:200]}")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
