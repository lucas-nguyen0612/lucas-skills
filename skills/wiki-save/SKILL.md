---
name: wiki-save
description: >
  Quickly save a new piece of knowledge into lucas-wiki (an Obsidian vault made
  of several Lumina workspaces; its path is stored in ~/.claude/lucas-wiki.json,
  shared with /wiki-ask) from any directory. Use when the user types /wiki-save
  or says things like "lưu cái này vào wiki", "ghi lại kiến thức này", "save to
  wiki", "note lại vào lucas-wiki", "đưa vào wiki", pastes text/URL/file and
  wants it kept, or wants to keep something just learned in the conversation.
  The skill proposes a fitting workspace (or a new workspace if the topic does
  not fit), ALWAYS asks the user to confirm before writing, then writes
  Vietnamese wiki pages with bidirectional links. Not for books/PDFs of 50+
  pages (use /lumi-ingest inside the matching workspace).
argument-hint: "[text | URL | file path | 'from the conversation']"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - WebFetch
  - AskUserQuestion
---

# /wiki-save

You record knowledge for **lucas-wiki**. Goal: the user hands you a piece of knowledge, you file it in the right place, fast and with few questions — but you **always confirm the workspace before writing anything**.

**Language:** always reply to the user in Vietnamese (short, natural sentences, no internal tool details). Write all wiki pages in Vietnamese.

## Step 0: Vault path

The vault path lives in a config file shared with `/wiki-ask`: `~/.claude/lucas-wiki.json`, shaped like `{"vault_path": "<absolute path>"}`. Below, `<VAULT>` means that value.

1. Read it: `cat ~/.claude/lucas-wiki.json 2>/dev/null`.
2. If the file is missing, has no `vault_path`, or the directory no longer exists → **ask the user for the path** with AskUserQuestion (suggest `~/Documents/Lucas/lucas-wiki` if it exists; the user can type "Other"). Expand `~`, convert to an absolute path, check the directory exists and has at least one subdirectory containing both `README.md` and `wiki/`, then write `{"vault_path": "..."}` to the file (keep other keys if present). Once valid, never ask again.

Every subdirectory of `<VAULT>` that has `README.md` + `wiki/` is a workspace; ignore `.git` and `.obsidian`.

Never git-commit unless the user asks.

## Workflow

### 1. Get the content

Determine the input from the argument or the conversation:

- **Pasted text/notes** → use verbatim.
- **URL** → fetch with WebFetch; keep the URL as the source.
- **"from the conversation"** (or no argument but the user clearly just learned something) → summarize the knowledge worth keeping; drop temporary task details.
- **File path** → read the file. If it is a book/PDF of 50+ pages, stop and suggest copying it into the workspace's `raw/sources/` and running `/lumi-ingest` there.

If there is no content at all, ask the user what to save.

### 2. Choose the workspace — PROPOSE, THEN CONFIRM (mandatory)

1. List workspaces: `ls <VAULT>`, keeping directories with `README.md` and `wiki/`.
2. For each workspace, read the `## Project Purpose` section of `README.md` and `wiki/index.md` (if the index is empty, `ls wiki/concepts wiki/sources`) to learn what it covers.
3. Judge the topic of the new knowledge:
   - **Clear fit** with one workspace → propose that workspace.
   - **Partial fit / off-topic** → **do NOT force it into the closest workspace.** Propose creating a new workspace with a suggested name (lowercase, hyphenated, no diacritics, e.g. `cooking`, `design`).
4. Ask with AskUserQuestion, giving a short reason for the proposal. Options:
   - Save to `<proposed workspace>` (first, marked "Đề xuất").
   - Create new workspace `<suggested name>` (put first if it fits better).
   - Pick another workspace (list up to 2 closest remaining; the user may type "Other").
5. **Write no file before the user has chosen.**

### 3. Create a new workspace (only if the user chose it)

Scaffold it like the existing workspaces, using `trading` (or another intact workspace) as the template:

```bash
V=<VAULT>; NEW="$V/<name>"; SRC="$V/trading"
mkdir -p "$NEW" && cd "$NEW"
cp -R "$SRC/.agents" "$SRC/.claude" "$SRC/_lumina" .
cp "$SRC/.gitignore" "$SRC/.env.example" . 2>/dev/null
rm -rf _lumina/_state/* && mkdir -p _lumina/_state
node _lumina/scripts/wiki.mjs init
mkdir -p raw/notes raw/sources raw/assets raw/tmp raw/download raw/discovered   # init does not create raw/
```

