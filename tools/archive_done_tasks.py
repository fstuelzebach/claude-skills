#!/usr/bin/env python3
"""
archive_done_tasks.py  ·  Move finished tasks out of ROADMAP.md into CHANGELOG.md.

WHAT IT DOES
    For every docs/**/ROADMAP.md, cuts each done task block — the `- [x] **ID**`
    line plus its indented continuation lines — and appends it to CHANGELOG.md
    in the same folder, under the ROADMAP section heading it came from and a
    dated "Archived" heading. Open tasks, prose and headings stay put, so the
    ROADMAP shrinks back to "what is still to do" while the history is kept.

    roadmap_frontier.py reads CHANGELOG.md too (every task there counts as
    done), so needs: edges to archived tasks keep resolving and duplicate-id
    checks still span both files.

USAGE
    python tools/archive_done_tasks.py              # dry-run: what would move
    python tools/archive_done_tasks.py --apply      # move it
    python tools/archive_done_tasks.py --apply --only trading

    Run it from the session-close ritual about once a quarter, then run
    `python tools/roadmap_frontier.py --check` and commit both files together.

NO DEPENDENCIES  -- standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DONE_RE = re.compile(r'^\s*-\s*\[[xX]\]\s*\*\*[A-Za-z0-9_.\-]+\*\*')
TASK_RE = re.compile(r'^\s*-\s*\[[ xX]\]\s*\*\*[A-Za-z0-9_.\-]+\*\*')
HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')


def split_front_matter(lines: list[str]) -> tuple[list[str], list[str]]:
    if lines and lines[0].strip() == '---':
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                return lines[:i + 1], lines[i + 1:]
    return [], lines


def is_continuation(line: str) -> bool:
    return bool(line.strip()) and line[:1] in (' ', '\t') and not TASK_RE.match(line)


def extract(body: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Returns (kept lines, [(section heading, block lines), ...])."""
    kept: list[str] = []
    moved: list[tuple[str, list[str]]] = []
    heading = ''
    i = 0
    while i < len(body):
        line = body[i]
        m = HEADING_RE.match(line)
        if m:
            heading = m.group(2).strip()
        if DONE_RE.match(line):
            block = [line]
            j = i + 1
            while j < len(body):
                if is_continuation(body[j]):
                    block.append(body[j])
                    j += 1
                    continue
                # a blank line belongs to the block only if indented text follows
                if not body[j].strip():
                    k = j
                    while k < len(body) and not body[k].strip():
                        k += 1
                    if k < len(body) and is_continuation(body[k]):
                        block.extend(body[j:k])
                        j = k
                        continue
                break
            moved.append((heading, block))
            i = j
            # drop one now-redundant blank separator left behind
            if kept and not kept[-1].strip() and i < len(body) and not body[i].strip():
                i += 1
            continue
        kept.append(line)
        i += 1
    return kept, moved


def changelog_text(existing: str, sub: str, moved: list[tuple[str, list[str]]]) -> str:
    out: list[str] = []
    if not existing.strip():
        out += [f"# {sub} — CHANGELOG", "",
                "Finished tasks moved here from ROADMAP.md by `tools/archive_done_tasks.py`.",
                "Every task in this file counts as done for `tools/roadmap_frontier.py`.", ""]
    else:
        out.append(existing.rstrip('\n'))
        out.append("")
    out += [f"## Archived {date.today()}", ""]
    current = None
    for heading, block in moved:
        if heading != current:
            out += [f"### {heading or '(no section)'}", ""]
            current = heading
        out += block
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Move done ROADMAP tasks into CHANGELOG.md.")
    ap.add_argument('--root', default='docs')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--only', nargs='*', help="sub-project folder names to process")
    args = ap.parse_args()

    total = 0
    for roadmap in sorted(Path(args.root).glob('**/ROADMAP.md')):
        if args.only and roadmap.parent.name not in args.only:
            continue
        raw = roadmap.read_text(encoding='utf-8')
        nl = '\r\n' if '\r\n' in raw else '\n'
        lines = raw.replace('\r\n', '\n').split('\n')
        fm, body = split_front_matter(lines)
        kept, moved = extract(body)
        if not moved:
            continue
        sub = next((l.split(':', 1)[1].strip() for l in fm if l.startswith('sub_project:')),
                   roadmap.parent.name)
        n_lines = sum(len(b) for _, b in moved)
        total += len(moved)
        print(f"{roadmap}: {len(moved)} done task(s), {n_lines} lines -> CHANGELOG.md "
              f"({len(lines)} -> {len(fm) + len(kept)} lines)")
        if args.apply:
            changelog = roadmap.with_name('CHANGELOG.md')
            existing = changelog.read_text(encoding='utf-8') if changelog.exists() else ''
            changelog.write_text(changelog_text(existing, sub, moved).replace('\n', nl),
                                 encoding='utf-8', newline='')
            roadmap.write_text('\n'.join(fm + kept).replace('\n', nl), encoding='utf-8', newline='')
    print(f"{'moved' if args.apply else 'would move'} {total} task(s)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
