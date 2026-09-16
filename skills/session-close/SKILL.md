---
name: session-close
description: "Run the end-of-session ritual for the project: reconcile ROADMAPs, compute the ready frontier with code, group it into isolated parallel tracks, ratify tracks and order with the user, write task packets, regenerate the dashboard file, push open tasks to Notion, commit atomically, and mirror docs. Use when the user says 'close the session', 'refresh the dashboard', 'wrap up', 'where are we', or at the end of a work block."
---

# Session Close v2 / Dashboard Refresh

This is the ONLY way the dashboard file is written. Follow in order. Read the
project's Working Protocol (`CLAUDE.md` and the workflow doc it points to) first;
those are the binding rules.

**Before starting:** read the `## Claude Skills Config` section in `CLAUDE.md` to
resolve all paths and script names used below. Every `{placeholder}` refers to a
key in that table. Defaults: `{frontier_script}` = `python tools/ready_set.py`,
`{ready_set_output}` = `docs/ready_set.json`, `{packets_dir}` = `docs/packets`,
`{todos_script}` = `python tools/notion_sync.py`.

**What changed from v1:** the ready frontier is a *dispatch list*, not a priority
queue — by construction every task in it has its dependencies satisfied, so it is
the raw material for parallel work. Calendar scheduling is gone: Notion receives
the open tasks and the user schedules them by hand.

## Step 1 — Reconcile ROADMAPs (truth first)
- Mark finished tasks `[x]` and add a dated one-line note under each.
- Tasks completed outside a session: run `{todos_script} --checked` (Notion
  configured only). It lists open tasks whose Notion checkbox is ticked. Confirm
  each with the user, then flip it to `[x]` in the matching ROADMAP. The checkbox
  is a signal; the ROADMAP is the truth.
- Merge back any finished implementer worktree branches the user has reviewed,
  and delete the packet of every task now `[x]` (`{packets_dir}/{task-id}.md`).
- Add any new tasks discovered this session. **Propose** new `needs:`/`blocks:`
  edges explicitly and wait for the user to ratify before writing them.

## Step 2 — Compute eligibility BY CODE (the guardrail)
```
{frontier_script}            # e.g. python tools/ready_set.py
```
This writes `{ready_set_output}` and prints a summary. **Do not infer the ready
set by reading markdown** — eligibility is graph traversal and must come from the
parser. Run `{frontier_script} --check` too; if it reports errors (duplicate ids,
malformed task lines, unknown `needs:`, cycles), fix the ROADMAP syntax — do not
work around it. The commit guard hook will refuse the Step 8 commit otherwise.

## Step 3 — Group the frontier into isolated tracks
Dependency-independence is **necessary but not sufficient** for parallelism. Two
ready tasks may share a track-free slot only if ALL hold:
- **disjoint file sets** — estimate the files each task will touch (use the `scout`
  agent for anything non-obvious rather than reading widely yourself);
- **no shared config** (same TOML/settings file);
- **no shared schema or migration**;
- **no design dependency** (one task's outcome shapes how the other is built).

Tasks that fail any test go into the **same track**, serialised. **When in doubt,
same track** — a wrongly-serialised task costs an hour; a wrongly-parallelised pair
costs a merge conflict in generated state. Start with **2–4 tracks** at most: merge
friction and review capacity bind before usage limits do. A task that cannot be
given a clean file boundary is not ready to parallelise — keep it sequential.

## Step 4 — Ratify tracks + order (one question, with a recommendation)
Show the proposal as a short table:

```
Track A  sql.T2 → sql.T12        src/.../beta*.py, conf/config_benchmarks.toml
Track B  dashboard.T19           dashboard/frontend/components/stock/*
Seq      trading.D1              touches walk_forward.py (shared with D2)
```

Ask ONE question: do the tracks and ordering hold? Give your recommendation with a
one-line rationale per track ("A first — it unblocks the most"). Eligibility is
mechanical; grouping and ordering are the user's.

## Step 5 — Write task packets
For every task in a ratified track, write `{packets_dir}/{task-id}.md`. An
`implementer` agent sees only its packet, its worktree, and `CLAUDE.md` —
everything it needs must be in the packet:

```markdown
# {task-id} — {title}
Track: {A|B|…}   Branch: task/{task-id}

## Goal
What must be true when done.

## Boundary
Allow (only these may change):
- path/or/glob
Forbid (always):
- any ROADMAP.md, {dashboard_file}, {ready_set_output}, other packets
- config owned by another track: …

## Context
Design docs, relevant METRICS/ubiquitous-language entries, prior decisions that constrain this.

## Acceptance
A checkable condition — a command to run and its expected result.

## Open questions
Things the implementer must surface, never decide.
```

If you cannot write a clean Boundary for a task, move it back to a sequential track
and say so. Packets are committed in Step 8 so worktrees branched from that commit
can read them.

## Step 6 — Write the dashboard file
Regenerate `{dashboard_file}` from `{ready_set_output}` + the ratified tracks,
following the structure in the existing dashboard file:
- **Now / Next**: ratified tracks, each with its tasks in order and the one-line "why".
- **Rollup**: straight from the parser's `rollup`.
- **Roter Faden**: a short narrative — critical path, what just unlocked, the
  strategic thrust. This is the part only the model can write.
- **Flags** / **Blocked**: from the parser's `redundancies` and `blocked`.
Update the "Last regenerated" date. Never hand-edit outside this ritual.

## Step 7 — Push open tasks to Notion (`push-todos`)
Follow the `push-todos` skill: dry-run, show the counts, then push. Default source is
the ready frontier. It creates missing pages and ticks pages of `[x]` tasks; it never
archives and never sets dates — scheduling happens by hand in Notion.
If Notion is not configured, say so in one line and continue.

## Step 8 — Commit atomically
One commit: code + ROADMAP deltas + packets + regenerated `{dashboard_file}`
(+ `{ready_set_output}`). Conventional message scoped to the sub-project, with a
2–4 sentence human-readable body. If the commit guard denies the commit, fix the
ROADMAP it names and retry — never bypass the hook.

## Step 9 — Push the Notion doc-mirror (always, no separate ask)
Run this automatically — do not wait for the user to separately say "push mirror".
Follow the `push-notion-mirror` skill's procedure. This step runs AFTER the commit so
the header stamp on each Notion page shows the just-created commit hash.

If `NOTION_TOKEN` is missing or `{mirror_config}` has an unfilled `page_id`,
STOP and tell the user to complete one-time setup — never invent a page_id or skip silently.

## Dispatching (after the ritual, when the user says go)
For each ratified track, launch one `implementer` agent (it runs in its own git
worktree) with the packet path of the track's next task. Tracks run in parallel;
tasks within a track run one after another. When an implementer reports back:
review its open questions with the user, optionally run the `explainer` agent on its
branch (advisory), and merge only after the user OKs it.
