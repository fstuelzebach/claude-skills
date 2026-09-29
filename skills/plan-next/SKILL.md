---
name: plan-next
description: "Plan the next work with the user and book it into the calendar: show the ready tasks and the already-booked slots, recommend 2–3, let the user pick tasks and time slots, then create Notion task pages ONLY for the booked slots (they appear in the calendar). Optionally group them into parallel tracks with task packets. Use ONLY when the user asks — 'what's next', 'plan next', 'plan the next session', 'pencil in', 'book a slot', 'schedule tasks'. Never run it from session-close."
---

# Plan Next

The user decides what comes next and when; Claude recommends and does the
paperwork. This is the only place Claude creates Notion task pages, and only for
tasks that get a concrete calendar slot. Nothing else is pushed to Notion.

**Before starting:** resolve `{frontier_script}`, `{frontier_output}`,
`{tasks_push_script}`, `{packets_dir}` from `## Claude Skills Config` in `CLAUDE.md`
(defaults as in `session-close`). Timezone: the project's (Europe/Berlin unless
`CLAUDE.md` says otherwise).

## Step 1 — Fresh picture (no questions yet)
```
{frontier_script} --check && {frontier_script}
{tasks_push_script} --agenda 14
```
The first gives the ready set (by code — never infer it from markdown); the
second shows what is already booked, including pages the user created by hand.

## Step 2 — Recommend, then ask once
Show at most one screen:
- **Already booked** (from the agenda) — these are fixed; do not re-plan them.
- **Recommendation: 2–3 tasks** from the ready set, each with a one-line why
  (unlocks something, high priority, small and quick, user asked for it before).
- The rest of the ready set as ids + titles, unranked, for the user to pick from.

Ask ONE question: which tasks, and when (date + time slot, e.g. "Thu 14–16")?
The user may also pick a blocked task — then say what it waits on. Accept "none"
without argument.

## Step 3 — Book the slots
For each task the user gave a slot:
```
{tasks_push_script} --schedule {gid} {start} {end} --dry-run   # show all first
{tasks_push_script} --schedule {gid} {start} {end}
```
ISO local time (`2026-10-01T14:00`), end optional (a date without time books a
whole day). It sets the Notion `Datum` — creating the task page only if the task
has none — so the slot appears in the user's calendar. Report each page link.
A task the user picked **without** a slot gets no page; note it in the status
file's Booked section as "next, unscheduled" only if the user wants that.

## Step 4 — Optional: parallel tracks + packets
Only if the user wants tasks dispatched to `task-implementer` agents. Two booked
tasks may run in parallel only with **disjoint file sets, no shared config, no
shared schema/migration, no design dependency** — otherwise same track, in
sequence; when in doubt, same track. Propose the grouping in one question, then
write `{packets_dir}/{task-id}.md` per task:

```markdown
# {task-id} — {title}
Track: {A|B|…}   Branch: task/{task-id}   Slot: {date time}

## Goal
What must be true when done.

## Boundary
Allow (only these may change):
- path/or/glob
Forbid (always):
- any ROADMAP.md / CHANGELOG.md, status file, frontier output, other packets
- config owned by another track: …

## Context
Design docs, glossary entries, prior decisions, the Notion page if it has one.

## Acceptance
A checkable condition — a command to run and its expected result.

## Open questions
Things the task-implementer must surface, never decide.
```

Dispatch (when the user says go): one `task-implementer` per track with the packet
path of its next task; review its open questions with the user and merge only
after the user OKs it.

## Step 5 — Record
Commit packets (if any) with a one-line message; the booked slots live in Notion
only (planning = Notion). The next `session-close` shows them under **Booked**.

## Rules
- Never book a slot the user did not name; never move or delete a date the user set.
- Never create pages for the whole frontier; never archive or delete pages.
- Never create calendar entries outside the Notion `Datum` field.
