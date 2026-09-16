#!/bin/bash
# install.sh — wire claude-skills into a project
#
# Run from the TARGET PROJECT ROOT:
#   bash ~/.claude-skills/install.sh [--copy] [--adopt]
#
# What it does:
#   1. Installs every skill into .claude/skills/<name>
#   2. Installs every generic agent into .claude/agents/<name>.md
#   3. Copies hooks/ into .claude/hooks/ (first-time copy; does NOT overwrite)
#   4. Copies tools/ into the project's tools/ (first-time copy; does NOT overwrite)
#
# Link mode (macOS/Linux default): skills and agents are symlinks, so a `git pull`
# in ~/.claude-skills propagates immediately.
#
# Copy mode (Windows default, or --copy): Git Bash cannot create real symlinks
# without Developer Mode, so skills/agents are copied and recorded in
# .claude/.claude-skills-manifest. Re-running updates ONLY manifest entries —
# anything else with the same name is project-local and is never touched.
#
# --adopt  (copy mode) take over pre-existing same-named skills/agents that are not
#          yet in the manifest — use once when migrating a project whose skills were
#          hand-copied. Review `git diff .claude` afterwards.
#
# Project-local agents (e.g. .claude/agents/quant-reviewer.md) are always left alone.
# Hook registration is NOT automatic: merge settings.snippet.json into
# .claude/settings.json by hand (that file holds project permissions).

set -euo pipefail

SKILLS_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"
MANIFEST="$CLAUDE_DIR/.claude-skills-manifest"

MODE="link"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) MODE="copy" ;; esac
ADOPT=0
for arg in "$@"; do
  case "$arg" in
    --copy)  MODE="copy" ;;
    --adopt) ADOPT=1 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

echo "→ Installing claude-skills into: $PROJECT_ROOT  (mode: $MODE)"
mkdir -p "$CLAUDE_DIR/skills" "$CLAUDE_DIR/agents"
touch "$MANIFEST"

in_manifest() { grep -qxF "$1" "$MANIFEST"; }
add_manifest() { in_manifest "$1" || echo "$1" >> "$MANIFEST"; }

# install_item <source path> <target path> <manifest key>
install_item() {
  local src="${1%/}" target="$2" key="$3" name
  name="$(basename "$target")"
  if [ "$MODE" = "link" ]; then
    if [ -L "$target" ]; then
      ln -sfn "$src" "$target"; echo "  ~ $name (symlink updated)"
    elif [ -e "$target" ]; then
      echo "  ! $name (real file/dir exists — skipping; remove it to link instead)"
    else
      ln -s "$src" "$target"; echo "  + $name"
    fi
    return
  fi
  if [ -e "$target" ] || [ -L "$target" ]; then
    if in_manifest "$key" || [ "$ADOPT" = 1 ]; then
      rm -rf "$target"; cp -R "$src" "$target"; add_manifest "$key"
      echo "  ~ $name (updated)"
    else
      echo "  ! $name (project-local — skipping; use --adopt to take it over)"
    fi
  else
    cp -R "$src" "$target"; add_manifest "$key"; echo "  + $name"
  fi
}

# 1. Skills
echo ""; echo "→ Skills:"
for skill_dir in "$SKILLS_REPO/skills"/*/; do
  name="$(basename "$skill_dir")"
  install_item "$skill_dir" "$CLAUDE_DIR/skills/$name" "skills/$name"
done

# 2. Generic agents (domain agents stay per-project)
if [ -d "$SKILLS_REPO/agents" ]; then
  echo ""; echo "→ Agents:"
  for agent in "$SKILLS_REPO/agents"/*.md; do
    name="$(basename "$agent")"
    install_item "$agent" "$CLAUDE_DIR/agents/$name" "agents/$name"
  done
fi

# 2b. Retired/renamed items: manifest entries (copy mode) or symlinks into this repo
#     (link mode) whose source no longer exists are removed from the project.
echo ""; echo "→ Retired items:"
removed=0
if [ -s "$MANIFEST" ]; then
  while IFS= read -r key; do
    [ -z "$key" ] && continue
    if [ ! -e "$SKILLS_REPO/$key" ]; then
      rm -rf "${CLAUDE_DIR:?}/$key"
      grep -vxF "$key" "$MANIFEST" > "$MANIFEST.tmp" || true
      mv "$MANIFEST.tmp" "$MANIFEST"
      echo "  - $key (no longer in claude-skills — removed)"; removed=1
    fi
  done < <(cat "$MANIFEST")
fi
for link in "$CLAUDE_DIR/skills"/* "$CLAUDE_DIR/agents"/*; do
  if [ -L "$link" ] && [ ! -e "$link" ] && [[ "$(readlink "$link")" == "$SKILLS_REPO"* ]]; then
    rm -f "$link"; echo "  - $(basename "$link") (dangling symlink — removed)"; removed=1
  fi
done
[ "$removed" = 0 ] && echo "  (none)"

# first_copy <src dir> <dest dir> — copy files that don't exist yet
first_copy() {
  mkdir -p "$2"
  for f in "$1"/*; do
    local name; name="$(basename "$f")"
    if [ -e "$2/$name" ]; then
      if cmp -s "$f" "$2/$name"; then echo "  = $name (up to date)"
      else echo "  ~ $name (exists, differs — not overwritten; diff against $f)"; fi
    else
      cp "$f" "$2/$name"; echo "  + $name"
    fi
  done
}

# 3. Hooks (first-time only)
if [ -d "$SKILLS_REPO/hooks" ]; then
  echo ""; echo "→ Hooks (skips existing files):"
  first_copy "$SKILLS_REPO/hooks" "$CLAUDE_DIR/hooks"
fi

# 4. Tools (first-time only — do not overwrite project customizations)
if [ -d "$SKILLS_REPO/tools" ]; then
  echo ""; echo "→ Tools (skips existing files):"
  first_copy "$SKILLS_REPO/tools" "$PROJECT_ROOT/tools"
fi

[ -s "$MANIFEST" ] || rm -f "$MANIFEST"

echo ""
echo "Done. Next steps for a new project:"
echo "  1. Merge $SKILLS_REPO/settings.snippet.json into .claude/settings.json BY HAND"
echo "     (registers the commit guard; do not overwrite the file)"
echo "  2. Set NOTION_TOKEN and NOTION_TASKS_DB_ID globally (shell profile / user env vars)"
echo "  3. Create .claude/project.env with NOTION_CLASS_PAGE_ID=<your-notion-class-page-id>"
echo "  4. Add .claude/project.env to .gitignore"
echo "  5. Set up conf/notion_mirror.toml with your doc page IDs"
echo "  6. Add '## Claude Skills Config' section to CLAUDE.md (see README)"
