#!/usr/bin/env python3
"""
notion_push_tasks.py  ·  Sync between ROADMAP tasks and the Notion Tasks DB (calendar).

RULE (user decision 2026-09-29): a Notion task page exists only when a task has a
calendar slot. Pages come from two places only — the user creates one with a date
(it IS the session input; it gets linked, never duplicated), or `plan-next`
books a slot with the user (`--schedule`). Nothing pushes the open-task list.

WHAT IT DOES
    (default)  sync: ticks the checkbox on pages whose task is now [x] in a ROADMAP.
    --schedule GID START [END]   book a calendar slot: set Datum on the task's page,
               creating the page if the task has none (plan-next only).
    --agenda [DAYS]              this project's dated, unticked pages from today
               for DAYS days (default 1 = today): the session goal / booked slots.
    It NEVER archives or deletes pages and never writes to ROADMAPs itself.
    Two things flow back from Notion, and the session-close ritual turns them
    into ROADMAP / CHANGELOG edits by hand:
      · `--checked` — pages ticked in Notion whose task is still open;
      · `--inbox`   — planning input: pages of this project's Class that have no
        task_key yet (tasks and notes you created in Notion). Once session-close
        has turned one into a ROADMAP task (open) or CHANGELOG entry (done),
        `--link PAGE_ID GID` writes the task_key back so it is not ingested twice.

SETUP
    pip install requests
    NOTION_TOKEN          internal integration token (global env var)
    NOTION_TASKS_DB_ID    32-char id of the Tasks DB (global env var)
    NOTION_CLASS_PAGE_ID  per-project class page — in .claude/project.env
    .claude/project.env is read automatically (KEY=VALUE lines) for any variable
    not already set, so no `source` is needed (works on Windows too).
    The integration must be shared with the DB: open the DB in Notion ->
    ··· menu -> Connections -> add your integration.

USAGE
    python tools/notion_push_tasks.py --inspect          # print DB schema (connection test)
    python tools/notion_push_tasks.py --dry-run          # show which pages would be ticked
    python tools/notion_push_tasks.py                    # tick pages of done tasks
    python tools/notion_push_tasks.py --agenda           # today's dated tasks (session goal)
    python tools/notion_push_tasks.py --agenda 7         # booked slots for the next 7 days
    python tools/notion_push_tasks.py --schedule oc_dashboard.T141 2026-10-01T14:00 2026-10-01T16:00
    python tools/notion_push_tasks.py --checked          # list open tasks ticked in Notion
    python tools/notion_push_tasks.py --inbox --since 2026-09-15  # Notion-born items not yet in git
    python tools/notion_push_tasks.py --link <page> <gid>  # mark an inbox page as ingested

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

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"
TITLE_MAX = 120      # page titles are truncated; the full title goes into Notes
RICH_TEXT_MAX = 2000  # Notion's per-text-object limit

# --- Map your Notion DB property names here (see --inspect output) -------------
# Set a value to "" to skip that property.
PROPERTY_MAP = {
    "title":    "title",             # title property
    "task_key": "task_key",          # rich_text: global task id (gid) used for matching
    "blocks":   "blocks",            # rich_text: ids this task unlocks
    "notes":    "Notes",             # rich_text: full title + needs/waiting_on
    "class":    "Class",             # relation → project class page
    "done":     "Kontrollkästchen",  # checkbox: ticked when the task is [x]
    "date":     "Datum",             # date (optionally with a time range): the calendar slot
}
TZ = "Europe/Berlin"
# ------------------------------------------------------------------------------


def load_project_env(path: Path = Path(".claude/project.env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.removeprefix("export ").partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def env(name: str, hint: str = "") -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"{name} not set{(' — ' + hint) if hint else ''}")
    return v


def headers() -> dict:
    return {"Authorization": f"Bearer {env('NOTION_TOKEN')}",
            "Notion-Version": VERSION,
            "Content-Type": "application/json"}


def db_id() -> str:
    return env("NOTION_TASKS_DB_ID")


def class_id() -> str:
    return env("NOTION_CLASS_PAGE_ID", "add to .claude/project.env")


def inspect() -> None:
    r = requests.get(f"{API}/databases/{db_id()}", headers=headers(), timeout=30)
    if r.status_code != 200:
        sys.exit(f"connection failed [{r.status_code}]: {r.text[:300]}")
    props = r.json().get("properties", {})
    print("Connection OK. DB properties:")
    for name, meta in props.items():
        print(f"  · {name}  ({meta.get('type')})")
    print("\nSet PROPERTY_MAP at the top of this file to match these names.")


def query_existing() -> dict[str, dict]:
    """Return {task_key: {"id", "checked"}} for non-archived pages, paginating fully."""
    out: dict[str, dict] = {}
    payload: dict = {"page_size": 100}
    key_prop, done_prop = PROPERTY_MAP["task_key"], PROPERTY_MAP.get("done")
    while True:
        r = requests.post(f"{API}/databases/{db_id()}/query",
                          headers=headers(), json=payload, timeout=30)
        if r.status_code != 200:
            sys.exit(f"query failed [{r.status_code}]: {r.text[:300]}")
        data = r.json()
        for page in data["results"]:
            props = page["properties"]
            rt = props.get(key_prop, {}).get("rich_text", [])
            key = rt[0]["plain_text"] if rt else None
            if key:
                checked = bool(props.get(done_prop, {}).get("checkbox")) if done_prop else False
                out[key] = {"id": page["id"], "checked": checked}
        if not data.get("has_more"):
            return out
        payload["start_cursor"] = data["next_cursor"]


def query_inbox(since: str | None = None) -> list[dict]:
    """Pages of this project's Class with an empty task_key: Notion-born input."""
    out: list[dict] = []
    payload: dict = {"page_size": 100, "filter": {"and": [
        {"property": PROPERTY_MAP["class"], "relation": {"contains": class_id()}},
        {"property": PROPERTY_MAP["task_key"], "rich_text": {"is_empty": True}},
    ]}}
    if since:
        payload["filter"]["and"].append(
            {"timestamp": "last_edited_time", "last_edited_time": {"on_or_after": since}})
    while True:
        r = requests.post(f"{API}/databases/{db_id()}/query",
                          headers=headers(), json=payload, timeout=30)
        if r.status_code != 200:
            sys.exit(f"inbox query failed [{r.status_code}]: {r.text[:300]}")
        data = r.json()
        for page in data["results"]:
            props = page["properties"]
            title = "".join(t["plain_text"] for t in props.get(PROPERTY_MAP["title"], {}).get("title", []))
            notes = "".join(t["plain_text"] for t in props.get(PROPERTY_MAP.get("notes") or "", {}).get("rich_text", []))
            done_prop = PROPERTY_MAP.get("done")
            out.append({
                "id": page["id"], "url": page.get("url", ""), "title": title,
                "checked": bool(props.get(done_prop, {}).get("checkbox")) if done_prop else False,
                "notes": notes, "edited": page.get("last_edited_time", "")[:10],
            })
        if not data.get("has_more"):
            return out
        payload["start_cursor"] = data["next_cursor"]


