#!/bin/bash
# install.sh — wire claude-skills into a project
#
# Run from the TARGET PROJECT ROOT:
#   bash ~/.claude-skills/install.sh
#
# What it does:
#   1. Symlinks every skill from this repo into .claude/skills/<name>
#   2. Copies tools/ into the project's tools/ (first-time copy; does NOT overwrite)
#
# To update skills after a `git pull` in ~/.claude-skills, just re-run this script.
# Symlinks auto-update; tool copies are untouched.

set -euo pipefail

SKILLS_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"

echo "→ Installing claude-skills into: $PROJECT_ROOT"
echo "  Skills source: $SKILLS_REPO/skills"

# 1. Symlink skills
SKILLS_DIR="$PROJECT_ROOT/.claude/skills"
mkdir -p "$SKILLS_DIR"

for skill_dir in "$SKILLS_REPO/skills"/*/; do
  skill_name="$(basename "$skill_dir")"
  target="$SKILLS_DIR/$skill_name"
  if [ -L "$target" ]; then
    echo "  ~ $skill_name (symlink already exists, updating)"
    ln -sf "$skill_dir" "$target"
  elif [ -d "$target" ]; then
    echo "  ! $skill_name (real dir exists — skipping; remove manually to replace with symlink)"
  else
    ln -s "$skill_dir" "$target"
    echo "  + $skill_name"
  fi
done

# 2. Copy tools (first-time only — do not overwrite project customizations)
if [ -d "$SKILLS_REPO/tools" ]; then
  TOOLS_DIR="$PROJECT_ROOT/tools"
  mkdir -p "$TOOLS_DIR"
  echo ""
  echo "→ Copying tools (skips existing files):"
  for tool in "$SKILLS_REPO/tools"/*; do
    tool_name="$(basename "$tool")"
    dest="$TOOLS_DIR/$tool_name"
    if [ -f "$dest" ]; then
      echo "  ~ $tool_name (exists, skipped)"
    else
      cp "$tool" "$dest"
      echo "  + $tool_name"
    fi
  done
fi

echo ""
echo "Done. Next steps for a new project:"
echo "  1. Add NOTION_TOKEN and NOTION_TASKS_DB_ID to ~/.zshrc"
echo "  2. Create .claude/project.env with NOTION_CLASS_PAGE_ID=<your-notion-class-page-id>"
echo "  3. Add .claude/project.env to .gitignore"
echo "  4. Set up conf/notion_mirror.toml with your doc page IDs"
echo "  5. Add '## Claude Skills Config' section to CLAUDE.md (see docs/SETUP_NOTION_MIRROR.md)"
