---
name: view-clean
description: Delete all temp files created by /view (claude_view_*.md in the OS temp directory) and report how many were removed. Use when the user types /view-clean, /view clean, or asks to clean up view files.
---

Run the shared helper from the `view` skill, which sits in the sibling folder of
this skill's base directory:

```
python "<this skill's base directory>/../view/view_files.py" clean
```

Report its one-line result to the user (e.g. `deleted 3 view file(s) from C:\Users\…\Temp`).
Nothing else is deleted — only files named `claude_view_*.md` in the temp directory.
