---
name: review-artifact
description: Turn a PR, branch diff, ADR or architecture change into one self-contained HTML review artifact — visual data-model schema, animated change flow, highlighted additions/deletions, changed folder tree, ranked review findings. Use whenever the user asks to review, overview or "nắm tổng quan" a pull request, branch, migration set or architecture document and wants something visual, or says "tạo file html", "visual schema", "sơ đồ thay đổi", "review kiến trúc", "visual review". Review-only: it never creates issues or tickets.
---

# Review Artifact

One HTML file a reviewer can scan in three minutes: what changed, where, what it means, what to
challenge. Built for the human view — diagrams and colour before prose.

## Scope

Use for: a teammate's PR, your own PR before merge, a branch diff, a set of migrations, an ADR
series, an epic's architecture delta.

Do not use for: code review findings on their own (that is `/code-review`), user-facing product
docs (that is `docs/user-guide/`), or anything that must live in the repo as documentation. The
artifact is a throwaway review aid, not a project document — no frontmatter rules, no `docs/` tier.

**Never create a GitHub issue or a board task for a review.** Reviews are review-only. Create one
only if the review uncovers work that must be scheduled, and only after an explicit yes.

## Output

`~/.claude/review-artifacts/<repo>/<kind>-<n>-<slug>.html` — e.g.
`~/.claude/review-artifacts/capigo/pr-1462-inbound-receipt-waybill.html`.
Self-contained: no network fonts, no CDN, no external assets. It must open from `file://`.

Light theme is the default; the header carries a sun/moon toggle that switches to dark and remembers
the choice. Keep both themes working — a new component takes tokens, never a literal colour.

## Workflow

### 1. Establish the real diff

```bash
gh pr view <n> --json number,title,state,author,baseRefName,headRefName,additions,deletions,changedFiles,body,updatedAt
gh pr diff <n> --name-only
git fetch origin <base> --quiet
git merge-base HEAD origin/<base>   # diff against the merge-base, not the branch tip
git log --oneline --no-merges origin/<base>..HEAD
```

Verify what the PR body claims against what the diff shows. A body that names error codes, event
versions or endpoints is a common source of drift; when body and code disagree, the code wins and
the disagreement becomes a finding.

### 2. Separate deliberate work from carried work

A PR diff often contains more than its title says. Check each commit and each merged-in PR:

```bash
gh pr view <other> --json number,title,baseRefName,mergedAt   # base = this branch ⇒ stacked
```

If the branch carries other workstreams, say so at the top of the artifact. Merging it ships them
all at once, which is the single most important thing a reviewer can miss.

### 3. Read the change, not the summary

Read the migrations, schemas, route handlers and event builders themselves. For each surface record
path and `path:line` where the line is the point. Facts you cannot tie to a file you read do not go
in the artifact.

For a schema change, collect: tables added/changed/dropped, columns with type and nullability,
constraints and partial indexes, triggers, functions created/replaced/dropped, and grants or RLS.
Note a function redefined more than once in the same change — only the last definition is live, and
a reviewer reading the first will judge dead code.

### 4. Build

```bash
cp ~/.claude/skills/review-artifact/assets/template.html <output>
python3 -I ~/.claude/skills/review-artifact/scripts/pr_tree.py \
  --repo <repo> --base <merge-base> --head HEAD -o /tmp/tree.json
```

Replace every `REGION:<name>` block. Keep the CSS and JS; extend them rather than rewriting.
Inject the tree JSON at `/*TREE_JSON*/`.

Sections, in order — keep all seven or delete one deliberately, never silently reorder:

| Region | Job |
|---|---|
| hero | what changed in one sentence, counts, branch, links |
| stack | what the diff *actually* contains when it carries more than one workstream |
| logic | **BA-style flowchart** of the rule the change introduces: start terminator, decision diamonds, "không" branches into the refusal terminal, happy path in one colour |
| flow | how data moves between systems — the animated pipeline |
| schema | a real ERD: table boxes with columns, cardinality lines, added columns glowing; functions listed beside, not described |
| contract | events, versions, error codes, endpoints |
| tree | area bars + collapsible file tree with per-file `+/-` |
| review | findings ranked CHẶN / NÊN XEM / GHI NHẬN |

A change that adds a rule needs both diagrams: the **flowchart** answers "what does this rule do to
the document", the **pipeline** answers "where does the data travel". One without the other leaves
the reviewer guessing.

Write the artifact in the user's chat language; keep identifiers, paths and code exact.

### Density: a diagram, not a document — and not a wireframe either

- **Body text never below 14.5px.** Section labels, table types, badges, tree rows, legends: all at
  or above it. A 12px label is a defect, not a compact design.
- **Carry the rule inside the diagram.** Every decision node names the condition, every "không"
  branch names the error code it produces, every process node names the write it performs. That is
  the text; do not move it into prose below.
- **Prose is for what the diagram cannot show:** why the rule exists, what it changes for a person,
  what to challenge. One line per card, two at most.
- **Never leave the reader unable to answer "how does this touch the document".** If the wiring
  between two workstreams is not visible in a diagram, the diagram is incomplete, not the text.
- When the content overflows, widen or add a diagram step before adding a paragraph; shrink type
  never.

### 5. Verify before reporting

Never report an artifact you have not rendered. Check for console errors and look at every section:

```bash
node -e "import('playwright')..."   # or the project's playwright
```

Screenshot each section at 1440×1000, open it, and fix overflow, clipped code, flex-in-flex
breakage and unreadable contrast. A section that scrolls sideways on a 1440 viewport is a bug.

### 6. Report

Three lines: path, what it covers, and the finding that needs a decision. If a finding is blocking,
state it in chat too — the artifact is for reading, not for discovering.

## Content rules

- **Colour means one thing.** added = emerald, modified = amber, deleted = rose, carried-in /
  secondary direction = violet. Never reuse a colour for a different meaning in the same artifact.
- **Show removal.** A dropped table, column, function or error code gets the same visual weight as
  an addition and is struck through, not omitted.
- **Counts over adjectives.** `+14,286 / −2,764`, `113 of 258 files are JSON fixtures` beats
  "large change".
- **Rank findings.** Blocking means it changes what ships or who it affects. Put the reason
  underneath, one or two lines, with the path that proves it.
- **No walls of prose.** A paragraph longer than four lines belongs in chat, not the artifact.
- **Say what is not shown.** Fixtures, generated types and lockfiles get a count and a sentence;
  do not list them file by file.

## Animation rules

Animation exists to show cause and effect, not to decorate.

- **One moving diagram minimum.** Data flow with marching dashes and travelling packets; stages
  highlight in sequence on reveal.
- **A replayable diff.** A button that re-runs the `.added` / `.newtbl` / `.dropped` entrance so the
  reviewer can see what appeared last. Stagger by ~90ms.
- Counters animate once, on reveal, and stop.
- Everything respects `prefers-reduced-motion` — already handled in the template; do not remove it.
- Nothing animates on scroll in a way that moves the reader's target under the cursor.

`references/design-system.md` holds the tokens, component inventory and anti-patterns.

## Adapting to a non-PR review

For an architecture document or ADR series: same shell, different sections — decisions made,
alternatives rejected, data-model delta, migration path, blast radius. The `flow` region shows the
target architecture instead of a before/after pipeline. Everything else holds.
