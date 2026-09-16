# Remote access — the planned-session model

*Decided 2026-09-16. Replaces an earlier wake-on-LAN / Raspberry Pi design, which was dropped.*

## The decision
**The desktop stays on, and sessions are planned.**

Designing for *unplanned* access means building a wake chain: BIOS flags, a magic-packet
sender, an always-on Pi, a boot service. You then debug that chain only when you are away from
the machine and least able to fix it. But planned work is the whole premise of this system:
`ready_set.py` computes what is eligible, `push-todos` puts it in Notion, and you schedule it. A
session that wasn't planned has no packet and no ratified track. Optimising access for it
optimises for the case the method exists to avoid.

Leaving the machine on is a single setting. The wake chain takes a weekend to build and is
something to maintain forever.

## ⚠️ The one-way door
**A remote shutdown cannot be undone remotely.** Once the desktop is off, Tailscale isn't
running, and only physical access brings it back.

> **Rule: shut down remotely only when you will next be *physically* at the machine.**
> Otherwise lock the screen and leave it running.

The one cheap escape hatch to check *before* travelling: many consumer routers can send a
wake-on-LAN packet from their admin page, with no extra hardware. It's the only part of the
dropped wake chain worth keeping.

## Setup — one evening, then leave it alone
| # | What | Why |
|---|---|---|
| 1 | **Tailscale** on desktop, laptop and phones, set to run **unattended** on the desktop | How you reach the machine. Without unattended mode, a reboot leaves it unreachable until someone logs in locally. It also replaces any public DNS exposure, which is strictly safer |
| 2 | **Power settings: never sleep, never hibernate** | Disk and display sleep are fine; system sleep kills the session |
| 3 | **Windows Update → notify**, not auto-restart | An unattended reboot is the realistic way this fails |
| 4 | Run `claude` once in the project dir by hand | Accepts the workspace trust dialog, which a service cannot answer |
| 5 | **Auto-start service** for `claude remote-control` | Makes a reboot mid-trip a non-event |
| 6 | **Test the full loop from your phone, off home wifi** | An empty session list means the service didn't start. Find that out at home, not abroad |

```bash
claude remote-control --spawn worktree --capacity 4 --name "olymp"
```

Auto-start per OS:
- **Windows** — Task Scheduler task, trigger *At startup*, "run whether user is logged on or not".
- **macOS** — `launchd` LaunchAgent with `RunAtLoad` + `KeepAlive`.
- **Linux** — `systemd --user` unit + `loginctl enable-linger`.

## The planned-session loop
```
at the desk       session-close → push-todos → Notion Tasks
                       ↓
in Notion         schedule the tasks you intend to do
                       ↓
before leaving    confirm remote-control is running
                       ↓
away              phone → Tailscale → desktop → the planned packet
                       ↓
end of trip       lock screen — or shut down only if returning physically
```

## Cloud sessions — optional, not on the critical path
Still useful in three cases: the desktop is off or rebooting and the work is repo-only; a long
autonomous build you'd rather keep off the machine; routines, which only run in the cloud.

**What cloud sessions can never do**, however they are configured:

| MCP / data | Local (Remote Control) | Cloud session |
|---|---|---|
| Servers added via `claude mcp add` | Yes | **No** — stored on the machine, not the account |
| claude.ai connectors (Notion, Gmail, …) | Yes | Yes |
| Committed `.mcp.json` | Yes | Yes |
| Local files, DuckDB, market data | Yes | **Never** |

Most real work in a data-heavy project reads local files. That is why the planned-session model
is *correct*, not just convenient.

If cloud sessions become a concrete need (deferred until then):
- `NOTION_TOKEN` → cloud environment **API credential** (stored outside the sandbox). IDs such as
  `NOTION_TASKS_DB_ID` / `NOTION_CLASS_PAGE_ID` are not secrets → environment variables.
- Add every outside host the work needs (data API, VPS, dashboard domain) to the environment's
  network allowlist. The default allowlist covers package registries only, so other hosts fail with 403.
- Move any MCP servers you want there to claude.ai connectors or a committed `.mcp.json`.
- **Never** put live broker credentials in any cloud environment.

## Secrets hygiene
The current setup (global env vars + gitignored `.claude/project.env`) keeps working unchanged,
because the work runs where that environment already lives. Worth doing, but not urgent:
- [ ] Check your shell profile (`~/.zshrc`) isn't syncing to a dotfiles repo, iCloud or Dropbox —
      the most common leak, and invisible until it isn't.
- [ ] Move to the OS keychain or a secret manager when convenient, keeping the variable names
      (`security find-generic-password`, `op read`, Windows Credential Manager) so skills keep working.
- [ ] Rotate anything already pasted into a chat, doc or screenshot, rather than reasoning about
      whether it mattered.

Never put secrets in the repo, `CLAUDE.md`, a mirrored doc, a prompt or skill file, or a Notion
page. `push-notion-mirror` refuses to push a doc that contains a secret; keep that guard.
