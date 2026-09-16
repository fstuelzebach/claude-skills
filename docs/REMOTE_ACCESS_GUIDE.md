# Remote access — step-by-step guide (Stage 3)

*Companion to [REMOTE_ACCESS.md](REMOTE_ACCESS.md), which records **why** (planned sessions,
desktop stays on). This file is the **how**, written to be followed without prior knowledge.
Checked against Claude Code 2.1.273 on Windows 11, 2026-09-16.*

---

## 1. The two tools in one minute

| | **Remote Control** (`claude remote-control`) | **Tailscale** |
|---|---|---|
| What it is | A Claude Code mode that makes Claude sessions **on your desktop** controllable from **claude.ai/code** in a browser or the **Claude mobile app** | A private network (VPN) between *your own* devices, wherever they are |
| What you get | Type to Claude on your phone; Claude works on the desktop with the desktop's files, databases, MCP servers and credentials | Your phone/laptop can reach the desktop as if it were on your home Wi-Fi: SSH, Remote Desktop, `http://desktop:3000` |
| How it connects | The desktop opens an **outgoing** connection to Anthropic; your phone talks to Anthropic. No open ports, no VPN needed | Each device runs Tailscale and gets a private `100.x.y.z` address; traffic is encrypted device-to-device |
| Needs on the desktop | Claude Code installed and logged in, the command running, the PC **awake** and online | Tailscale installed, signed in, "run unattended" on |
| Costs | Included in your Claude plan | Free "Personal" plan (up to 100 devices, 3 users) |

**The key point:** Remote Control does **not** need Tailscale. The earlier plan drew
"phone → Tailscale → desktop → Claude"; the real path is **phone → Claude app → Anthropic →
desktop**. Tailscale is the *second* tool, for everything that isn't a Claude chat:
looking at the local dashboard, opening a terminal (SSH), seeing the actual screen (Remote
Desktop), fixing things when Claude itself is stuck.

Both tools need the same thing from the desktop: **awake and online**. A sleeping or
switched-off PC is unreachable by either one.

```
                ┌──────────── Anthropic (claude.ai) ────────────┐
 phone / browser│  Claude app  ◀────────────▶  session relay    │◀── outgoing ── desktop:
                └───────────────────────────────────────────────┘                claude remote-control
                                                                                 (D:\olymp_capital)
 phone / laptop ── Tailscale (encrypted, 100.x.y.z) ───────────────────────────▶ desktop:
                                                                                 SSH · RDP · :3000 dashboard
```

---

## 2. Prerequisites — the desktop must stay awake

This is the step everything else depends on. Your desktop is currently set to **sleep after
5 hours on AC power**, and the Olymp scheduler **hibernates the PC after every scheduled
run**. Either one ends a remote session.

### 2.1 Power settings (5 minutes)
Settings → System → Power & battery → Screen, sleep & hibernate timeouts:
- *Turn my screen off after*: anything (screen-off is harmless)
- *Make my device sleep after*: **Never** (plugged in)
- *Make my device hibernate after*: **Never** (plugged in)

Or in an **Administrator** PowerShell:
```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 15
```
Check: `powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` → the AC value must read `0x00000000`.

### 2.2 Tell the scheduler the PC is always on
In `D:\olymp_capital\conf\schedule.toml` set `always_on = true` (in `[scheduler]`). This
turns off the post-run hibernate and the "late trigger" skip. Do it **only after 2.1**,
otherwise the scheduler would stop hibernating a PC that still sleeps on its own.

### 2.3 Windows Update — no surprise reboots
Settings → Windows Update → Advanced options:
- *Get me up to date*: **Off** (this one forces restarts ASAP)
- *Notify me when a restart is required*: **On**
- *Active hours*: set them to cover the hours you usually work remotely

Windows can still reboot eventually; step 4 makes a reboot survivable.

### 2.4 Optional — Fast Startup off
Control Panel → Power Options → *Choose what the power buttons do* → *Change settings that
are currently unavailable* → untick **Turn on fast startup**. Only matters if you ever shut
down and want Wake-on-LAN to work; harmless otherwise.

