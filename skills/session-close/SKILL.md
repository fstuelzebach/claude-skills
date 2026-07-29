---
name: session-close
description: "Run the end-of-session ritual for the project: reconcile ROADMAPs, compute the ready frontier with code, ratify ordering with the user, regenerate the dashboard file, project to Notion, propose calendar blocks, and commit atomically. Use when the user says 'close the session', 'refresh the dashboard', 'wrap up', 'where are we', or at the end of a work block."
---

# Session Close / Dashboard Refresh

This is the ONLY way the dashboard file is written. Follow in order. Read
`CLAUDE.md` Sections 4–8 first (Working Protocol); they are the binding rules.

**Before starting:** read the `## Claude Skills Config` section in `CLAUDE.md` to
resolve all paths and script names used below. Every `{placeholder}` refers to a
key in that table.

## Step 1 — Reconcile ROADMAPs (truth first)
- Mark finished tasks `[x]` and add a dated one-line note under each.
- If the user completed tasks outside a session, read the checked items in the
  Notion Progress Tasks DB and flip them to `[x]` in the matching ROADMAP. The
  checkbox is a signal; the ROADMAP is the truth.
- Add any new tasks discovered this session. **Propose** new `needs:`/`blocks:`
  edges explicitly and wait for the user to ratify before writing them.

## Step 2 — Compute eligibility BY CODE (the guardrail)
Run the `{frontier_script}` from `## Claude Skills Config`:
```
python tools/ready_set.py        # default; actual command from CLAUDE.md
```
This writes `{ready_set_output}` and prints a summary. **Do not infer the ready
set by reading markdown** — eligibility is graph traversal and must come from the
parser. If the parser errors, fix the ROADMAP syntax; do not work around it.

## Step 3 — Ratify ordering (one question, with a recommendation)
Read `{ready_set_output}`. Summarise the ready frontier in plain language and
ask the user ONE strategic question: which eligible task goes first, and does the
ordering hold? Give your recommended order with a one-line rationale (e.g. "T3
first — it unblocks the most"). Eligibility is mechanical; this ordering is the user's.

## Step 4 — Write the dashboard file
Regenerate `{dashboard_file}` from `{ready_set_output}` + the user's answer,
following the structure in the existing dashboard file:
- **Now / Next**: ready tasks in the user's ratified order, each with the one-line "why".
- **Rollup**: straight from the parser's `rollup`.
- **Roter Faden**: a short narrative — critical path, what just unlocked, the
  strategic thrust. This is the part only the model can write.
- **Flags** / **Blocked**: from the parser's `redundancies` and `blocked`.
Update the "Last regenerated" date. Never hand-edit outside this ritual.

## Step 5 — Project upcoming sessions to Notion (one-way)

**Do NOT run the bulk notion_sync script.** Notion receives only the sessions that are
actually being scheduled into the calendar (Step 6c). The full frontier lives in
`{dashboard_file}` and the ROADMAPs — Notion is not a frontier mirror, it is a
session calendar.

Notion tasks are created in Step 6c alongside each calendar event — one Notion
task per filled slot, linked to its calendar event. No bulk sync of the ready set.

## Step 6 — Schedule upcoming sessions (propose → confirm → fill)

The `{calendar_slot_name}` recurring calendar slots are empty placeholders. This step
fills them with specific tasks from the ready frontier — after the user confirms.

### 6a — Find upcoming empty slots

List the next 2–3 weeks of primary calendar events. Identify recurring
**`{calendar_slot_name}`** entries that are still **empty** (summary equals the slot
name exactly, no task-specific description or title suffix). Capture each slot's
exact `start.dateTime`, `end.dateTime`, and `id`.

### 6b — Propose assignments (one question)

Based on slot length and the ready frontier (priority order from `{ready_set_output}`),
propose a concrete schedule: which task (or small task group) goes in which slot.
Match scope to duration — a 90-min slot fits one focused task; a 2-hour slot can
hold two small ones. Show the proposal as a short table:

```
Thu 18-Jun 06:15–07:45 (90 min)  →  dashboard.T8  Production deployment
Sat 20-Jun 16:15–17:45 (90 min)  →  sql.T2        Beta fallback chain
```

Ask the user ONE question: does this assignment work, or should any slot be
reassigned? Recommend the ordering; the user ratifies.

### 6c — Fill confirmed slots (after user says yes)

For each confirmed slot, source project credentials first:
```bash
[ -f .claude/project.env ] && source .claude/project.env
```

Then:

1. Create a new calendar event on the primary calendar:
   - `summary`: `"{calendar_slot_name} — {task IDs}: {brief name}"`
   - `description`: what needs to be done / acceptance criteria
   - `start` / `end`: the slot's **exact** datetimes — do not adjust them
   - `colorId`: 8 (graphite, matches existing style)
2. Capture the event's `htmlLink` from the response.
3. Create a linked Notion task:

```bash
[ -f .claude/project.env ] && source .claude/project.env
python {session_task_script} \
    --title "{calendar_slot_name} — {same summary}" \
    --date YYYY-MM-DD \
    --class-id "$NOTION_CLASS_PAGE_ID" \
    --link "{htmlLink}" \
    --notes "{one-line: task IDs and what they do}"
```

This writes a Progress Tasks page so the scheduled session appears on the project's
Notion page. `Kontrollkästchen` starts unchecked — it is checked to `true` at the
end of that session to confirm the work was done.

## Step 7 — Commit atomically
One commit: code + ROADMAP deltas + regenerated `{dashboard_file}` (+ `{ready_set_output}`).
Conventional message scoped to the sub-project, with a 2–4 sentence human-readable
body. See `CLAUDE.md` Section 4.

## Step 8 — Push the Notion doc-mirror (always, no separate ask)
Run this automatically — do not wait for the user to separately say "push mirror".
Follow the `push-notion-mirror` skill's procedure. This step runs AFTER commit
(Step 7) so the header stamp on each Notion page shows the just-created commit hash.

Source project credentials before running:
```bash
[ -f .claude/project.env ] && source .claude/project.env
```

If `NOTION_TOKEN` is missing or `{mirror_config}` has an unfilled `page_id`,
STOP and tell the user to complete one-time setup — never invent a page_id or skip silently.