def link_page(page_id: str, gid: str) -> None:
    r = requests.patch(f"{API}/pages/{page_id}", headers=headers(), timeout=30,
                       json={"properties": {PROPERTY_MAP["task_key"]: {"rich_text": _text(gid)}}})
    if r.status_code != 200:
        sys.exit(f"link failed [{r.status_code}]: {r.text[:300]}")
    print(f"linked {page_id} -> {gid}")


def _datum(start: str, end: str | None) -> dict:
    """Naive ISO datetimes are Berlin local time (Notion applies time_zone)."""
    d = {"start": start, "end": end}
    if "T" in start:
        d["time_zone"] = TZ
    return {"date": d}


def schedule(gid: str, start: str, end: str | None, open_tasks: dict[str, dict], dry: bool) -> None:
    if gid not in open_tasks:
        sys.exit(f"{gid} is not an open task in any ROADMAP — nothing to schedule")
    existing = query_existing()
    slot = start + (f" -> {end}" if end else "")
    if dry:
        print(f"would {'update' if gid in existing else 'create'} {gid} at {slot}")
        return
    if gid in existing:
        r = requests.patch(f"{API}/pages/{existing[gid]['id']}", headers=headers(), timeout=30,
                           json={"properties": {PROPERTY_MAP["date"]: _datum(start, end)}})
    else:
        props = task_properties(open_tasks[gid])
        props[PROPERTY_MAP["date"]] = _datum(start, end)
        r = requests.post(f"{API}/pages", headers=headers(), timeout=30,
                          json={"parent": {"database_id": db_id()}, "properties": props})
    if r.status_code != 200:
        sys.exit(f"schedule failed [{r.status_code}]: {r.text[:300]}")
    print(f"scheduled {gid} at {slot}: {r.json().get('url', '')}")


