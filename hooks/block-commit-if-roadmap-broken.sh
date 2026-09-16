#!/bin/bash
# block-commit-if-roadmap-broken.sh — PreToolUse hook: deny `git commit` while the ROADMAP graph is broken.
#
# Registered for the Bash and PowerShell tools (see settings.snippet.json). It ignores
# every command except a real `git commit`. On a commit it runs
#   python tools/roadmap_frontier.py --check
# (read-only structural validation) and, if that fails, denies the tool call and hands
# the parser's errors back to Claude. Projects without tools/roadmap_frontier.py are a no-op.
#
# This enforces the session-close rule "if the parser errors, fix the ROADMAP syntax;
# do not work around it" mechanically. A Stop hook cannot do this — it fires after the
# turn and cannot block.

set -uo pipefail

PY=""
for cand in python python3; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "" >/dev/null 2>&1; then
    PY="$cand"; break
  fi
done
[ -z "$PY" ] && exit 0   # no python: fail open, never wedge the session

exec "$PY" -c '
import json, os, re, shlex, subprocess, sys
from pathlib import Path

try:
    event = json.load(sys.stdin)
except Exception:
    sys.exit(0)

cmd = (event.get("tool_input") or {}).get("command") or ""

# git global options that consume the next token
OPT_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

def is_git_commit(segment: str) -> bool:
    try:
        toks = shlex.split(segment, posix=True)
    except ValueError:
        toks = segment.split()
    i = 0
    # skip env assignments (FOO=bar git commit) and the PowerShell call operator
    while i < len(toks) and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[i]) or toks[i] == "&"):
        i += 1
    if i >= len(toks):
        return False
    exe = re.split(r"[\\/]", toks[i])[-1].lower()
    if exe not in ("git", "git.exe"):
        return False
    i += 1
    while i < len(toks) and toks[i].startswith("-"):
        i += 2 if toks[i] in OPT_WITH_ARG else 1
    return i < len(toks) and toks[i] == "commit"

segments = re.split(r"&&|\|\||;|\||\r?\n|\(|\)|\{|\}", cmd)
if not any(is_git_commit(s) for s in segments):
    sys.exit(0)

root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or ".")
script = root / "tools" / "roadmap_frontier.py"
if not script.exists() or "--check" not in script.read_text(encoding="utf-8", errors="replace"):
    sys.exit(0)   # no parser, or an old copy without --check: nothing to enforce

res = subprocess.run([sys.executable, str(script), "--check"], cwd=root,
                     capture_output=True, text=True, encoding="utf-8", errors="replace")
if res.returncode == 0:
    sys.exit(0)

detail = (res.stderr or res.stdout).strip()[-3000:]
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": (
        "Commit blocked: tools/roadmap_frontier.py --check failed. Fix the ROADMAP syntax "
        "(do not work around it), then commit again.\n" + detail),
}}))
sys.exit(0)
'
