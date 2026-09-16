---
name: session-close
description: "Run the end-of-session ritual for the project: ingest Notion planning input, reconcile ROADMAPs/CHANGELOGs, compute the ready frontier with code, group it into isolated parallel tracks, ratify tracks and order with the user, write task packets, regenerate the status file, push open tasks to Notion, commit and push with a clean working tree, and mirror docs. Use when the user says 'close the session', 'refresh the status', 'wrap up', 'where are we', or at the end of a work block."
---

# Session Close

This is the ONLY way the status file is written. Follow in order. Read the
project's Working Protocol (`CLAUDE.md` and the workflow doc it points to) first;
those are the binding rules.

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
CHANGELOG = finished work, code). Notion holds planning and thinking, because it
is reachable from anywhere. This ritual keeps them in step both ways: Notion input
comes *in* at Step 1, open tasks and docs go *out* at Steps 8 and 10.

## Step 0 — Working tree check
Run `git status --short`. Every change must end this session in a commit (Step 9).
List anything that is not this session's work and ask the user what to do with it
— never leave it silently uncommitted, never discard it. Half-finished work goes
to a branch, `session/{YYYYMMDD}`, not onto main.

## Step 1 — Ingest Notion input
Only when Notion is configured (otherwise say so in one line and continue).

1. **Planning input:** `{tasks_push_script} --inbox --since {last regeneration date of {status_file}}`
   lists pages of this project created or edited in Notion that are not yet linked to
   a task. For each, propose to the user one of:
   - a new ROADMAP task (open work) — with proposed `needs:`/`blocks:` edges,
   - a CHANGELOG entry (the page describes finished work),
   - a note merged into an existing task,
   - ignore (not project work).
   After the user agrees and the line is written, link the page:
   `{tasks_push_script} --link {page_id} {gid}` so it is never ingested twice.
2. **Completion signals:** `{tasks_push_script} --checked` lists open tasks ticked in
   Notion. Confirm each with the user, then flip it to `[x]`.

## Step 2 — Reconcile ROADMAPs
- Mark finished tasks `[x]` and add a dated one-line note under each.
- Park tasks that cannot move (plan-gated, dead end, waiting on a decision) with a
  `` `hold:reason` `` tag — they leave the frontier and show under "held".
- Merge back finished `task-implementer` worktree branches the user has reviewed,
  and delete the packet of every task now `[x]` (`{packets_dir}/{task-id}.md`).
- Add new tasks discovered this session. **Propose** new `needs:`/`blocks:` edges
  explicitly and wait for the user to ratify before writing them.
- **Archive** (when a ROADMAP holds more than ~40 done tasks, or once a quarter):
  `{archive_script}` (dry-run) then `{archive_script} --apply` moves done task blocks
  into the sibling `CHANGELOG.md`. The frontier script reads both files.

## Step 3 — Compute eligibility BY CODE (the guardrail)
```
{frontier_script} --check
{frontier_script}
```
This writes `{frontier_output}`. **Do not infer the ready set by reading
markdown** — eligibility is graph traversal and must come from the parser. If
`--check` reports errors (duplicate ids, malformed task lines, unknown `needs:`,
cycles), fix the ROADMAP — do not work around it. The commit guard hook refuses
the Step 9 commit otherwise.

## Step 4 — Group the frontier into isolated tracks
Dependency-independence is **necessary but not sufficient** for parallelism. Two
ready tasks may run in parallel only if ALL hold:
- **disjoint file sets** — estimate the files each task will touch (use the `scout`
  agent for anything non-obvious rather than reading widely yourself);
- **no shared config** (same TOML/settings file);
- **no shared schema or migration**;
- **no design dependency** (one task's outcome shapes how the other is built).

Tasks that fail any test go into the **same track**, serialised. **When in doubt,
same track** — a wrongly-serialised task costs an hour; a wrongly-parallelised pair
costs a merge conflict in generated state. Start with **2–4 tracks** at most. A task
that cannot be given a clean file boundary stays sequential.

## Step 5 — Ratify tracks + order (one question, with a recommendation)
```
Track A  sql.T2 → sql.T12        src/.../beta*.py, conf/config_benchmarks.toml
Track B  dashboard.T19           dashboard/frontend/components/stock/*
Seq      trading.D1              touches walk_forward.py (shared with D2)
```
Ask ONE question: do the tracks and ordering hold? Recommend, with a one-line
rationale per track. Eligibility is mechanical; grouping and ordering are the user's.

## Step 6 — Write task packets
For every task in a ratified track, write `{packets_dir}/{task-id}.md`. A
`task-implementer` agent sees only its packet, its worktree, and `CLAUDE.md` —
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
- any ROADMAP.md / CHANGELOG.md, {status_file}, {frontier_output}, other packets
- config owned by another track: …

## Context
Design docs, relevant METRICS/domain-glossary entries, prior decisions, and the
Notion planning page if the task came from one.

## Acceptance
A checkable condition — a command to run and its expected result.

## Open questions
Things the task-implementer must surface, never decide.
```

## Step 7 — Write the status file (one screen)
Regenerate `{status_file}` from `{frontier_output}` + the ratified tracks. Keep it
to roughly one screen — history belongs in CHANGELOGs and commit bodies:
- **Now / Next**: ratified tracks, each task with a one-line "why".
- **Roter Faden**: 3–6 sentences — critical path, what just unlocked, the thrust.
- **Rollup**: straight from the parser's `rollup` (ready / blocked / held / done).
- **Held** / **Blocked** / **Flags**: from `held`, `blocked`, `redundancies`.
Update the "Last regenerated" date — Step 1 of the next session filters on it.

## Step 8 — Push open tasks to Notion (`push-tasks`)
Follow the `push-tasks` skill: dry-run, show the counts, then push. It creates
missing pages and ticks pages of done tasks; it never archives and never sets
dates — scheduling happens by hand in Notion.

## Step 9 — Commit and push
One commit: code + ROADMAP/CHANGELOG deltas + packets + `{status_file}` +
`{frontier_output}`. Conventional message scoped to the sub-project, 2–4 sentence
body. If the commit guard denies it, fix the ROADMAP it names and retry — never
bypass the hook. Then `git status --short` must be empty (Step 0's rule), and push
the branch so the work exists somewhere other than this machine.

## Step 10 — Push the Notion doc-mirror (always, no separate ask)
Follow the `push-docs` skill. This runs AFTER the commit so each mirrored page's
header shows the new commit hash. If `NOTION_TOKEN` is missing or
`{docs_push_config}` has an unfilled `page_id`, STOP and point to setup — never
invent a page_id or skip silently.

## Dispatching (after the ritual, when the user says go)
For each ratified track, launch one `task-implementer` agent (it runs in its own
git worktree) with the packet path of the track's next task. Tracks run in
parallel; tasks within a track run one after another. When one reports back:
review its open questions with the user, optionally run `diff-explainer` on its
branch (advisory), and merge only after the user OKs it.
