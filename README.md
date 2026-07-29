# claude-skills

Reusable Claude Code skills and project tools — install into any project in one command.

---

## Philosophy

This repo embodies two design principles that work together:

**1. Notion as second brain (hardwired productivity choice)**
The `session-close` and `push-notion-mirror` skills assume you use Notion as a persistent second brain across all your projects — one workspace, one Progress Tasks database, mirrored docs per project. This is not optional or configurable; it's a deliberate productivity choice baked into the session ritual. Every project gets its own Notion domain (its own mirror pages, its own class entry in the Progress Tasks DB), but the workspace and credential are shared globally.

**2. Skills without Notion still work**
The five general-purpose skills (`caveman`, `grill-me`, `handoff`, `zoom-out`, `ubiquitous-language`) have zero dependency on Notion or any external service. If you just want those, install them and ignore everything in the "Notion setup" sections below. `session-close` degrades gracefully too — Steps 1–4 (ROADMAP reconciliation, frontier computation, ordering ratification, dashboard regeneration) are pure git + markdown and work without Notion configured. Only Steps 5–8 (Notion mirror, calendar, Notion task creation) require the integration.

---

## Skills

| Skill | Notion required? | What it does |
|---|---|---|
| `caveman` | No | Ultra-compressed communication mode (~75% fewer tokens) |
| `grill-me` | No | Relentless one-question-at-a-time interview to stress-test a plan or design |
| `handoff` | No | Compact the current conversation into a handoff doc for the next agent |
| `zoom-out` | No | Map all relevant modules and callers when unfamiliar with an area of code |
| `ubiquitous-language` | No | Extract a DDD-style glossary from the conversation, saved to `UBIQUITOUS_LANGUAGE.md` |
| `session-close` | Steps 5–8 only | End-of-session ritual: reconcile ROADMAPs → compute frontier → ratify order → regenerate dashboard → mirror to Notion → fill calendar slots → commit |
| `push-notion-mirror` | Yes | Push canonical docs (ROADMAPs, dashboard, CLAUDE.md, …) to Notion as a read-only mirror |

---

## Tools (`tools/` — copy into project once)

These are standalone Python scripts that the skills call. They are copied into the project's `tools/` directory on first install, not symlinked — so you can customize them per project without affecting other projects.

| Tool | Notion required? | What it does |
|---|---|---|
| `ready_set.py` | No | Traverses `needs:`/`blocks:` dependency graph across all `ROADMAP.md` files → writes `docs/ready_set.json` with ready/blocked/rollup. Standard library only. |
| `notion_doc_sync.py` | Yes | Wipes and rewrites Notion pages from local markdown (idempotent). Reads doc→page mapping from `conf/notion_mirror.toml`. Auth via `NOTION_TOKEN` env var. |
| `create_session_task.py` | Yes | Creates a session-recap entry in a Notion Progress Tasks database, linked to a Google Calendar event. |
| `notion_sync.py` | Yes | One-way projection of the ready frontier into Notion Progress Tasks: creates pages for new ready tasks, archives pages for tasks that left the frontier. |

---

## Install into a project

```bash
# From the target project root:
bash ~/.claude-skills/install.sh
```

What this does:
- **Symlinks** every skill into `.claude/skills/<name>` — so a `git pull` in `~/.claude-skills` auto-updates all projects.
- **Copies** tools into `tools/` on first install only (does not overwrite existing files, so per-project customizations are preserved).

To update skills after pulling:
```bash
cd ~/.claude-skills && git pull
# Symlinks auto-update — no re-run needed unless you want to install newly added skills.
bash ~/.claude-skills/install.sh   # re-run from project root to pick up new skills
```

---

## Setting up a new project (full walkthrough)

### Step 1 — Install skills and tools

```bash
cd /path/to/your/new-project
bash ~/.claude-skills/install.sh
```

### Step 2 — Add `## Claude Skills Config` to your `CLAUDE.md`

This is the only place the generic skills look for project-specific paths. No secrets here.

```markdown
## Claude Skills Config

### Session Management
| key | value |
|---|---|
| frontier_script | `python tools/ready_set.py` |
| ready_set_output | `docs/ready_set.json` |
| dashboard_file | `DASHBOARD.md` |
| calendar_slot_name | `<name of your recurring calendar slot>` |

### Notion Integration
| key | value |
|---|---|
| mirror_script | `python tools/notion_doc_sync.py` |
| mirror_config | `conf/notion_mirror.toml` |
| session_task_script | `python tools/create_session_task.py` |
```