---

## 3. Remote Control — first run by hand (10 minutes)

1. Open a terminal **on the desktop**:
   ```powershell
   cd D:\olymp_capital
   claude
   ```
   If Claude asks whether you trust this folder, answer **yes**. A background service can't
   answer that question, which is why this runs once by hand. Type `/exit`.
2. Start Remote Control:
   ```powershell
   claude remote-control --spawn worktree --capacity 4 --name "olymp"
   ```
   - `--spawn worktree`: each new session you start from the phone gets its **own git
     worktree** (a separate checkout), so two sessions can't overwrite each other's files.
   - `--capacity 4`: at most 4 sessions at once.
   - `--name "olymp"`: the name shown in the app.
   - Leave this window open. As long as it runs, the desktop is reachable.
3. On the phone: Claude app → **Code** → you should see **olymp** listed. Open it and ask
   something harmless: *"Run `git status` and tell me the branch."* The answer must match
   the desktop.
4. Now repeat step 3 **with Wi-Fi off** (mobile data). This proves it works away from home.

If the session list is empty: the command isn't running, or the desktop isn't logged in to
the same Claude account (`claude` → `/status`).

**Worth knowing:**
- `claude remote-control --continue` reattaches to the last session in this folder, if it
  was recorded within about 4 hours.
- `--permission-mode` sets what spawned sessions may do without asking. The project's
  `.claude/settings.json` already defines permissions; leave the flag off unless you want
  to override them.
- Each spawned worktree is a branch. Finished work gets merged by the normal session-close
  ritual, not automatically.

---

## 4. Remote Control — start automatically after a reboot (15 minutes)

A Windows Update reboot while you're away would otherwise end remote access for the trip.

1. Make sure **automatic sign-in** is acceptable to you. A task that runs "at log on"
   needs a logged-in user. The simplest robust setup is: the PC signs in to your account on
   boot, then locks itself. (Settings → Accounts → Sign-in options; automatic sign-in on
   Windows 11 requires turning off *"For improved security, only allow Windows Hello
   sign-in"* and using `netplwiz`. This is a real security trade-off for a machine others
   can touch physically — decide consciously.)
2. Register the task in an **Administrator** PowerShell:
   ```powershell
   $claude = (Get-Command claude).Source
   $action  = New-ScheduledTaskAction -Execute $claude `
                -Argument 'remote-control --spawn worktree --capacity 4 --name "olymp"' `
                -WorkingDirectory 'D:\olymp_capital'
   $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
   $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
                -ExecutionTimeLimit ([TimeSpan]::Zero)
   Register-ScheduledTask -TaskName 'Olymp-RemoteControl' -Action $action `
       -Trigger $trigger -Settings $settings -RunLevel Limited
   ```
   - *At log on* (not *At startup*): the Claude login lives in your user profile.
   - *RestartCount*: if the command ever exits, Windows restarts it every minute.
   - *ExecutionTimeLimit 0*: never killed for running "too long".
3. Test: restart the PC, **don't touch it**, and check the phone. `olymp` must appear
   within a couple of minutes. If not: Task Scheduler → *Olymp-RemoteControl* → *History*
   and *Last Run Result*.

To stop it: `Disable-ScheduledTask -TaskName Olymp-RemoteControl`.

---

## 5. Tailscale (20 minutes)

### 5.1 Install and sign in
1. Desktop: download from **tailscale.com/download** → Windows → install → sign in (Google or
   GitHub account; use the same one on every device).
2. In the Tailscale tray icon → **Preferences → Run unattended** ✔. Without this, Tailscale
   only runs while you're logged in interactively. After a reboot the PC would be off the
   network until someone logs in.
3. Phone(s): App Store / Google Play (Fairphone: Play Store or F-Droid build) → "Tailscale"
   → same account → connect.
4. Mac: Mac App Store → Tailscale → same account.
5. Admin console (**login.tailscale.com/admin/machines**): all devices listed. On the
   desktop's row → *…* → **Disable key expiry**, so it never silently drops off after 180 days.

Each device now has a name (e.g. `desktop-fabian`) that works from any other device when
MagicDNS is on (default).

### 5.2 What to use it for
| Goal | How |
|---|---|
| See the local dashboard | phone browser → `http://desktop-fabian:3000`. The dev servers must listen on all interfaces, not only `localhost`. Check with `launchers\start_dashboard.bat` first |
| Terminal on the desktop | `ssh fabian@desktop-fabian`. OpenSSH Server already runs on the desktop (see `docs/WINDOWS_MAC_SYNC.md`). On the phone use an SSH app (Termius, Blink) |
| See the actual screen | Windows **Pro**: enable Remote Desktop (Settings → System → Remote Desktop), connect with the *Windows App* to `desktop-fabian`. Windows Home has no RDP host; use Chrome Remote Desktop or RustDesk instead |
| Replace duckdns | Anything you exposed publicly only to reach it yourself can be reached over Tailscale instead, with no public port |

