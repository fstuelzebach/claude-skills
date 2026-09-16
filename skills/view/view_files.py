#!/usr/bin/env python3
"""
view_files.py — helper for the /view and /view-clean skills (macOS, Windows, Linux).

    python view_files.py path          # print a fresh view-file path in the OS temp dir
    python view_files.py open <file>   # open <file> in PyCharm (falls back to the OS default app)
    python view_files.py clean         # delete all view files, print how many

Standard library only.
"""
from __future__ import annotations

import glob
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

PREFIX = "claude_view_"


def view_dir() -> Path:
    return Path(tempfile.gettempdir())


def new_path() -> Path:
    return view_dir() / f"{PREFIX}{datetime.now():%Y%m%d_%H%M%S}.md"


def _windows_pycharm() -> str | None:
    roots = [os.environ.get("ProgramFiles", r"C:\Program Files"),
             os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "JetBrains", "Toolbox", "apps")]
    # explicit install layouts only — a recursive scan of Program Files takes minutes
    patterns = [
        os.path.join("JetBrains", "PyCharm*", "bin", "pycharm64.exe"),     # standard installer
        os.path.join("PyCharm*", "bin", "pycharm64.exe"),                  # per-user / Toolbox 2.x
        os.path.join("PyCharm*", "*", "bin", "pycharm64.exe"),             # Toolbox 1.x (ch-0/<build>)
        os.path.join("PyCharm*", "*", "*", "bin", "pycharm64.exe"),
    ]
    hits: list[str] = []
    for root in roots:
        if root and os.path.isdir(root):
            for pat in patterns:
                hits += glob.glob(os.path.join(root, pat))
    # newest install wins (version is part of the folder name)
    return sorted(hits)[-1] if hits else None


def open_file(path: str) -> str:
    system = platform.system()
    for cli in ("pycharm", "pycharm64", "charm", "pycharm-community"):
        exe = shutil.which(cli)
        if exe:
            subprocess.Popen([exe, path])
            return f"PyCharm ({exe})"
    if system == "Darwin":
        for app in ("PyCharm CE", "PyCharm", "PyCharm Community Edition"):
            if subprocess.run(["open", "-a", app, path], capture_output=True).returncode == 0:
                return app
        subprocess.run(["open", path])
        return "default app (PyCharm not found)"
    if system == "Windows":
        exe = _windows_pycharm()
        if exe:
            subprocess.Popen([exe, path], creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
            return f"PyCharm ({exe})"
        os.startfile(path)  # type: ignore[attr-defined]
        return "default app (PyCharm not found)"
    subprocess.Popen(["xdg-open", path])
    return "default app (PyCharm not found)"


def clean() -> int:
    files = list(view_dir().glob(f"{PREFIX}*.md"))
    for f in files:
        f.unlink(missing_ok=True)
    return len(files)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "path":
        print(new_path())
    elif cmd == "open" and len(sys.argv) == 3:
        print(f"opened with {open_file(sys.argv[2])}")
    elif cmd == "clean":
        print(f"deleted {clean()} view file(s) from {view_dir()}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
