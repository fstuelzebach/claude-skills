# claude-skills

> There's a difference between *using* Claude Code and *working with* Claude Code.
> This repo is my answer to what the latter looks like.

Derived from [Matt Pocock's skills repo](https://github.com/mattpocock/skills) — he built the pattern, I adapted it for my own purposes. Matt's original is focused on engineering fundamentals: TDD, code review, spec writing, architecture. This fork is built around a different goal: **staying in command while delegating aggressively.**

That means two things in practice. Macro-level control: roadmaps, session continuity, a Notion second brain that means I always know where things stand and can pick up exactly where I left off. Micro-level excellence: precise skills that Claude can execute reliably without me having to re-explain how I work every time. The point isn't to vibe code and hope for the best. It's to build a working method that compounds — one where AI handles the execution and I handle the direction.

I'm not a developer. I'm a curious person who reads widely, thinks carefully, and uses these tools to build things that would otherwise take much longer or stay half-formed. This repo is how I keep that from drifting into chaos.

---

## What this is

I've built a system around Claude Code that operates at two levels: **skills** define how I work, and **Notion** is the second brain that gives that work continuity across sessions and projects.

Skills are not prompts. They are reusable behavioral protocols — precise instructions that shape how Claude Code thinks, communicates, and operates within a session. Some are about communication style. Some are about how a session opens and closes. Some are about how decisions get made and recorded. Together they form an opinionated method for working with Claude Code that is consistent, traceable, and improvable over time.

Notion is the memory layer. Without it, each session starts cold. With it, every session closes by pushing its output — reconciled task graphs, regenerated dashboards, mirrored docs — into a persistent second brain that Claude can read back in the next session. This is what makes the system compound rather than reset.

The two are intertwined: skills define the method, Notion gives it continuity. AI-assisted project work needs this kind of structure to scale — this repo is one opinionated answer to what that structure looks like.

---

## Skills

| Skill | Notion required? | What it does |
|---|---|---|
| `caveman` | No | Ultra-compressed communication mode (~75% fewer tokens, zero loss of precision) |
| `grill-me` | No | Relentless one-question-at-a-time interview to stress-test a plan or design before committing |
| `handoff` | No | Compact the current conversation into a structured handoff doc for the next agent or session |
| `zoom-out` | No | Map all relevant modules and callers when unfamiliar with an area of code |
| `ubiquitous-language` | No | Extract a DDD-style domain glossary from the conversation, saved to `UBIQUITOUS_LANGUAGE.md` |
| `session-close` | Steps 5–8 only | End-of-session ritual: reconcile ROADMAPs → compute dependency frontier → ratify order → regenerate dashboard → mirror to Notion → fill calendar slots → atomic commit |
| `push-notion-mirror` | Yes | Push canonical project docs (ROADMAPs, dashboard, CLAUDE.md, …) to Notion as a generated, read-only mirror |

---

## The Notion integration

I use a single Notion workspace as a second brain across all projects. Each project gets its own domain within it — its own mirror pages, its own entry in the Progress Tasks database — but the workspace, token, and database are shared globally.

This design choice is hardwired. It's not a plugin or an optional add-on; it's the memory architecture the `session-close` ritual is built around. The mirror keeps Notion current so it can be read on mobile, in Claude.ai, or anywhere outside the IDE. The Progress Tasks database tracks which sessions are scheduled and which have shipped.

**Skills without Notion still work.** The five general-purpose skills have no Notion dependency at all. `session-close` degrades gracefully — Steps 1–4 (ROADMAP reconciliation, frontier computation, ratification, dashboard regeneration, atomic commit) are pure git + markdown and work without any Notion configuration. Only Steps 5–8 require the integration.

---

## Tools (`tools/` — copied into each project once)

These are standalone Python scripts that the skills call. They are copied into the project's `tools/` directory on first install — not symlinked — so per-project customizations don't affect other projects.

| Tool | Notion required? | What it does |
|---|---|---|
| `ready_set.py` | No | Traverses `needs:`/`blocks:` dependency edges across all `ROADMAP.md` files → writes `docs/ready_set.json` with ready/blocked/rollup. Standard library only. |
| `notion_doc_sync.py` | Yes | Wipes and rewrites Notion pages from local markdown (idempotent). Reads doc→page mapping from `conf/notion_mirror.toml`. Auth via `NOTION_TOKEN` env var. |
| `create_session_task.py` | Yes | Creates a session-recap entry in a Notion Progress Tasks database, linked to a Google Calendar event. |
| `notion_sync.py` | Yes | One-way projection of the ready frontier into Notion Progress Tasks: creates pages for new ready tasks, archives pages for tasks that left the frontier. |

---

## Install into a project

```bash
# From the target project root:
bash ~/.claude-skills/install.sh
```

This symlinks every skill into `.claude/skills/<name>` and copies tools into `tools/` (first-time only). A `git pull` in `~/.claude-skills` automatically updates all symlinked projects.

---

## Setting up a new project

### 1 — Install skills and tools

```bash
cd /path/to/your/new-project
bash ~/.claude-skills/install.sh
```

### 2 — Add `## Claude Skills Config` to your `CLAUDE.md`

The generic skills read all project-specific paths from this section. No secrets here.

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

> Skip the Notion Integration table entirely if you're not using Notion.
> `session-close` will skip those steps automatically.

### 3 — Set global env vars (once per machine)

```bash
# Add to ~/.zshrc or ~/.zprofile
export NOTION_TOKEN="secret_xxx"       # Internal integration token — Notion Settings → Connections → your integration → Secret
export NOTION_TASKS_DB_ID="abc123..."  # Open your Progress Tasks DB in Notion, copy the URL → 32-char segment after the last /
```

### 4 — Create `.claude/project.env` (per project, gitignored)

The one thing that differs between projects: which Notion Class page tags tasks to this project.

```bash
# .claude/project.env — gitignored
NOTION_CLASS_PAGE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# Open the project's Class page in Notion → copy URL → UUID at the end
```

Add to `.gitignore`:
```
.claude/project.env
```

### 5 — Create `conf/notion_mirror.toml` (per project, committed)

Maps local markdown files to the Notion pages they mirror into. Page IDs are not secrets — the token is.

```toml
# conf/notion_mirror.toml

[[docs]]
key      = "dashboard"
path     = "DASHBOARD.md"
page_id  = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
# How to get a page ID: open the Notion page → Share → Copy link → UUID at the end of the URL
title    = "DASHBOARD"

[[docs]]
key      = "claude_md"
path     = "CLAUDE.md"
page_id  = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
title    = "CLAUDE.md"

# One [[docs]] block per file. Use --only <key> to sync a subset:
# python tools/notion_doc_sync.py --only dashboard
```

> The Notion integration must be connected to each target page: open the page → `···` → Connections → add your integration.

### 6 — Install Python dependencies

```bash
pip install notion-client requests
```

### 7 — Test the setup

```bash
# Preview (no writes):
source .claude/project.env && python tools/notion_doc_sync.py --dry-run

# Push for real:
source .claude/project.env && python tools/notion_doc_sync.py

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

| Credential | Where | Scope | How to find |
|---|---|---|---|
| `NOTION_TOKEN` | `~/.zshrc` | Global — one per Notion workspace | Notion Settings → Connections → your integration → Secret |
| `NOTION_TASKS_DB_ID` | `~/.zshrc` | Global — same Progress Tasks DB for all projects | Open DB in Notion, copy URL → 32-char segment |
| `NOTION_CLASS_PAGE_ID` | `.claude/project.env` (gitignored) | Per-project | Open the project's Class page in Notion, copy URL → UUID |
| Doc page IDs | `conf/notion_mirror.toml` (committed) | Per-project | Open each target Notion page, copy URL → UUID |
