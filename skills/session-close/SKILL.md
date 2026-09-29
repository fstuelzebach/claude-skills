---
name: session-close
description: "Run the end-of-session bookkeeping for the project: ingest Notion input, reconcile ROADMAPs/CHANGELOGs, check the task graph with code, regenerate the status file, tick done tasks in Notion, commit and push with a clean working tree, and mirror docs. It never asks what to do next and never creates Notion task pages — that is plan-next, and only when the user asks. Use when the user says 'close the session', 'refresh the status', 'wrap up', 'where are we', or at the end of a work block."
---

# Session Close

Bookkeeping only: after it, git and Notion reflect everything that happened, and
nothing has been decided about the future. **Do not ask what to work on next, do
not propose tracks or dates, do not create Notion task pages.** Planning is the
separate `plan-next` skill and runs only when the user asks for it.

This is the ONLY way the status file is written. Read the project's Working
Protocol (`CLAUDE.md` and the workflow doc it points to) first.

**Before starting:** read the `## Claude Skills Config` section in `CLAUDE.md` to
resolve every `{placeholder}` below. Defaults:

| key | default |
|---|---|
| `{frontier_script}` | `python tools/roadmap_frontier.py` |
| `{frontier_output}` | `docs/roadmap_frontier.json` |
| `{status_file}` | `PROJECT_STATUS.md` |
| `{packets_dir}` | `docs/packets` |
| `{tasks_push_script}` | `python tools/notion_push_tasks.py` |
| `{archive_script}` | `python tools/archive_done_tasks.py` |

**Two golden sources.** Git holds execution truth (ROADMAP = open work,
CHANGELOG = finished work, code). Notion holds planning: the user's own pages and
the calendar. **A Notion task page exists only when a task has a calendar slot**
— either the user created it with a date, or `plan-next` booked it with the user.

## Step 0 — Working tree check
Run `git status --short`. Every change must end this session in a commit (Step 6).
List anything that is not this session's work and ask the user what to do with it
— never leave it silently uncommitted, never discard it. Half-finished work goes
to a branch, `session/{YYYYMMDD}`, not onto main.

## Step 1 — Ingest Notion input
Only when Notion is configured (otherwise say so in one line and continue).

1. **Planning input:** `{tasks_push_script} --inbox --since {last regeneration date of {status_file}}`
   lists pages of this project created or edited in Notion that are not yet linked to
   a task. For each, propose ONE of (batch them into a single confirmation):
   - a new ROADMAP task (open work), with proposed `needs:`/`blocks:` edges,
   - a CHANGELOG entry (the page describes finished work),
   - a note merged into an existing task,
   - ignore (not project work).
   After the user agrees and the line is written, link the page:
   `{tasks_push_script} --link {page_id} {gid}`. A page that bundles several items
   (a session note with a list) is linked to the task that matches its main topic;
   the other items become tasks without a page.
2. **Completion signals:** `{tasks_push_script} --checked` lists open tasks ticked in
   Notion. Confirm each with the user, then flip it to `[x]`.

## Step 2 — Reconcile ROADMAPs
- Mark finished tasks `[x]` and add a dated one-line note under each.
- Park tasks that cannot move (plan-gated, dead end, waiting on a decision) with a
  `` `hold:reason` `` tag.
- Merge back finished `task-implementer` worktree branches the user has reviewed,
  and delete the packet of every task now `[x]` (`{packets_dir}/{task-id}.md`).
- Add new tasks discovered this session. **Propose** new `needs:`/`blocks:` edges
  explicitly and wait for the user to ratify before writing them.
- **Archive** (when a ROADMAP holds more than ~40 done tasks, or once a quarter):
  `{archive_script}` (dry-run) then `{archive_script} --apply`.

## Step 3 — Check the task graph BY CODE (the guardrail)
```
{frontier_script} --check
{frontier_script}
```
This writes `{frontier_output}`. Do not infer the ready set by reading markdown.
If `--check` reports errors, fix the ROADMAP — the commit guard hook refuses the
Step 6 commit otherwise.

## Step 4 — Write the status file (one screen)
Regenerate `{status_file}` from `{frontier_output}` and the calendar
(`{tasks_push_script} --agenda 14`). No tracks, no recommendation of what's next:
- **Booked**: dated Notion tasks of the next 14 days (date/time, task id, title) —
  the user's plan, verbatim; "none booked" is a valid state.
- **In flight**: dispatched tasks with an open packet, if any.
- **Roter Faden**: 3–6 sentences — what changed this session, what just unlocked.
- **Rollup**: straight from the parser's `rollup` (ready / blocked / held / done).
- **Ready** (ids + one-line titles, no ranking) / **Held** / **Blocked** / **Flags**.
Update the "Last regenerated" date — Step 1 of the next session filters on it.

## Step 5 — Sync Notion (`push-tasks`)
`{tasks_push_script} --dry-run`, then without `--dry-run`: ticks the pages of tasks
that are now `[x]`. It creates nothing.

## Step 6 — Commit and push
One commit: code + ROADMAP/CHANGELOG deltas + `{status_file}` + `{frontier_output}`.
Conventional message scoped to the sub-project, 2–4 sentence body. If the commit
guard denies it, fix the ROADMAP it names and retry — never bypass the hook. Then
`git status --short` must be empty (Step 0's rule), and push.

## Step 7 — Push the Notion doc-mirror (always, no separate ask)
Follow the `push-docs` skill. This runs AFTER the commit so each mirrored page's
header shows the new commit hash. If `NOTION_TOKEN` is missing or the mirror
config has an unfilled `page_id`, STOP and point to setup — never invent a
page_id or skip silently.

End with one line: what was ingested, ticked, committed — and, only if the user
wants to plan, that `plan-next` is available. Never start planning unasked.