> **If you're not using Notion:** omit the "Notion Integration" table entirely.
> `session-close` will skip those steps automatically.

### Step 3 — Set global env vars (once per machine, shared across all projects)

Add to `~/.zshrc` or `~/.zprofile`:

```bash
# Notion — one workspace, shared across all projects
export NOTION_TOKEN="secret_xxx"        # Internal integration token from Notion settings
export NOTION_TASKS_DB_ID="abc123..."   # 32-char ID of your Progress Tasks database
```

> **Where to find these:**
> - `NOTION_TOKEN`: Notion → Settings → Connections → Develop or manage integrations → your integration → Internal Integration Secret
> - `NOTION_TASKS_DB_ID`: Open your Progress Tasks database in Notion, copy the URL — the 32-char segment after the last `/` and before `?` is the ID

### Step 4 — Create `.claude/project.env` (per project, gitignored)

This file holds the one thing that differs between projects: which Notion "Class" page tags your tasks to this project.

```bash
# .claude/project.env
NOTION_CLASS_PAGE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

> **Where to find `NOTION_CLASS_PAGE_ID`:**
> Open the Notion page that represents this project in your Class/Config database.
> Copy the page URL — the 32-char UUID at the end is the ID (reformat with dashes: `8chars-4-4-4-12`).

Add it to `.gitignore`:
```
.claude/project.env
```

### Step 5 — Create `conf/notion_mirror.toml` (per project, committed)

This maps local markdown files to the Notion pages they mirror into. Page IDs are not secrets.

```toml
# conf/notion_mirror.toml
# Each [[docs]] entry = one local file → one Notion page (wiped and rewritten each run).
# Run `python tools/notion_doc_sync.py --dry-run` to preview block counts before pushing.

[[docs]]
key      = "dashboard"
path     = "DASHBOARD.md"
page_id  = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"   # Notion page URL → copy the UUID
title    = "DASHBOARD"

[[docs]]
key      = "claude_md"
path     = "CLAUDE.md"
page_id  = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
title    = "CLAUDE.md"

# Add one [[docs]] block per file you want mirrored.
# Keys must be unique — used with --only to sync a subset: python tools/notion_doc_sync.py --only dashboard
```

> **How to get a Notion page ID:** Create a blank page in Notion (or use an existing one). Open it, click Share → Copy link. The URL looks like `https://notion.so/My-Page-title-<32chars>`. The `<32chars>` at the end is the page ID. Reformat with dashes for the TOML: `8-4-4-4-12`.

> **Integration access:** The Notion integration must be added to each page you want to write. Open the page → `···` menu → Connections → add your integration.

### Step 6 — Install `notion-client` Python package

```bash
pip install notion-client requests
```

### Step 7 — Test the setup

```bash
# Preview what would be synced (no writes):
source .claude/project.env
python tools/notion_doc_sync.py --dry-run

# Push for real:
python tools/notion_doc_sync.py

# Test session task creation (dry run):
source .claude/project.env
python tools/create_session_task.py \
    --title "my-project — Test Task" \
    --date "$(date +%Y-%m-%d)" \
    --class-id "$NOTION_CLASS_PAGE_ID" \
    --dry-run
```

---

## Credential reference

| Credential | Where stored | Scope | How to find it |
|---|---|---|---|
| `NOTION_TOKEN` | `~/.zshrc` env var | Global — one per Notion workspace | Notion Settings → Connections → your integration → Secret |
| `NOTION_TASKS_DB_ID` | `~/.zshrc` env var | Global — same Progress Tasks DB for all projects | Open DB in Notion, copy URL → 32-char segment |
| `NOTION_CLASS_PAGE_ID` | `.claude/project.env` (gitignored) | Per-project — the Class/Config page that tags this project's tasks | Open the project's Class page in Notion, copy URL → UUID |
| Doc page IDs | `conf/notion_mirror.toml` (committed) | Per-project — one UUID per mirrored doc | Create/open each target Notion page, copy URL → UUID |

---

## Without Notion — what still works

If you skip all Notion setup, you get:

- All 5 general-purpose skills with full functionality
- `session-close` Steps 1–4: ROADMAP reconciliation, dependency-graph computation (`ready_set.py`), ordering ratification, dashboard file regeneration, atomic commit
- `ready_set.py` as a standalone dependency tracker for any project with `ROADMAP.md` files

What you miss: the Notion doc mirror, Notion Progress Tasks sync, and the calendar-to-Notion task creation in `session-close` Steps 5–8.
