---
name: push-tasks
description: Sync ROADMAP completion into the Notion Tasks DB — tick the pages of tasks that are now done — and read the calendar (agenda). It never creates pages for open tasks; pages exist only for calendar slots (created by the user, or booked via plan-next). Use as Step 5 of session-close, or when the user says "push tasks", "sync tasks", "sync notion tasks", or asks what is booked / what today's session is for.
---

# Notion task sync

**Rule (user decision 2026-09-29):** a Notion task page exists only when a task
has a calendar slot. Pages come from exactly two places:
- the **user** creates one with a date — it is the input for that session and is
  linked to a ROADMAP task (`--link`), never duplicated;
- **`plan-next`** books a slot with the user (`--schedule`).
Nothing projects the open-task list into Notion.

**Before starting:** read `## Claude Skills Config` in `CLAUDE.md` to resolve
`{tasks_push_script}` (default `python tools/notion_push_tasks.py`) and
`{frontier_output}` (default `docs/roadmap_frontier.json`). `NOTION_TOKEN` and
`NOTION_TASKS_DB_ID` come from the global environment, `NOTION_CLASS_PAGE_ID` from
`.claude/project.env`.

## Sync (Step 5 of session-close)
1. Make sure `{frontier_output}` is fresh (run the frontier script if needed).
2. `{tasks_push_script} --dry-run` → one summary line (tick / orphans).
3. `{tasks_push_script}` → ticks pages whose task is now `[x]`.
4. Report one line: ticked N, orphans K (left alone — pages whose task id is in no
   ROADMAP; mention them so the user can tidy up by hand).

## Agenda (session goal)
- `{tasks_push_script} --agenda` — this project's dated, unticked pages for today.
  At the start of a session, these are the session's goal: read each page (it may
  hold notes or a list). An unlinked page is ingested like `session-close` Step 1
  (propose task / note → confirm → `--link`).
- `{tasks_push_script} --agenda 14` — booked slots for the next 14 days.

## What it never does
- Never creates pages for open tasks (only `plan-next` books slots).
- Never archives or deletes pages; never changes a date the user set.
- Never writes to ROADMAPs — completion signals (`--checked`) and Notion-born
  pages (`--inbox`) are turned into ROADMAP edits by `session-close` Step 1.

If `NOTION_TOKEN` / `NOTION_TASKS_DB_ID` / `NOTION_CLASS_PAGE_ID` is missing, STOP
and point the user to setup — never invent an id.