def agenda(days: int) -> None:
    from datetime import date, timedelta
    first, last = date.today(), date.today() + timedelta(days=days - 1)
    payload = {"page_size": 100,
               "sorts": [{"property": PROPERTY_MAP["date"], "direction": "ascending"}],
               "filter": {"and": [
                   {"property": PROPERTY_MAP["class"], "relation": {"contains": class_id()}},
                   {"property": PROPERTY_MAP["date"], "date": {"on_or_after": first.isoformat()}},
                   {"property": PROPERTY_MAP["date"], "date": {"on_or_before": last.isoformat()}},
                   {"property": PROPERTY_MAP["done"], "checkbox": {"equals": False}},
               ]}}
    r = requests.post(f"{API}/databases/{db_id()}/query", headers=headers(), json=payload, timeout=30)
    if r.status_code != 200:
        sys.exit(f"agenda query failed [{r.status_code}]: {r.text[:300]}")
    pages = r.json()["results"]
    span = str(first) if days == 1 else f"{first} .. {last}"
    print(f"{len(pages)} dated task(s) {span}:")
    for page in pages:
        pr = page["properties"]
        d = pr[PROPERTY_MAP["date"]]["date"]
        when = d["start"].replace("T", " ")[:16]
        if d.get("end") and "T" in d["end"]:
            when += " - " + d["end"][11:16]
        key = "".join(t["plain_text"] for t in pr[PROPERTY_MAP["task_key"]]["rich_text"])
        key = key or "(unlinked: ingest, then --link)"
        title = "".join(t["plain_text"] for t in pr[PROPERTY_MAP["title"]]["title"])
        notes = "".join(t["plain_text"] for t in pr.get(PROPERTY_MAP["notes"], {}).get("rich_text", []))
        print(f"  {when:22} {key:30} {title[:70]}  (page {page['id']})")
        if notes:
            print(f"        notes: {notes[:200]}")


def _text(s: str, limit: int = RICH_TEXT_MAX) -> list[dict]:
    return [{"text": {"content": s[:limit]}}]


def page_title(task: dict) -> str:
    title = task["title"] or ""
    if len(title) > TITLE_MAX:
        title = title[:TITLE_MAX - 1].rstrip() + "…"
    return f"{task['gid']} — {title}" if title else task["gid"]


