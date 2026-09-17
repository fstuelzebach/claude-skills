---
name: session-summary
description: Write a Notion review page documenting everything changed in the current session. It explains each change, why it was made and what it means for the user, in plain English with the technical terms in bold, and gives GitHub commit, file and raw links for cross-checking in the browser, a detailed section on open points, and a glossary. Use when the user says "session summary", "review page", "document this session in Notion", or invokes /session-summary.
argument-hint: "[subject, e.g. metis] — optional; the page title defaults to <subject>_review_<YYYYMMDD>"
---

# Session summary → Notion review page

Produces one Notion page that lets the user **understand, verify and look up** what this
session did, weeks later and without the chat. It is written for a reader who is not
a developer: every technical term (*Fachterminus*) appears in **bold** with a plain-English
explanation next to it, and ends up in the glossary.

## 1. Resolve the destination
- **Title:** `<subject>_review_<YYYYMMDD>` (Europe/Berlin date). `<subject>` is the
  argument, else the repo the session mainly changed (e.g. `metis`, `oc` for olymp_capital).
  A user-given title wins.
- **Parent:** the project's Notion Tasks database, the same place `push-tasks` writes to.
  - Database id: env `NOTION_TASKS_DB_ID`. Fetch it to get its data source (`collection://…`).
  - Class page: `NOTION_CLASS_PAGE_ID` in `.claude/project.env`.

  If either is missing, create the page with `creation_mode: "draft"` and say so.
- **Properties:**
  - `title`
  - `Class` = the class page
  - `Links` = the main repo URL
  - `task_key` = `review:<title>`. This keeps the page out of `session-close`'s Notion intake (which only takes pages with an empty `task_key`), and `notion_push_tasks.py` skips `review:` keys when listing orphans.
  - icon `🔎`
- **No duplicates:** search Notion for the title first. If the page exists, ask whether to update it or add a suffix (`_2`).

## 2. Collect the facts (from the session only, never invented)
- **Commits:** for every repo touched this session, get the commits with their full hashes
  (`git -C <repo> log --format='%H %h %s' <start>..HEAD`) and the remote
  (`git remote get-url origin` → `https://github.com/<owner>/<repo>`).
- **Push status:** confirm the commits are pushed (`git status -sb`). If they aren't, say so on
  the page, because the GitHub links won't resolve yet.
- **Changes outside git:** Claude memory, user-level config (MCP registrations,
  settings), files moved or renamed on disk, Notion pages created or edited, services
  restarted.
- **Decisions:** what was decided, by whom (user vs. Claude's proposal), and the reason.
- **Problems hit:** symptom → diagnosis → fix → how it was verified.
- **Open points:** anything left undecided, assumed, or known broken.
- **Current state:** tests, data counts, what is running. Quote the real numbers you saw.
- **Secrets:** never write tokens, passwords, API keys or push topics onto the page. Name the
  credential key instead.

## 3. Page structure
Mirror this order; drop a section only if it would be empty.

1. **Intro quote block:** what this page is, which session (date and time of day), the status at writing.
2. **§0 How to cross-check this page:**
   - **Side by side:** open this page and the GitHub diff next to each other.
   - **claude.ai:** paste a commit or *raw* link plus the matching section, with a
     ready-to-copy verification prompt.
   - **Raw links:** `https://raw.githubusercontent.com/<owner>/<repo>/main/<path>` for the key
     files. Note that private repos need claude.ai's GitHub connector, or copy-paste instead.
   - **Repo links:** the repo and its `commits/main` page.
   - **Related Notion pages:** as `<mention-page>` links.
   - **Commit map:** a table of commit (linked, short hash) | what it did | section, newest first.
3. **§1 Orientation:** what the project is, in a few lines, and a "where things live" table.
4. **One section per change** (group related commits). Each section has:
   - **Commit:** the link. **Files:** `blob/main/<path>` links.
   - **What changed**, in plain English.
   - **Why:** the reason or decision, and alternatives if they were weighed.
   - **Implication for you:** what the user must do or know differently now.
5. **Changes outside the repo.**
6. **The open points, in detail:** one `###` per point, each with:
   - what it is;
   - the options with pros and cons;
   - **what each option changes**;
   - what happens until it's decided.

   Then a short numbered list of "small to-dos (no decision needed)".
7. **Glossary:** a two-column table (Term | Plain English) covering every bolded term.

## 4. Writing rules
- English, short paragraphs, bullets over prose. Every term in **bold** on first use,
  explained in the same sentence (German gloss in *italics* where it helps).
- Link every commit and file; use full hashes in URLs and short hashes as link text.
- Say what was **verified** and how (tests, counts, re-reads). Mark assumptions as
  assumptions.
- Notion markdown: tables as `<table header-row="true"><tr><td>…</td></tr></table>`,
  pages as `<mention-page url="…"/>`, and tabs for nested lists. Avoid bare `FILE.md`
  words outside backticks, because Notion auto-links them to `http://FILE.md`.

## 5. Create, verify, report
1. `notion-create-pages` with `allow_async: false`.
2. `notion-fetch` the new page. Check it isn't truncated and that tables and links rendered.
3. Report to the user:
   - the page link;
   - where the page sits;
   - anything to watch (unpushed commits, private-repo links, a stale related page).

   Don't repeat the page content in chat.
