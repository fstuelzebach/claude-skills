---
name: view
description: Write the last Claude response to a temp file and open it in PyCharm (macOS, Windows, Linux) so you can read and chat side by side. Use /view-clean to delete the view files.
---

You are implementing the /view skill. The helper script sits next to this file:
`{this skill's base directory}/view_files.py` (standard-library Python, any OS).

1. Identify the most recent assistant message in this conversation — the one
   immediately before the user typed `/view`.
2. Get a fresh file path: `python "<base dir>/view_files.py" path`
   (it lives in the OS temp directory and is named `claude_view_YYYYMMDD_HHMMSS.md`).
3. Write the message's full content verbatim (no reformatting, no added commentary)
   to that path with the Write tool.
4. Open it: `python "<base dir>/view_files.py" open "<path>"`. The script finds
   PyCharm on macOS (`open -a`), Windows (`pycharm64.exe` under Program Files /
   Toolbox) and Linux (`pycharm` on PATH), and falls back to the OS default app.
5. Tell the user: `Opened in PyCharm: <path>` (or the fallback the script reported),
   and remind them that `/view-clean` deletes all view files.

If the user typed `/view clean`, do what the `view-clean` skill does instead.
