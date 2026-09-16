#!/usr/bin/env python3
"""
ready_set.py  ·  Deterministic eligibility computer for the Olymp Capital workflow.

WHAT IT DOES
    Reads every docs/**/ROADMAP.md, parses the structured task graph, and computes
    -- by code, not by an LLM eyeballing markdown -- which tasks are actually
    actionable *now* (the "ready frontier"). Also emits per-sub-project rollups,
    a blocked list with reasons, and redundancy flags.

WHY IT EXISTS
    "Which tasks are unblocked?" is graph traversal. It is mechanical and an LLM
    gets it subtly and silently wrong across multiple files. So the graph math is
    done here, deterministically; Claude Code then reasons (ordering, narrative)
    on top of guaranteed-correct input.

USAGE
    python tools/ready_set.py                 # print summary + write docs/ready_set.json
    python tools/ready_set.py --json           # print full JSON to stdout
    python tools/ready_set.py --root docs      # point at a different docs root

NO DEPENDENCIES  -- standard library only, so it runs anywhere with Python 3.8+.

TASK LINE FORMAT (in any ROADMAP.md)
    - [ ] **T3** Chunk dedup `needs:T1,T7` `blocks:T9` `prio:2`
    - [x] **T1** Schema parser
    Status comes from the checkbox: [x]/[X] = done, [ ] = not done.
    Readiness is COMPUTED, never authored: a not-done task is "ready" iff every
    id in its needs is done; otherwise it is "blocked".
    Bare ids (T1) resolve within the file's sub_project; cross-project refs are
    namespaced (ingestion.T3).

FRONT-MATTER (top of each ROADMAP.md, optional but recommended)
    ---
    sub_project: ingestion
    status: active          # active | paused | done   (only 'active' feeds the frontier)
    priority: 2             # 1 = highest; orders the frontier
    depends_on: [schema]    # informational; gates are enforced at task level via needs
    ---
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

# Windows consoles default stdout to cp1252, which chokes on the -> arrows
# authored in some ROADMAP task titles/notes. Force UTF-8 so printing never
# crashes after the (already-written) JSON output is safely on disk.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TASK_RE = re.compile(r'^\s*-\s*\[([ xX])\]\s*\*\*([A-Za-z0-9_.\-]+)\*\*\s*(.*)$')
TAG_RE  = re.compile(r'`([a-zA-Z_]+):([^`]+)`')


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Return (front_matter_dict, body). Flat keys only; lists written as [a, b]."""
    fm: dict = {}
    if not text.startswith('---'):
        return fm, text
    end = text.find('\n---', 3)
    if end == -1:
        return fm, text
    block = text[3:end].strip()
    body = text[end + 4:]
    for line in block.splitlines():
        if ':' not in line:
            continue
        key, _, val = line.partition(':')
        key, val = key.strip(), val.strip()
        if val.startswith('[') and val.endswith(']'):
            inner = val[1:-1].strip()
            fm[key] = [v.strip() for v in inner.split(',') if v.strip()] if inner else []
        else:
            fm[key] = val
    return fm, body


_NONE_PLACEHOLDERS = {'—', '-', 'none'}


def split_ids(raw: str) -> list[str]:
    # `—` (em dash) is the established ROADMAP convention for "no needs/blocks" —
    # every prior use happened to sit on an already-[x]-done task, where an
    # unresolvable phantom dependency is silently harmless (done tasks skip
    # readiness computation entirely), so this never surfaced until a not-done
    # task used the same placeholder.
    return [p.strip() for p in raw.split(',') if p.strip() and p.strip().lower() not in _NONE_PLACEHOLDERS]


