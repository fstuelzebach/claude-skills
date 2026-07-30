---
name: view
description: Write the last Claude response to a temp file and open it in PyCharm so you can read and chat simultaneously. Use /view clean to delete all temp files.
---

You are implementing the /view skill.

**Default behavior (`/view`):**

1. Identify the most recent assistant message in this conversation — the one immediately before the user typed `/view`.
2. Write its full content verbatim (no reformatting, no added commentary) to `/tmp/claude_view_YYYYMMDD_HHMMSS.md` using the actual current timestamp.
3. Run `open -a "PyCharm" /tmp/claude_view_<timestamp>.md` via Bash to open it as a new PyCharm editor tab.
4. Tell the user: `Opened in PyCharm: /tmp/claude_view_<filename>` and remind them they can run `/view clean` to delete all view files when done.

**Cleanup (`/view clean`):**

1. Count existing files first: `ls /tmp/claude_view_*.md 2>/dev/null | wc -l`
2. Delete them: `rm -f /tmp/claude_view_*.md`
3. Report how many files were deleted.
