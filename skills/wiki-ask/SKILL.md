---
name: wiki-ask
description: >
  Look up and answer questions from the knowledge saved in lucas-wiki (an
  Obsidian vault made of several Lumina workspaces). Use when the user types
  /wiki-ask or asks things like "trong wiki của tôi có gì về X", "tra lucas-wiki
  giúp tôi...", "tôi đã ghi gì về...", "wiki nói gì về...", "tìm trong wiki".
  On first use the skill asks for the vault path and stores it in
  ~/.claude/lucas-wiki.json (shared with /wiki-save); afterwards it reuses it.
  Read-only: never modifies the wiki. Answers only from wiki content, with page
  citations.
argument-hint: "<question> | --reset (change vault path)"
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

# /wiki-ask

You look up knowledge for **lucas-wiki**. Answer the user's question **only from wiki content**, with citations. This skill is **read-only** with respect to the wiki (the single exception: writing the config file in step 1).

**Language:** always reply to the user in Vietnamese (short, natural sentences, no internal tool details).

## 1. Get the vault path

Config file shared with `/wiki-save`: `~/.claude/lucas-wiki.json`

```json
{"vault_path": "/Users/lucas/Documents/Lucas/lucas-wiki"}
```

1. Read it if present: `cat ~/.claude/lucas-wiki.json 2>/dev/null`.
2. **Ask the user for the path** when: the file is missing, has no `vault_path`, the directory no longer exists, or the user passes `--reset` / says "đổi đường dẫn wiki".
   - Ask with AskUserQuestion (suggest `~/Documents/Lucas/lucas-wiki` if that directory exists; the user can type "Other" for another path).
   - Expand `~` and convert to an absolute path.
   - Validate: the directory exists and has at least one subdirectory containing both `README.md` and `wiki/`. If invalid, say why and ask again.
   - Save: write `{"vault_path": "<absolute path>"}` to `~/.claude/lucas-wiki.json` (keep other keys if the file exists), then briefly confirm "đã lưu đường dẫn".
3. If valid, use it directly and **do not ask again**.

If the user passed only `--reset` with no question, stop after saving the new path.
If there is no question, ask the user what they want to look up.

## 2. Guess the relevant workspaces

1. List workspaces: direct subdirectories of the vault containing `README.md` and `wiki/` (ignore `.git`, `.obsidian`).
2. For each workspace, read the `## Project Purpose` section of `README.md` and `wiki/index.md` (if the index is empty, `ls wiki/concepts wiki/sources`) to learn what it covers.
3. Pick the 1–2 workspaces most likely to match the question. If the question spans several topics, pick all relevant workspaces and synthesize.

Do not ask the user "which workspace" — lookup is read-only, so there is no risk.

## 3. Search and read

1. In the chosen workspaces: read `wiki/index.md`, then `grep -ril` keywords (Vietnamese and English, synonyms, abbreviations) across `wiki/concepts`, `wiki/sources`, `wiki/summary`, `wiki/readings`, `wiki/topics`, `wiki/people`, `wiki/reflections`.
2. Read the best-matching pages. Follow `[[slug]]` links **one hop** for extra context when needed.
3. If nothing is found, or too little: **widen the search to the entire vault** (every workspace, including `raw/notes`) before concluding the wiki has nothing. Guessing the workspace is only to search faster; it must never make you miss knowledge in another workspace.
4. Do not read raw `wiki/graph/` jsonl unless you need relations between pages.

## 4. Answer

- Vietnamese, straight to the answer, concise.
- **Use only wiki content.** Do not fill gaps with your own general knowledge. For anything the wiki does not cover, say plainly "wiki chưa có phần này".
- Cite a source for each main point as `workspace/wiki/type/slug.md` (e.g. `Technical Knownlege/wiki/concepts/caching.md`).
- If pages contradict each other or have `confidence: low/unverified`, say so.
- If drawing from several workspaces, state which workspace each point comes from.
- If the wiki has nothing or very little: say so directly, mention whatever was found (if any), and suggest `/wiki-save` to record this knowledge.

## Constraints

- Read-only: never create/modify/delete files in the vault. The only file you may write is `~/.claude/lucas-wiki.json`.
- Never invent content or cite pages that do not exist.
- Do not expand scope: answer only the question asked.