def parse_roadmap(path: Path, docs_root: Path) -> dict:
    text = path.read_text(encoding='utf-8')
    fm, body = parse_front_matter(text)
    # sub_project defaults to the parent folder name if not declared.
    sub = fm.get('sub_project') or path.parent.name
    try:
        priority = int(fm.get('priority', 99))
    except ValueError:
        priority = 99
    project = {
        'sub_project': sub,
        'status': (fm.get('status') or 'active').lower(),
        'priority': priority,
        'depends_on': fm.get('depends_on', []),
        'path': str(path.relative_to(docs_root.parent)) if docs_root.parent in path.parents else str(path),
        'tasks': [],
    }
    order = 0
    for line in body.splitlines():
        m = TASK_RE.match(line)
        if not m:
            continue
        status_char, tid, rest = m.groups()
        tags = {k.lower(): v for k, v in TAG_RE.findall(rest)}
        title = TAG_RE.sub('', rest).strip()
        project['tasks'].append({
            'id': tid,
            'gid': f'{sub}.{tid}' if '.' not in tid else tid,
            'title': title,
            'done': status_char.lower() == 'x',
            'needs': [resolve(n, sub) for n in split_ids(tags.get('needs', ''))],
            'blocks': [resolve(b, sub) for b in split_ids(tags.get('blocks', ''))],
            'prio': int(tags['prio']) if tags.get('prio', '').isdigit() else None,
            'order': order,
        })
        order += 1
    return project


def resolve(ref: str, sub: str) -> str:
    """Bare id -> namespaced under current sub_project; already-namespaced kept."""
    return ref if '.' in ref else f'{sub}.{ref}'


def normalize_title(t: str) -> str:
    return re.sub(r'[^a-z0-9 ]', '', t.lower()).strip()


def compute(docs_root: Path) -> dict:
    roadmaps = sorted(docs_root.glob('**/ROADMAP.md'))
    projects = [parse_roadmap(p, docs_root) for p in roadmaps]

    all_tasks: dict[str, dict] = {}
    for proj in projects:
        for t in proj['tasks']:
            t['_proj_status'] = proj['status']
            t['_proj_priority'] = proj['priority']
            all_tasks[t['gid']] = t
    done = {gid for gid, t in all_tasks.items() if t['done']}

    ready, blocked = [], []
    for gid, t in all_tasks.items():
        if t['done'] or t['_proj_status'] != 'active':
            continue
        unmet = [n for n in t['needs'] if n not in done]
        # A reference to an unknown task is treated as unmet (fail safe, not silent).
        record = {
            'gid': gid, 'sub_project': gid.split('.')[0], 'title': t['title'],
            'needs': t['needs'], 'blocks': t['blocks'],
        }
        if unmet:
            record['waiting_on'] = unmet
            blocked.append(record)
        else:
            record['_sort'] = (t['prio'] if t['prio'] is not None else t['_proj_priority'], t['order'])
            ready.append(record)
    ready.sort(key=lambda r: r.pop('_sort'))

    # Rollup per sub-project.
    rollup = []
    for proj in projects:
        tasks = proj['tasks']
        n = len(tasks)
        ndone = sum(1 for t in tasks if t['done'])
        nready = sum(1 for r in ready if r['sub_project'] == proj['sub_project'])
        nblocked = sum(1 for b in blocked if b['sub_project'] == proj['sub_project'])
        rollup.append({
            'sub_project': proj['sub_project'], 'status': proj['status'],
            'priority': proj['priority'], 'total': n, 'done': ndone,
            'ready': nready, 'blocked': nblocked,
            'pct_done': round(100 * ndone / n) if n else 0,
        })
    rollup.sort(key=lambda r: r['priority'])

    # Redundancy: same normalized title across different task ids.
    seen: dict[str, str] = {}
    redundancies = []
    for gid, t in all_tasks.items():
        key = normalize_title(t['title'])
        if not key:
            continue
        if key in seen and seen[key] != gid:
            redundancies.append({'title': t['title'], 'tasks': [seen[key], gid]})
        else:
            seen[key] = gid

    return {
        'generated_from': str(docs_root),
        'ready': ready,
        'blocked': blocked,
        'rollup': rollup,
        'redundancies': redundancies,
        # Done gids (all sub-projects) — lets notion_sync tick checkboxes without guessing.
        'done': sorted(done),
        'counts': {'ready': len(ready), 'blocked': len(blocked),
                   'sub_projects': len(projects), 'tasks': len(all_tasks)},
    }


