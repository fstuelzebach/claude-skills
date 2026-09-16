---
name: push-tasks
description: Project the project's open ROADMAP tasks into the Notion Tasks database as pages (create-only), so they can be scheduled by hand in Notion. Default pushes the ready frontier; "push-tasks all" pushes every unchecked task including blocked ones. Use as Step 8 of session-close, or when the user says "push tasks", "push todos", "push tasks to notion", or "sync tasks".
---

# Push open tasks to Notion

A one-way, **create-only** projection of open tasks into the Notion Tasks DB.
ROADMAPs are the truth; Notion is where the user decides *when* to do things.

**Before starting:** read `## Claude Skills Config` in `CLAUDE.md` to resolve
`{tasks_push_script}` (default `python tools/notion_push_tasks.py`) and `{frontier_output}`
(default `docs/roadmap_frontier.json`). The script reads `.claude/project.env`
(`NOTION_CLASS_PAGE_ID`) itself; `NOTION_TOKEN` and `NOTION_TASKS_DB_ID` come from
the global environment.

## What a pushed page looks like
- **title** `{task-id} — {title}` (long titles truncated; the full title is in Notes)
- **task_key** the global task id — the only matching key
- **Class** → the project's class page
- **Notes** full title, `needs:`, and `waiting on:` for blocked tasks
- **Kontrollkästchen** unchecked
- **Datum** left empty — scheduling is done by hand in Notion

## Procedure
1. Make sure `{frontier_output}` is fresh — run the frontier script first if this
   is not already Step 8 of `session-close`.
2. **Preview:**
   ```bash
   {tasks_push_script} --dry-run            # ready frontier
   {tasks_push_script} --dry-run --all      # when invoked as "push-tasks all"
   ```
   Show the user the summary line (create / tick / orphans).
3. **Push** with the same arguments minus `--dry-run`. No extra confirmation is
   needed inside `session-close`; when invoked on its own and more than ~15 pages
   would be created, confirm first.
4. **Report** one line: created N, ticked M, orphans K (left alone).

## What it never does
- Never archives or deletes pages — a task that became blocked keeps its page and
  any date the user set.
- Never writes dates, and never writes to ROADMAPs.
- Orphans (pages whose task id is in no ROADMAP) are listed, not touched. Mention
  them so the user can tidy up by hand.

## The return path
Notion is a golden source for planning, so two things flow back — both handled
by `session-close` Step 1, never by this skill:
- `{tasks_push_script} --checked` — open tasks ticked in Notion (a completion
  signal; confirmed with the user, then flipped to `[x]` in the ROADMAP).
- `{tasks_push_script} --inbox --since DATE` — pages created or edited in Notion
  that are not linked to a task yet; each becomes a ROADMAP task or CHANGELOG
  entry, then `--link PAGE_ID GID` marks it ingested.

If `NOTION_TOKEN` / `NOTION_TASKS_DB_ID` / `NOTION_CLASS_PAGE_ID` is missing, STOP
and point the user to setup — never invent an id.
