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
| `grill-me` | No | Dependency-aware interview in rounds of 2–4 questions (with recommendations) to stress-test a plan or design before committing; `quick` for one-at-a-time |
| `improve-prompt` | No | Diagnose a prompt against ten axes (scope, test data, permissions, evidence standard, output contract, candour, …) and return a paste-ready rewrite |
| `deepening` | No | Deepen a cluster of shallow modules safely — classify dependencies, choose seams/adapters, replace rather than layer tests |
| `view` | No | Write the last response to a temp file and open it in PyCharm, so you can read and chat side by side |
| `handoff` | No | Compact the current conversation into a structured handoff doc for the next agent or session |
| `zoom-out` | No | Map all relevant modules and callers when unfamiliar with an area of code |
| `ubiquitous-language` | No | Extract a DDD-style domain glossary from the conversation, saved to `UBIQUITOUS_LANGUAGE.md` |
| `session-close` | Steps 7 & 9 only | End-of-session ritual (v2): reconcile ROADMAPs → compute dependency frontier → group it into isolated parallel tracks → ratify → write task packets → regenerate dashboard → push open tasks to Notion → atomic commit → mirror docs |
| `push-todos` | Yes | Create-only projection of open tasks into the Notion Tasks DB (ready frontier by default, `all` for blocked too); ticks pages of done tasks, never archives, never sets dates |
| `push-notion-mirror` | Yes | Push canonical project docs (ROADMAPs, dashboard, CLAUDE.md, …) to Notion as a generated, read-only mirror |

---

## The Notion integration

I use a single Notion workspace as a second brain across all projects. Each project gets its own domain within it — its own mirror pages, its own entry in the Progress Tasks database — but the workspace, token, and database are shared globally.

This design choice is hardwired. It's not a plugin or an optional add-on; it's the memory architecture the `session-close` ritual is built around. The mirror keeps Notion current so it can be read on mobile, in Claude.ai, or anywhere outside the IDE. The Tasks database holds the open tasks (pushed by `push-todos`); scheduling happens there, by hand.

**Skills without Notion still work.** The general-purpose skills have no Notion dependency at all. `session-close` degrades gracefully — reconciliation, frontier computation, track grouping, packets, dashboard regeneration and the atomic commit are pure git + markdown. Only Step 7 (`push-todos`) and Step 9 (doc mirror) need the integration.

---

## Agents (`agents/` — installed into `.claude/agents/`)

Skills are instructions; agents are separate workers with their own context, model and tool set. Generic agents live here; **domain agents stay in the project** (e.g. a `quant-reviewer` committed to `.claude/agents/`) and the installer never touches them.

| Agent | Model | What it does |
|---|---|---|
| `scout` | haiku | Read-only exploration — where things live, callers, module summaries — so the main context stays clean |
| `explainer` | sonnet | Explains a diff in the project's domain language and asks comprehension questions. Advisory, never blocks |
| `implementer` | sonnet | Executes one task packet (`docs/packets/{task-id}.md`) inside its own git worktree, strictly within the packet's file boundary |

Deliberately **not** built: a "frontier agent". `ready_set.py` is deterministic graph traversal — putting a model in front of it would be a regression.

## Hooks (`hooks/` — copied into `.claude/hooks/` once)

Hooks give guarantees rather than instructions.

| Hook | Event | What it does |
|---|---|---|
| `guard-commit.sh` | `PreToolUse` on `Bash` / `PowerShell` | Ignores everything except a real `git commit`. On a commit it runs `python tools/ready_set.py --check`; if the ROADMAP graph is broken (duplicate ids, malformed task lines, unknown `needs:`, cycles) the commit is **denied** and the errors are handed back. No-op in projects without `tools/ready_set.py`. |

Registration is manual: merge [`settings.snippet.json`](settings.snippet.json) into the project's `.claude/settings.json` (don't overwrite it — it holds your permissions).

---

## Tools (`tools/` — copied into each project once)

These are standalone Python scripts that the skills call. They are copied into the project's `tools/` directory on first install — not symlinked — so per-project customizations don't affect other projects.

| Tool | Notion required? | What it does |
|---|---|---|
| `ready_set.py` | No | Traverses `needs:`/`blocks:` dependency edges across all `ROADMAP.md` files → writes `docs/ready_set.json` with ready/blocked/done/rollup. `--check` validates structure only (used by the commit guard). Standard library only. |
| `notion_doc_sync.py` | Yes | Wipes and rewrites Notion pages from local markdown (idempotent). Reads doc→page mapping from `conf/notion_mirror.toml`. Auth via `NOTION_TOKEN` env var. |
| `notion_sync.py` | Yes | Create-only projection of open tasks into the Notion Tasks DB (used by `push-todos`): creates missing pages, ticks pages of done tasks, never archives. `--all` includes blocked tasks; `--checked` lists open tasks ticked in Notion. Reads `.claude/project.env` itself. |

---

## Install into a project

```bash
# From the target project root:
bash ~/.claude-skills/install.sh
```

This installs every skill into `.claude/skills/<name>` and every generic agent into `.claude/agents/`, and copies `hooks/` and `tools/` (first-time only — existing files are never overwritten; the script tells you when they differ).

- **macOS / Linux:** skills and agents are symlinks, so a `git pull` in `~/.claude-skills` updates every project immediately.
- **Windows (Git Bash) or `--copy`:** Git Bash can't create real symlinks without Developer Mode, so items are copied and recorded in `.claude/.claude-skills-manifest`. After a `git pull`, re-run the installer — it refreshes only manifest entries and never touches project-local skills or agents.
- **`--adopt`:** migrating a project whose skills were copied by hand? Run once with `--adopt` to bring same-named items under the manifest, then review `git diff .claude`.

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
| packets_dir | `docs/packets` |

### Notion Integration
| key | value |
|---|---|
| mirror_script | `python tools/notion_doc_sync.py` |
| mirror_config | `conf/notion_mirror.toml` |
| todos_script | `python tools/notion_sync.py` |
```

> Skip the Notion Integration table entirely if you're not using Notion.
> `session-close` will skip those steps automatically.

### 3 — Set global env vars (once per machine)

On Windows, set them as user environment variables instead (`setx NOTION_TOKEN "secret_xxx"`).

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

# Check the Tasks DB connection and preview a todo push:
python tools/notion_sync.py --inspect
python tools/ready_set.py && python tools/notion_sync.py --dry-run
```

---

## Credential reference

| Credential | Where | Scope | How to find |
|---|---|---|---|
| `NOTION_TOKEN` | `~/.zshrc` / Windows user env | Global — one per Notion workspace | Notion Settings → Connections → your integration → Secret |
| `NOTION_TASKS_DB_ID` | `~/.zshrc` / Windows user env | Global — same Progress Tasks DB for all projects | Open DB in Notion, copy URL → 32-char segment |
| `NOTION_CLASS_PAGE_ID` | `.claude/project.env` (gitignored) | Per-project | Open the project's Class page in Notion, copy URL → UUID |
| Doc page IDs | `conf/notion_mirror.toml` (committed) | Per-project | Open each target Notion page, copy URL → UUID |

Never put secrets in the repo, `CLAUDE.md`, a mirrored doc, a skill file, or a Notion page. For remote access and secrets in cloud sessions, see [docs/REMOTE_ACCESS.md](docs/REMOTE_ACCESS.md).
