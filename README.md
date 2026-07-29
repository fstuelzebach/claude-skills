# claude-skills

Shared Claude Code skills and project tools. Install into any project in one command.

## Install into a project

```bash
cd /path/to/your/project
bash ~/.claude-skills/install.sh
```

This symlinks all skills into `.claude/skills/` and copies tools into `tools/` (first-time only).

To update after pulling new skill versions:
```bash
cd ~/.claude-skills && git pull
bash ~/.claude-skills/install.sh   # re-run from your project root
```

## Skills

| Skill | What it does |
|---|---|
| `caveman` | Ultra-compressed communication mode (~75% fewer tokens) |
| `grill-me` | Relentless interview protocol to stress-test a plan |
| `handoff` | Compact current conversation into a handoff doc for the next agent |
| `zoom-out` | Map all relevant modules/callers when unfamiliar with an area |
| `ubiquitous-language` | Extract DDD-style glossary from the conversation |
| `session-close` | End-of-session ritual: reconcile ROADMAPs → compute frontier → ratify → regenerate dashboard → Notion → calendar → commit |
| `push-notion-mirror` | Push canonical docs to Notion as a read-only mirror |

## Tools (copy into project's `tools/`)

| Tool | What it does |
|---|---|
| `ready_set.py` | Computes task dependency graph across all ROADMAP.md files → `docs/ready_set.json` |
| `notion_doc_sync.py` | Syncs local markdown docs to Notion pages (idempotent wipe-and-rewrite) |
| `create_session_task.py` | Creates a session-recap task in Notion's Progress Tasks DB |
| `notion_sync.py` | One-way projection of the ready frontier into Notion Progress Tasks |

## Credential model

| What | Where |
|---|---|
| `NOTION_TOKEN` | `~/.zshrc` env var — global, one per Notion workspace |
| `NOTION_TASKS_DB_ID` | `~/.zshrc` env var — global, same Progress Tasks DB across projects |
| `NOTION_CLASS_PAGE_ID` | `.claude/project.env` (gitignored) — per-project Notion class page |
| Doc page IDs | `conf/notion_mirror.toml` (committed) — per-project doc mapping |
| Script paths, calendar slot | `CLAUDE.md ## Claude Skills Config` — committed, no secrets |

## Setting up a new project

1. Run `install.sh` from the project root.
2. Add to `~/.zshrc` (if not already there):
   ```bash
   export NOTION_TOKEN="secret_xxx"
   export NOTION_TASKS_DB_ID="<32-char-db-id>"
   ```
3. Create `.claude/project.env` (gitignored):
   ```bash
   NOTION_CLASS_PAGE_ID=<notion-class-page-id-for-this-project>
   ```
4. Add `.claude/project.env` to `.gitignore`.
5. Create `conf/notion_mirror.toml` mapping local doc paths to Notion page IDs.
6. Add `## Claude Skills Config` to `CLAUDE.md`:
   ```markdown
   ## Claude Skills Config

   ### Session Management
   | key | value |
   |---|---|
   | frontier_script | `python tools/ready_set.py` |
   | ready_set_output | `docs/ready_set.json` |
   | dashboard_file | `DASHBOARD.md` |
   | calendar_slot_name | `<your-calendar-slot-name>` |

   ### Notion Integration
   | key | value |
   |---|---|
   | mirror_script | `python tools/notion_doc_sync.py` |
   | mirror_config | `conf/notion_mirror.toml` |
   | session_task_script | `python tools/create_session_task.py` |
   ```
