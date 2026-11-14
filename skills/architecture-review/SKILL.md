---
name: architecture-review
description: "Objective, evidence-based review of a project's IT architecture and workflows — data flow, where data is copied, memory/disk/runtime hot spots, inconsistencies, fragile workflows — reported in plain language, then (only if the user wants change) a phased plan with explicit decisions, an approval gate and a backup gate before any code changes. Each run saves a dated report with measured baselines so the next run can compare (feedback loop). Use when the user asks to 'analyse the architecture', 'review the setup', 'why is this so slow / so memory-hungry', 'find inconsistencies', 'audit the workflow', 'architecture review', or wants a previous review re-run. Optional scope argument: memory | data-flow | workflow | security | all (default all)."
---

# Architecture Review

A review the user can trust and act on. Three rules carry everything else:

1. **Measure before you judge.** Every finding is backed by evidence: a file and
   line, a measured number, or the output of a command you ran. Anything you
   did not verify is labelled *estimate* or *assumption*, never stated as fact.
2. **Read-only until approved.** Phases 1–3 change nothing. No code, no config,
   no data. Change only starts after the user approves the plan (Phase 4) and
   the backup gate passed (Phase 5).
3. **Plain language.** The user is not necessarily a programmer. Explain what
   happens and why it costs something ("the step loads all 16 million price
   rows into memory at once") instead of naming patterns ("unbounded
   materialisation"). Technical names go in backticks, next to the plain
   description, not instead of it.

**Before starting:** read the project's `CLAUDE.md` and respect its rules —
especially off-limits paths (secrets, credential stores): never read, copy or
inspect them, not even to measure them. If the project has a reference/
architecture doc, read its outline first; it saves reading code. Reply in the
user's language.

**Scope:** `all` unless the user names one (`memory`, `data-flow`, `workflow`,
`security`). A narrow scope still gets Phase 1's map, kept short.

---

## Phase 1 — Map what exists (read-only)

Build the picture before looking for problems.

- **Components:** what runs where (desktop, server, scheduled jobs, web app,
  database files, external APIs). One line each.
- **Data flow:** from source to what the user finally sees. Draw it as a short
  arrow diagram in a code block.
- **Copies of the data:** list every place the same data lives (files, each
  database, each server). Copies are where cost, drift and sync code hide —
  count them explicitly.
- **Workflows:** how a change reaches production, how jobs are scheduled, how
  failures are noticed, how things are backed up.

Prefer the project's docs and config for this; read code only to confirm or
where docs are silent. For a wide sweep use a read-only search agent if one is
available, but verify its claims yourself before reporting them.

## Phase 2 — Measure (read-only)

Find the numbers the project already records before creating new ones:
job logs with runtimes or peak memory, run-history tables, monitoring output.
Then measure what is missing, cheaply and safely:

- sizes of data folders and database files (`du`, file listings)
- row counts and table sizes, opened **read-only**
- free vs. used space inside database files
- what is written but never read (search for readers of each output)
- running processes, if the question is about live load

Never run a heavy job just to measure it without asking. Do not inspect
anything while a job is writing to it — check running processes first.

Record each number with its source (log line, command) — they become the
baseline for the next review (Phase 3 report).

## Phase 3 — Findings and report

Look for, in roughly this order of payoff:

| Kind | Typical signs |
|---|---|
| **Hot spots** | one step uses far more memory/time than the rest; cost does not scale with input size (small input, same big cost) |
| **Load-everything patterns** | whole tables or file sets pulled into memory, then filtered; filters applied at the end instead of while reading |
| **Write-only outputs** | files or tables produced every run that nothing reads |
| **Duplication** | the same rule implemented in several places; the same value stored on every row; several copies of the data kept in sync by hand |
| **Inconsistencies** | names that say one thing while the content is another; dates stored as text; mixed conventions for the same concept |
| **Fragile workflows** | manual steps, file swaps, merge rules for "which copy wins", missing or untested backups, secrets mixed with data |
| **What already works** | name it too — guards, caps, good decisions — so the review is balanced and nobody removes them by accident |

For each finding give: **what happens** (plain words), **evidence** (number,
`file:line`), **why it matters**, **fix idea** and **expected effect** (labelled
as estimate if not measured), **size of the change** (small / medium / large).

Rank by payoff relative to effort, biggest first. Add a short "suggested order".
Stop after the report and ask whether the user wants a change plan. Do not
start one uninvited.

**Save the report** to `docs/reviews/YYYY-MM-DD-architecture-review.md` (or the
location the project's `CLAUDE.md` names), with:

```markdown
# Architecture review — YYYY-MM-DD   (scope: …)
## Baseline (measured)
| What | Value | Source |
## Map
## Findings (ranked)
## Status of previous findings     ← only from the second review on
| Finding (from review of …) | Then | Now | Status: fixed / better / unchanged / worse |
## Suggested order
```

Ask before committing the report if the project's workflow requires it.

### Feedback loop (repeat reviews)

If earlier reports exist in `docs/reviews/`, read the newest one first. Re-measure
its baseline the same way, fill "Status of previous findings", and call out
regressions plainly. A fix only counts as fixed when the number moved, not
because the code changed.

## Phase 4 — Change plan (only when asked)

Write the plan so the user can approve it in one go:

1. **Target picture** — a small diagram and 3–5 sentences.
2. **Data roles** — every table/file/store gets exactly one role:
   - *persistent* — cannot or should not be re-created (history, user data,
     anything the source no longer provides); must be backed up
   - *cache* — fetched from an external source, kept, refreshed by a rule
     (state the rule: "older than 7 days")
   - *derived* — can be deleted and recomputed from the two above; not backed up
   - *never here* — secrets and anything the rules forbid in that store
3. **Building blocks** — the abstractions the change needs, each with one
   sentence of purpose and the files it replaces.
4. **What goes away** — scripts, jobs, files that become obsolete.
5. **Steps** — small, each one independently verifiable, the old path running
   until the last step. For each: what is checked and how ("old and new output
   identical, column by column, for universe X"). Mark steps that touch
   production or shared systems — those get a separate confirmation.
6. **Decisions for the user** — each with your recommendation first and why.

Then stop and wait for approval. Approval of the plan covers the plan as
written; anything that changes scope gets asked again.

## Phase 5 — Backup gate (before the first change)

Before the first change, establish and tell the user exactly what is restorable:

- **Code:** working tree clean or deliberately left, everything pushed, a
  restore-point tag on the current commit pushed to the remote.
- **Data that is not in version control** (databases, generated data, user
  data — check `.gitignore`): a copy on a *different physical disk* or machine,
  verified (copy finished without errors, sizes match). Git alone does not
  back up ignored data — say so plainly if the user assumes it does.
- **Off-limits stores** (credential databases etc.): do not copy them yourself;
  give the user the exact one-line command to run themselves.
- **Servers:** if a later step touches a server, plan a server-side snapshot
  before that step, not now — and say so.

Only when the gate passed (or the user explicitly accepts a gap) start Step 0
of the plan — on a separate branch, following the project's own workflow
(task tracking, commit rules, reviews).

---

## Style of the report

- Lead with the answer to the user's question in one or two sentences.
- Tables for numbers, short paragraphs for explanations.
- No jargon without a plain-language explanation; no hedging on things you
  measured; clear "estimate" labels on things you did not.
- End with what you did *not* change and what the next decision is.