### 5.3 Security notes
- Tailscale devices can reach **every** port on each other. Keep Windows Firewall on. In
  the admin console, *Access controls* can narrow this later.
- Use Tailscale's **two-factor** via your identity provider (Google/GitHub 2FA on).
- A lost phone: remove it in the admin console, and it's cut off immediately.

---

## 6. Pros and cons

| | Pros | Cons |
|---|---|---|
| **Remote Control** | Full power of the desktop (local DuckDB, `metadata.db`, MCP servers, credentials) from anywhere; nothing exposed to the internet; no extra software on the phone besides the Claude app; worktree mode keeps parallel sessions apart | Desktop must be awake and online; a crash or reboot drops sessions (step 4 limits the damage); chat-only view, so you don't *see* the dashboard; runs with your real credentials, so permission settings matter |
| **Tailscale** | Reach anything on the desktop, not just Claude; encrypted; no port forwarding; free; works for the Mac too | Another app on every device; unattended mode + disabled key expiry must be set or it quietly stops working; an extra account to protect |
| **Desktop always on** | Scheduler runs on time (no more silent skips); remote access always there | A few euros of electricity a month; fan noise; auto sign-in (step 4) weakens physical security |
| **Cloud sessions** (alternative) | Work even when the desktop is off | Can never read local data or machine-only MCP servers, so they're useless for most Olymp work |

---

## 7. The one-way door (read before every trip)

**Never shut the desktop down remotely unless you'll next be physically at it.** Once it's
off, neither Remote Control nor Tailscale can bring it back. Lock the screen instead.
Before travelling, check whether your router's admin page can send a **Wake-on-LAN** packet.
That's the only rescue for a switched-off PC, and it needs WoL enabled in the BIOS plus
Fast Startup off (2.4).

---

## 8. Before-you-leave checklist

- [ ] Power: sleep and hibernate = Never (2.1); `always_on = true` (2.2)
- [ ] Remote Control task registered, and a reboot test passed (4)
- [ ] Phone reaches `olymp` **on mobile data** (3.4)
- [ ] Tailscale: desktop shows *Connected*, run unattended ✔, key expiry disabled (5.1)
- [ ] `ssh fabian@desktop-fabian` works from the phone or Mac (5.2)
- [ ] Router Wake-on-LAN checked (7)
- [ ] ntfy app on the phone subscribed to the Olymp topic, so you hear about data problems
- [ ] The tasks you plan to do are scheduled in Notion (planned-session loop)

## 9. When something breaks

| Symptom | Likely cause | Fix |
|---|---|---|
| `olymp` missing in the app | PC asleep/off, task not running, or logged out of Claude | Via Tailscale: `ssh` in → `schtasks /query /tn Olymp-RemoteControl /v` → `schtasks /run /tn Olymp-RemoteControl` |
| Tailscale shows the desktop *offline* | PC asleep/off, or "run unattended" off | Nothing to do remotely; fix at home |
| Session answers but can't write files | permission mode / settings | Adjust `.claude/settings.json`, restart the task |
| Phone push "Olymp data is STALE" | scheduler skipped or failed | `ssh` in → `python scripts\status_data_freshness.py`, check `logs\scheduler_*.log` |
