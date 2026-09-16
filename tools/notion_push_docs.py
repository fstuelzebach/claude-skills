#!/usr/bin/env python
"""
tools/notion_push_docs.py

Push local markdown docs (ROADMAPs, DASHBOARD, CLAUDE.md, DOMAIN_GLOSSARY,
METRICS, DEPLOYMENT, ...) into Notion as a GENERATED, read-only mirror.

Idempotent: each run WIPES the target page and rewrites it from the current file
on disk. Truth stays in git; Notion is a derived reading surface for mobile /
Claude.ai on a private-repo project.

Config : conf/notion_mirror.toml   (path -> Notion page_id mapping)
Auth   : NOTION_TOKEN env var (export NOTION_TOKEN=secret_xxx)

Conversion:
  headings / paragraphs / bullets / numbered / quotes / dividers / fenced code
  render as native Notion blocks. Markdown TABLES render as monospace code blocks
  (reliable; avoids fragile Notion-table generation). Long text is split under the
  2000-char rich_text limit; blocks are appended in batches of 100.

Usage:
    python tools/notion_push_docs.py                       # sync every doc in config
    python tools/notion_push_docs.py --only dashboard      # sync a subset (by key)
    python tools/notion_push_docs.py --dry-run             # print block counts only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

try:
    from notion_client import Client
    from notion_client.errors import APIResponseError, RequestTimeoutError
except ModuleNotFoundError:  # pragma: no cover
    sys.exit("notion-client not installed. Run: pip install notion-client")

# --------------------------------------------------------------------------- #
# Paths / limits
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "conf" / "notion_mirror.toml"
CACHE_PATH = PROJECT_ROOT / "data" / "notion_push_docs_cache.json"

MAX_TEXT = 1900            # < Notion's 2000-char rich_text limit, with headroom
MAX_CODE_CHARS = 1800      # split code/table blocks longer than this
MAX_BLOCKS_PER_CALL = 100  # Notion append cap
MAX_RICH_TEXT_ITEMS = 100  # Notion's hard per-block rich_text array-length cap
REQ_PACING_S = 0.34        # ~3 requests/sec — used only where calls must stay serial
DELETE_WORKERS = 5         # concurrent block-delete workers during a page wipe


# --------------------------------------------------------------------------- #
# Change-detection cache (skip wiping pages whose source content is unchanged)
# --------------------------------------------------------------------------- #
def _load_cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")

# --------------------------------------------------------------------------- #
# Inline + rich-text helpers
# --------------------------------------------------------------------------- #
_INLINE_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+?`)")


def _split_text(s: str) -> list[str]:
    """Split a string into <= MAX_TEXT chunks."""
    if s == "":
        return [""]
    return [s[i:i + MAX_TEXT] for i in range(0, len(s), MAX_TEXT)]


def parse_inline(text: str) -> list[dict]:
    """Markdown line -> Notion rich_text objects. Handles **bold** and `code`."""
    if not text:
        return []
    out: list[dict] = []
    for token in _INLINE_RE.split(text):
        if not token:
            continue
        if token.startswith("**") and token.endswith("**"):
            content, ann = token[2:-2], {"bold": True}
        elif token.startswith("`") and token.endswith("`"):
            content, ann = token[1:-1], {"code": True}
        else:
            content, ann = token, None
        for chunk in _split_text(content):
            rt = {"type": "text", "text": {"content": chunk}}
            if ann:
                rt["annotations"] = ann
            out.append(rt)
    return out


def _rich(text: str) -> list[dict]:
    return [{"type": "text", "text": {"content": c}} for c in _split_text(text)]


# --------------------------------------------------------------------------- #
# Block builders
# --------------------------------------------------------------------------- #
def _para(text: str) -> dict:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": parse_inline(text)}}


def _heading(level: int, text: str) -> dict:
    key = f"heading_{min(level, 3)}"
    return {"object": "block", "type": key, key: {"rich_text": parse_inline(text)}}


def _bullet(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": parse_inline(text)}}


def _numbered(text: str) -> dict:
    return {"object": "block", "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": parse_inline(text)}}


def _quote(text: str) -> dict:
    return {"object": "block", "type": "quote",
            "quote": {"rich_text": parse_inline(text)}}


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _split_rich_text_block(block: dict) -> list[dict]:
    """A single markdown line with enough inline-formatting boundaries (code
    spans, bold runs) can produce a rich_text array longer than Notion's
    hard 100-item-per-block cap, even though each chunk is well under
    _split_text()'s 1900-char limit (that guards text length, not item
    count). Rather than crash mid-sync leaving a page half-wiped, split
    into consecutive same-type blocks — a few extra bullets/paragraphs
    instead of lost content.
    """
    block_type = block["type"]
    rich_text = block[block_type]["rich_text"]
    if len(rich_text) <= MAX_RICH_TEXT_ITEMS:
        return [block]
    chunks = []
    for i in range(0, len(rich_text), MAX_RICH_TEXT_ITEMS):
        piece = dict(block[block_type])
        piece["rich_text"] = rich_text[i:i + MAX_RICH_TEXT_ITEMS]
        chunks.append({"object": "block", "type": block_type, block_type: piece})
    return chunks


_NOTION_LANGS = {
    "python", "bash", "json", "yaml", "toml", "sql", "javascript",
    "typescript", "powershell", "markdown", "plain text", "diff", "html",
}
_LANG_ALIASES = {
    "sh": "bash", "shell": "bash", "console": "bash",
    "ps": "powershell", "ps1": "powershell",
    "js": "javascript", "ts": "typescript", "md": "markdown", "": "plain text",
}


def _notion_lang(lang: str) -> str:
    lang = (lang or "").strip().lower()
    lang = _LANG_ALIASES.get(lang, lang)
    return lang if lang in _NOTION_LANGS else "plain text"


def _code(text: str, language: str = "plain text") -> list[dict]:
    """Emit one or more code blocks, each <= MAX_CODE_CHARS."""
    text = text.rstrip("\n")
    lang = _notion_lang(language)
    if text == "":
        return [{"object": "block", "type": "code",
                 "code": {"rich_text": [], "language": lang}}]
    blocks: list[dict] = []
    for i in range(0, len(text), MAX_CODE_CHARS):
        chunk = text[i:i + MAX_CODE_CHARS]
        blocks.append({"object": "block", "type": "code",
                       "code": {"rich_text": [{"type": "text",
                                               "text": {"content": chunk}}],
                                "language": lang}})
    return blocks


# --------------------------------------------------------------------------- #
# Markdown -> blocks
# --------------------------------------------------------------------------- #
_H_RE = re.compile(r"^(#{1,6})\s+(.*)")
_BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)")
_NUM_RE = re.compile(r"^\s*\d+[.)]\s+(.*)")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->\n?", re.DOTALL)


def _strip_html_comments(md: str) -> str:
    """Drop <!-- ... --> blocks (e.g. PROJECT_STATUS.md's generation-metadata header)
    before conversion — they're notes for git readers, not Notion content."""
    return _HTML_COMMENT_RE.sub("", md)


def md_to_blocks(md: str) -> list[dict]:
    md = _strip_html_comments(md)
    lines = md.splitlines()
    n = len(lines)
    blocks: list[dict] = []
    para_buf: list[str] = []
    i = 0

    def flush_para() -> None:
        nonlocal para_buf
        if para_buf:
            joined = " ".join(l.strip() for l in para_buf).strip()
            if joined:
                blocks.extend(_split_rich_text_block(_para(joined)))
            para_buf = []

    # Leading YAML front-matter (--- ... ---) -> code block.
    if n and lines[0].strip() == "---":
        j = 1
        while j < n and lines[j].strip() != "---":
            j += 1
        if j < n:
            blocks.extend(_code("\n".join(lines[1:j]), "yaml"))
            i = j + 1

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Fenced code block
        if stripped.startswith("```"):
            flush_para()
            lang = stripped[3:].strip()
            buf: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # consume closing fence
            blocks.extend(_code("\n".join(buf), lang))
            continue

        # Markdown table -> code block
        if stripped.startswith("|") and "|" in stripped[1:]:
            flush_para()
            buf = []
            while i < n and lines[i].strip().startswith("|"):
                buf.append(lines[i].rstrip())
                i += 1
            blocks.extend(_code("\n".join(buf), "plain text"))
            continue

        # Blank line = paragraph break
        if stripped == "":
            flush_para()
            i += 1
            continue

        # Divider
        if stripped in ("---", "***", "___"):
            flush_para()
            blocks.append(_divider())
            i += 1
            continue

        # Heading
        m = _H_RE.match(line)
        if m:
            flush_para()
            blocks.extend(_split_rich_text_block(_heading(len(m.group(1)), m.group(2).strip())))
            i += 1
            continue

        # Bullet
        m = _BULLET_RE.match(line)
        if m:
            flush_para()
            blocks.extend(_split_rich_text_block(_bullet(m.group(1).strip())))
            i += 1
            continue

        # Numbered
        m = _NUM_RE.match(line)
        if m:
            flush_para()
            blocks.extend(_split_rich_text_block(_numbered(m.group(1).strip())))
            i += 1
            continue

        # Quote
        if stripped.startswith(">"):
            flush_para()
            blocks.extend(_split_rich_text_block(_quote(stripped.lstrip("> ").rstrip())))
            i += 1
            continue

        # Default: accumulate into a paragraph
        para_buf.append(line)
        i += 1

    flush_para()
    return blocks


# --------------------------------------------------------------------------- #
# Header + git
# --------------------------------------------------------------------------- #
def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def _header_blocks(source: Path, commit: str) -> list[dict]:
    ts = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d %H:%M %Z")
    txt = (f"Generated mirror — do not edit here. Source: {source.name} · "
           f"synced {ts} · commit {commit}. Truth lives in git; any edit here "
           f"is overwritten on the next session-close.")
    return [{"object": "block", "type": "callout",
             "callout": {"rich_text": _rich(txt),
                         "icon": {"type": "emoji", "emoji": "🔄"}}}]


# --------------------------------------------------------------------------- #
# Notion I/O
# --------------------------------------------------------------------------- #
def _with_retry(fn, *args, **kwargs):
    for attempt in range(6):
        try:
            return fn(*args, **kwargs)
        except RequestTimeoutError:
            # Transient network/API timeout — always worth a retry.
            time.sleep(1.5 * (attempt + 1))
            continue
        except APIResponseError as e:
            status = getattr(e, "status", None)
            if getattr(e, "code", "") == "rate_limited" or status == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise RuntimeError("Notion API: exceeded retry budget")


def wipe_page(notion: Client, page_id: str, label: str = "") -> int:
    """Delete every direct child block of page_id. Deletes are independent of
    each other (order doesn't matter, unlike appends), so they run concurrently
    through a small worker pool instead of one-at-a-time — the 429 backoff in
    _with_retry is what actually keeps us under Notion's rate limit; the old
    fixed 0.34s serial sleep was more conservative than necessary."""
    ids: list[str] = []
    cursor = None
    while True:
        resp = _with_retry(notion.blocks.children.list,
                           block_id=page_id, start_cursor=cursor, page_size=100)
        ids.extend(b["id"] for b in resp["results"])
        if not resp.get("has_more"):
            break
        cursor = resp["next_cursor"]

    total = len(ids)
    if total == 0:
        return 0

    counter = {"done": 0}
    lock = threading.Lock()

    def _delete_one(bid: str) -> None:
        _delete_if_present(notion, bid)
        with lock:
            counter["done"] += 1
            print(f"\r    {label} wiping {counter['done']}/{total}",
                  end="", flush=True)

    with ThreadPoolExecutor(max_workers=DELETE_WORKERS) as ex:
        for f in as_completed([ex.submit(_delete_one, bid) for bid in ids]):
            f.result()  # surface any exception instead of swallowing it

    print()  # move off the \r progress line
    return total


def _delete_if_present(notion: Client, block_id: str) -> None:
    """Delete (archive) a block. Already-archived blocks are treated as
    already-deleted rather than a hard failure — can happen if a previous
    sync was interrupted mid-wipe, leaving a block archived but still
    returned by a subsequent children.list call."""
    try:
        _with_retry(notion.blocks.delete, block_id=block_id)
    except APIResponseError as e:
        if getattr(e, "code", "") == "validation_error" and "archived" in str(e).lower():
            return
        raise


def patch_header(notion: Client, page_id: str, header_block: dict) -> bool:
    """Update just the first block (the generated-header callout) in place,
    without touching the rest of the page. Used when the source content is
    unchanged since the last sync but the commit/timestamp still needs
    refreshing. Returns False if the page has no blocks yet (never synced),
    so the caller can fall back to a full wipe+append."""
    resp = _with_retry(notion.blocks.children.list, block_id=page_id, page_size=1)
    results = resp.get("results", [])
    if not results:
        return False
    _with_retry(notion.blocks.update, block_id=results[0]["id"],
                callout=header_block["callout"])
    return True


def append_blocks(notion: Client, page_id: str, blocks: list[dict]) -> None:
    for k in range(0, len(blocks), MAX_BLOCKS_PER_CALL):
        _with_retry(notion.blocks.children.append,
                    block_id=page_id, children=blocks[k:k + MAX_BLOCKS_PER_CALL])
        time.sleep(REQ_PACING_S)


def _set_title(notion: Client, page_id: str, title: str) -> None:
    try:
        _with_retry(notion.pages.update, page_id=page_id,
                    properties={"title": {"title": [{"type": "text",
                                                     "text": {"content": title}}]}})
    except APIResponseError:
        pass  # title is cosmetic; never fail the sync over it


# --------------------------------------------------------------------------- #
# Per-doc sync
# --------------------------------------------------------------------------- #
def sync_doc(notion, doc: dict, commit: str, dry_run: bool, cache: dict) -> None:
    path = PROJECT_ROOT / doc["path"]
    key = doc.get("key", doc["path"])
    if not path.exists():
        print(f"  SKIP  {doc['path']} (not found on disk)")
        return
    md = path.read_text(encoding="utf-8")
    content_hash = hashlib.sha256(md.encode("utf-8")).hexdigest()
    header = _header_blocks(path, commit)[0]
    blocks = [header] + md_to_blocks(md)
    print(f"  {key:<22} {doc['path']:<48} -> {len(blocks):>4} blocks",
          flush=True)
    if dry_run:
        return

    if doc.get("title"):
        _set_title(notion, doc["page_id"], doc["title"])

    if cache.get(key) == content_hash:
        if patch_header(notion, doc["page_id"], header):
            print("    unchanged since last sync — header refreshed only")
            return
        # page had no blocks yet (first-ever sync of this doc) — fall through

    wiped = wipe_page(notion, doc["page_id"], label=key)
    append_blocks(notion, doc["page_id"], blocks)
    cache[key] = content_hash
    print(f"    (wiped {wiped})  OK")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Mirror repo markdown docs to Notion.")
    ap.add_argument("--only", nargs="*", metavar="KEY",
                    help="sync only these doc keys (from conf/notion_mirror.toml)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print per-doc block counts; touch nothing")
    args = ap.parse_args()

    if not CONFIG_PATH.exists():
        sys.exit(f"Missing config: {CONFIG_PATH}")
    cfg = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    docs = cfg.get("docs", [])
    if args.only:
        docs = [d for d in docs if d.get("key") in args.only]
        if not docs:
            sys.exit(f"No docs matched --only {args.only}")

    commit = _git_commit()
    notion = None
    if not args.dry_run:
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            sys.exit("NOTION_TOKEN not set — export NOTION_TOKEN=secret_xxx")
        notion = Client(auth=token)

    cache = {} if args.dry_run else _load_cache()

    print(f"Notion doc mirror · commit {commit} · {len(docs)} docs"
          f"{' · DRY RUN' if args.dry_run else ''}", flush=True)
    for doc in docs:
        if "path" not in doc or (not args.dry_run and not doc.get("page_id")):
            print(f"  SKIP  malformed/unconfigured entry: {doc.get('key', doc)}")
            continue
        sync_doc(notion, doc, commit, args.dry_run, cache)

    if not args.dry_run:
        _save_cache(cache)
    print("Done.")


if __name__ == "__main__":
    main()