def print_summary(d: dict) -> None:
    c = d['counts']
    print(f"\n  READY FRONTIER — {c['ready']} actionable / {c['blocked']} blocked "
          f"across {c['sub_projects']} sub-projects ({c['tasks']} tasks)\n")
    if d['ready']:
        print("  NOW / NEXT (dependency-ordered, eligible):")
        for r in d['ready']:
            unlocks = f"  -> unlocks {', '.join(r['blocks'])}" if r['blocks'] else ''
            print(f"    [{r['sub_project']}] {r['gid']}  {r['title']}{unlocks}")
    else:
        print("  Nothing ready. Everything is done, blocked, or paused.")
    print("\n  ROLLUP:")
    for r in d['rollup']:
        print(f"    {r['sub_project']:<18} {r['pct_done']:>3}% done  "
              f"| ready {r['ready']}  blocked {r['blocked']}  ({r['status']})")
    if d['redundancies']:
        print("\n  ⚠ POSSIBLE REDUNDANCIES (review):")
        for x in d['redundancies']:
            print(f"    '{x['title']}'  ->  {' / '.join(x['tasks'])}")
    print()


# A line that is clearly *trying* to be a task (checkbox + bold id, or dependency
# tags) but does not parse — the parser would silently skip it.
LOOSE_TASK_RE = re.compile(r'^\s*[-*+]\s*\[[^\]]*\].*(\*\*[A-Za-z0-9_.\-]+\*\*|`(needs|blocks):)')


def validate(docs_root: Path) -> list[str]:
    """Structural errors that would silently corrupt the frontier. Empty = OK."""
    errors: list[str] = []
    projects = []
    for path in sorted(docs_root.glob('**/ROADMAP.md')):
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError as e:
            errors.append(f"{path}: not valid UTF-8 ({e})")
            continue
        _, body = parse_front_matter(text)
        offset = text[:len(text) - len(body)].count('\n')
        for i, line in enumerate(body.splitlines(), start=1 + offset):
            if LOOSE_TASK_RE.match(line) and not TASK_RE.match(line):
                errors.append(f"{path}:{i}: malformed task line: {line.strip()[:80]}")
        projects.append((path, parse_roadmap(path, docs_root)))

    tasks: dict[str, tuple[Path, dict]] = {}
    for path, proj in projects:
        for t in proj['tasks']:
            if t['gid'] in tasks:
                errors.append(f"{path}: duplicate task id {t['gid']} "
                              f"(also in {tasks[t['gid']][0]})")
            else:
                tasks[t['gid']] = (path, t)

    # Dangling refs only matter on open tasks (done tasks skip readiness).
    for gid, (path, t) in tasks.items():
        if t['done']:
            continue
        for ref in t['needs']:
            if ref not in tasks:
                errors.append(f"{path}: {gid} needs unknown task {ref}")

    # Cycles among open tasks would block each other forever.
    open_needs = {g: [n for n in t['needs'] if n in tasks and not tasks[n][1]['done']]
                  for g, (_, t) in tasks.items() if not t['done']}
    state: dict[str, int] = {}

    def visit(g: str, stack: list[str]) -> None:
        state[g] = 1
        for n in open_needs.get(g, []):
            if state.get(n) == 1:
                errors.append("dependency cycle: " + " -> ".join(stack[stack.index(n):] + [n]))
            elif n not in state:
                visit(n, stack + [n])
        state[g] = 2

    for g in open_needs:
        if g not in state:
            visit(g, [g])
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute the ready frontier from ROADMAP.md files.")
    ap.add_argument('--root', default='docs', help="docs root to scan (default: docs)")
    ap.add_argument('--json', action='store_true', help="print full JSON to stdout")
    ap.add_argument('--out', default='docs/ready_set.json', help="where to write the JSON")
    ap.add_argument('--check', action='store_true',
                    help="validate ROADMAP structure only; write nothing; exit 1 on errors")
    args = ap.parse_args()

    docs_root = Path(args.root)
    if not docs_root.exists():
        print(f"error: docs root '{docs_root}' not found (run from repo root)", file=sys.stderr)
        return 1

    if args.check:
        errors = validate(docs_root)
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print(f"ROADMAP check: {len(errors)} error(s)")
        return 1 if errors else 0

    data = compute(docs_root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_summary(data)
        print(f"  -> wrote {args.out}\n")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
