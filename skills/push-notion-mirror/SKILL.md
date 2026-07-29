---
name: push-notion-mirror
description: Push the project's canonical docs into Notion as a generated, read-only mirror by running the mirror script from CLAUDE.md. Use as the final step of the session-close ritual (after the dashboard is regenerated and committed), or on demand when the user says "push mirror", "sync notion", "update notion mirror", or "mirror the docs".
---

# Push Notion Mirror

Mirrors the repo's canonical markdown docs into Notion so the user and Claude.ai
stay current on a **private** repo. Truth stays in git; the Notion pages are
generated and overwritten on every run — they are a reading surface, never a
source of truth.

This is distinct from `notion_sync.py` (which projects the task *frontier* into
Notion Progress Tasks for scheduling). This skill mirrors whole *documents*.

**Before starting:** read the `## Claude Skills Config → Notion Integration` section
in `CLAUDE.md` to resolve `{mirror_script}` and `{mirror_config}`. Then source the
per-project env file for credentials:
```bash
[ -f .claude/project.env ] && source .claude/project.env
```
Global secrets (`NOTION_TOKEN`, `NOTION_TASKS_DB_ID`) come from `~/.zshrc` or
`~/.zprofile` — set once per machine, shared across all projects.

## When to run
- **Final step of `session-close`**, AFTER the dashboard file is regenerated and
  everything is committed.
- **On demand:** "push mirror", "sync notion", "update notion mirror".

## Preconditions — fail loudly, never paper over
1. `{mirror_config}` exists and every `[[docs]]` entry you intend to push has a
   non-empty `page_id`. If any are empty, STOP and tell the user to complete
   one-time Notion setup (`docs/SETUP_NOTION_MIRROR.md`). **Never invent a page_id.**
2. `NOTION_TOKEN` is set in the environment. If the script reports it missing,
   STOP and point to setup.
3. `notion-client` is installed (`pip show notion-client`); if not, `pip install notion-client`.

## Procedure
1. **Confirm the docs are current on disk** before pushing:
   - ROADMAPs reflect this session (tasks marked `[x]`, edges proposed + ratified).
   - The dashboard file was regenerated this session.
   - If deployment/runbook content changed, it lives in CLAUDE.md's deployment section, not inside a ROADMAP.
2. **Preview:**
   ```bash
   [ -f .claude/project.env ] && source .claude/project.env
   python {mirror_script} --dry-run
   ```
   Show the user the per-doc block counts. Flag any doc reporting 0 blocks or "not found".
3. **Push:**
   ```bash
   [ -f .claude/project.env ] && source .claude/project.env
   python {mirror_script}
   ```
   For a subset, use `--only <key> <key>` (keys are defined in `{mirror_config}`).
4. **Report** one line per doc: synced / skipped / block count / wiped count.
   Surface any API error verbatim — the script already retries rate limits; do not
   add silent retries.

## Guardrails
- **Never hand-edit the Notion pages** or tell the user to — they are overwritten
  every session. All edits go to the markdown in git.
- **Never mirror a doc containing a secret.** The mirror only pushes files tracked
  in git. If a mirrored doc contains a key or token, that is a bug — STOP and flag
  it, don't push it.
- **Never change `page_id`s.** A missing page means the user re-runs one-time setup.
- Idempotent by design: safe to re-run. If interrupted mid-wipe, just run again.