Then:

- `README.md`: copy from `$SRC/README.md`, change the title `# trading` to `# <name>` and `## Project Purpose` to one sentence describing the new workspace's topic. Keep the `<!-- lumina:schema -->` region untouched.
- `CLAUDE.md`: copy from `$SRC/CLAUDE.md`, change the workspace name.
- `_lumina/config/lumina.config.yaml`: change `project_name` and `created_at` (today).
- `_lumina/manifest.json` is a copy from the template workspace; leave it alone (never hand-edit).
- Verify with `ls` that the skeleton is complete (`raw/*`, `wiki/{index.md,log.md,concepts,sources,people,summary,outputs}`); if `init` errors, read the error and fix it — do not ignore it silently.

### 4. Check for duplicates

In the target workspace, read `wiki/index.md` and `ls wiki/concepts wiki/sources`. Look for an existing page covering the same idea (compare slugs and both Vietnamese/English titles).

- A similar page exists → **extend that page** (add the new idea, bump `updated`, add the source); do not create a duplicate.
- None → create a new page in step 6.

### 5. Save the raw original to `raw/notes/`

Write `raw/notes/YYYY-MM-DD-<slug>.md` (add new files only; **never modify or delete existing files in `raw/`**). Content: the original text or the conversation summary, with a first line `Nguồn: <URL | "cuộc trò chuyện" | file path>` and the save date.

Slug: run `node _lumina/scripts/wiki.mjs slug "<title>"` inside the workspace (if the slug already exists, add a short suffix).

### 6. Write the wiki page (Vietnamese)

**Before writing**, read the target workspace's `_lumina/schema/page-templates.md` for the exact frontmatter and sections.

Pick the page type:

- **Knowledge/idea/technique** (a single concept) → `wiki/concepts/<slug>.md`.
- **A specific article, video, or document** → `wiki/sources/<slug>.md` (summary, key claims), plus stub/concept pages for important concepts it mentions.
- A notable person mentioned → `wiki/people/<slug>.md` (only when genuinely useful; avoid padding).

Writing rules:

- Slug: lowercase, hyphenated, no diacritics. On first use put the original term in parentheses.
- Set `confidence: unverified` or `medium` when content is unverified; link the source clearly (URL in Notes, or cite `raw/notes/...`).
- **Concept**: `## Definition`, `## Variants`, `## Key sources`, `## Related concepts`, `## Notes` per the template. **Source**: `## Summary`, `## Key claims`, `## Related concepts`, ... per the template.
- Preserve sections marked `<!-- user-edited -->`.
- **Bidirectional links are mandatory** (Obsidian `[[slug]]`): if page A links to B, write the back-link in B in the same operation (see the table in the workspace README). Only link to pages that actually exist.
- Record only what the source content says; do not invent.

### 7. Update bookkeeping

Inside the workspace directory:

- **`wiki/index.md`**: add an entry for every new page (follow the file's existing format; if empty, one line per page `- [[slug]] — short description`, grouped by page type).
- **`wiki/log.md`** (append-only): `node _lumina/scripts/wiki.mjs log wiki-save "<short detail: which pages were added/updated>"`. If the command fails, append by hand `## [YYYY-MM-DD] wiki-save | <detail>`.
- Never hand-edit `wiki/graph/`. For graph edges, use `wiki.mjs add-edge`.
- Run `node _lumina/scripts/lint.mjs` (if present) and fix broken links / missing back-links in the pages you just created.

### 8. Report back

Reply briefly in Vietnamese: which workspace it went to, which pages are **new** and which were **updated** (with paths), and anything the user should review. Do not list internal technical details.

## Constraints

- Always confirm the workspace (and any new-workspace creation) before writing.
- In `raw/`, only add new files under `raw/notes/`; never modify or delete existing ones.
- Never hand-edit `wiki/graph/`. `log.md` is append-only.
- Every new page must be in `index.md` and have bidirectional links.
- Scope: save only the knowledge the user gave; do not expand into other work.