def task_properties(task: dict) -> dict:
    p = {
        PROPERTY_MAP["title"]: {"title": _text(page_title(task))},
        PROPERTY_MAP["task_key"]: {"rich_text": _text(task["gid"])},
    }
    if PROPERTY_MAP.get("blocks"):
        p[PROPERTY_MAP["blocks"]] = {"rich_text": _text(", ".join(task.get("blocks", [])))}
    if PROPERTY_MAP.get("notes"):
        lines = [task["title"] or ""]
        lines.append("needs: " + (", ".join(task.get("needs", [])) or "—"))
        if task.get("waiting_on"):
            lines.append("waiting on: " + ", ".join(task["waiting_on"]))
        p[PROPERTY_MAP["notes"]] = {"rich_text": _text("\n".join(lines))}
    if PROPERTY_MAP.get("class"):
        p[PROPERTY_MAP["class"]] = {"relation": [{"id": class_id()}]}
    if PROPERTY_MAP.get("done"):
        p[PROPERTY_MAP["done"]] = {"checkbox": False}
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync ROADMAP tasks with the Notion Tasks DB (calendar).")
    ap.add_argument("--inspect", action="store_true", help="print DB schema and exit")
    ap.add_argument("--dry-run", action="store_true", help="show changes, make none")
    ap.add_argument("--agenda", nargs="?", type=int, const=1, metavar="DAYS",
                    help="list this project's dated, unticked pages for DAYS days from today (default 1)")
    ap.add_argument("--schedule", nargs="+", metavar="GID_START_END",
                    help="GID START [END] (ISO, Berlin time): book a calendar slot for an open task")
    ap.add_argument("--checked", action="store_true",
                    help="list open tasks ticked in Notion (for session-close reconcile) and exit")
    ap.add_argument("--inbox", action="store_true",
                    help="list this project's Notion pages that have no task_key yet, and exit")
    ap.add_argument("--since", metavar="YYYY-MM-DD",
                    help="with --inbox: only pages edited on/after this date (session-close passes "
                         "the last status-file regeneration date)")
    ap.add_argument("--link", nargs=2, metavar=("PAGE_ID", "GID"),
                    help="write GID into an inbox page's task_key, and exit")
    ap.add_argument("--ready", default="docs/roadmap_frontier.json")
    args = ap.parse_args()

    load_project_env()
    if args.inspect:
        inspect()
        return 0
    if args.link:
        link_page(*args.link)
        return 0
    if args.agenda:
        agenda(args.agenda)
        return 0
    if args.inbox:
        items = query_inbox(args.since)
        print(f"{len(items)} Notion inbox item(s) not yet in git:")
        for it in items:
            mark = "x" if it["checked"] else " "
            print(f"  [{mark}] {it['title'][:90]}  (edited {it['edited']}, page {it['id']})")
            if it["notes"]:
                print(f"        notes: {it['notes'][:160]}")
        return 0

    data = json.loads(Path(args.ready).read_text(encoding="utf-8"))
    if "done" not in data:
        sys.exit(f"{args.ready} has no 'done' list — update tools/roadmap_frontier.py and re-run it")
    open_tasks = {t["gid"]: t for t in data["ready"] + data["blocked"] + data.get("held", [])}
    if args.schedule:
        if len(args.schedule) not in (2, 3):
            sys.exit("--schedule GID START [END]")
        end = args.schedule[2] if len(args.schedule) == 3 else None
        schedule(args.schedule[0], args.schedule[1], end, open_tasks, args.dry_run)
        return 0
    done = set(data["done"])
    existing = query_existing()

    if args.checked:
        hits = sorted(g for g, pg in existing.items() if pg["checked"] and g in open_tasks)
        print(f"{len(hits)} open task(s) ticked in Notion:")
        for g in hits:
            print(f"  ✓ {g}  {open_tasks[g]['title'][:90]}")
        return 0

    to_tick = [(gid, pg["id"]) for gid, pg in existing.items()
               if gid in done and not pg["checked"]] if PROPERTY_MAP.get("done") else []
    # `review:` keys belong to session-summary pages, not ROADMAP tasks
    orphans = [gid for gid in existing
               if gid not in open_tasks and gid not in done and not gid.startswith("review:")]

    print(f"in_notion={len(existing)}  tick={len(to_tick)}  orphans={len(orphans)} (left alone)")

    if args.dry_run:
        for gid, _ in to_tick:
            print(f"  ✓ tick   {gid}")
        for gid in orphans:
            print(f"  ? orphan {gid} (not in any ROADMAP — untouched)")
        return 0

    for gid, pid in to_tick:
        r = requests.patch(f"{API}/pages/{pid}", headers=headers(), timeout=30,
                           json={"properties": {PROPERTY_MAP["done"]: {"checkbox": True}}})
        print(f"  ✓ {gid}: {'ticked' if r.status_code == 200 else r.text[:200]}")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
