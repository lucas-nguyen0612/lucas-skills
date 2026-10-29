---
main_config: '{project-root}/_bmad/bmm/config.yaml'
failed_layers: '' # set at runtime: comma-separated list of layers that failed or returned empty
---

# Step 2: Review

## RULES

- YOU MUST ALWAYS SPEAK OUTPUT in your Agent communication style with the config `{communication_language}`
- The Blind Hunter subagent receives NO project context — diff only.
- The Edge Case Hunter subagent receives diff and project read access.
- The Acceptance Auditor subagent receives diff, spec, and context docs.
- The **Performance & Efficiency Hunter** subagent receives diff and project read access — it checks for N+1 queries, inefficient loops, oversized components, and unnecessary API calls.

## REVIEW LAYERS

This skill runs **FOUR parallel review layers** (vs three in bmad-code-review):

| Layer | Purpose | Input |
|---|---|---|
| **Blind Hunter** | Adversarial general review | Diff only (no context) |
| **Edge Case Hunter** | Exhaustive path/condition coverage | Diff + project access |
| **Acceptance Auditor** | Spec compliance check | Diff + spec + context |
| **Performance & Efficiency Hunter** | N+1, loops, component bloat, API calls | Diff + project access |

## INSTRUCTIONS

1. Launch parallel subagents. Each subagent gets NO conversation history from this session:

   - **Blind Hunter** -- Invoke the `bmad-review-adversarial-general` skill in a subagent. Pass `content` = `{diff_output}` only. No spec, no project access.

   - **Edge Case Hunter** -- Invoke the `bmad-review-edge-case-hunter` skill in a subagent. Pass `content` = `{diff_output}`. This subagent has read access to the project.

   - **Acceptance Auditor** (only if `{review_mode}` = `"full"`) -- A subagent that receives `{diff_output}`, the content of the file at `{spec_file}`, and any loaded context docs. Its prompt:
     > You are an Acceptance Auditor. Review this diff against the spec and context docs. Check for: violations of acceptance criteria, deviations from spec intent, missing implementation of specified behavior, contradictions between spec constraints and actual code. Output findings as a markdown list. Each finding: one-line title, which AC/constraint it violates, and evidence from the diff.

   - **Performance & Efficiency Hunter** -- Always run. Pass `{diff_output}` and grant project read access. Use the following prompt:
     > You are a Performance & Efficiency Hunter. Review this code diff for performance problems, N+1 queries, inefficient algorithms, oversized components, and unnecessary API calls.
     >
     > **Mandatory check categories:**
     >
     > 1. **N+1 Queries**: Find queries inside loops that should be batched. Look for patterns like: `for (const id of ids) { db.query('SELECT * FROM table WHERE id = $1', [id]) }` or `items.map(async item => { const data = await fetch(item.id); ... })` — these should use `WHERE id IN (...)` or a single batch query, or `Promise.all()` for independent parallel fetches.
     >
     > 2. **Inefficient loop patterns**: Find loops that do multiple passes over the same data that could be a single pass. Look for: `data.map(...).filter(...)` where map and filter could be combined, or `arr.filter(x => arr.map(...).includes(x))` which is O(n²), or loops that rebuild maps/indexes on every iteration.
     >
     > 3. **Missing bulk/batch operations**: If the code queries individual records then creates/updates them one-by-one in a loop, flag it. Prefer `bulkInsert`, `bulkUpdate`, `upsert` patterns.
     >
     > 4. **Oversized/unnecessary re-renders in React**: Look for components that are too large (>300 lines is a red flag), missing `useMemo`/`useCallback` on expensive computations/callbacks passed as props, or components that call async functions inside `useEffect` without proper cleanup or dependency arrays.
     >
     > 5. **Unnecessary API calls**: Look for: multiple sequential API calls that could be parallel (use `Promise.all`), API calls inside render paths (should be in `useEffect` or Server Component), redundant fetches (same data fetched multiple times in one page/flow), missing `AbortController` for cancelled requests.
     >
     > 6. **Inefficient data transformations**: Find large array operations (sort, filter, map) inside render paths that should be memoized. Check for: `data.sort()` called on every render, deep cloning objects unnecessarily (`JSON.parse(JSON.stringify(...))`), or repeated expensive computations without caching.
     >
     > 7. **Complex algorithm issues**: Flag O(n²) or worse algorithms that could be O(n) or O(n log n). Check for: nested loops over the same or related arrays, `Array.find` inside a loop, repeated string concatenation in a loop (use array.join instead).
     >
     > **Output format**: Markdown list. Each finding:
     > - `category` — one of: `n_plus_1`, `inefficient_loop`, `missing_bulk`, `oversized_component`, `unnecessary_api`, `inefficient_transform`, `complexity`
     > - `title` — one-line summary
     > - `detail` — full description with file:line reference
     > - `suggestion` — how to fix it

2. **Subagent failure handling**: If any subagent fails, times out, or returns empty results, append the layer name to `{failed_layers}` (comma-separated) and proceed with findings from the remaining layers.

3. If `{review_mode}` = `"no-spec"`, note to the user: "Acceptance Auditor skipped — no spec file provided."

4. **Fallback** (if subagents are not available): Generate prompt files in `{implementation_artifacts}` -- one per active reviewer:
   - `review-blind-hunter.md` (always)
   - `review-edge-case-hunter.md` (always)
   - `review-performance-hunter.md` (always — include the Performance & Efficiency Hunter checklist above)
   - `review-acceptance-auditor.md` (only if `{review_mode}` = `"full"`)

   HALT. Tell the user to run each prompt in a separate session and paste back findings. When findings are pasted, resume from this point and proceed to step 3.

5. Collect all findings from the completed layers.


## NEXT

Read fully and follow `./step-03-triage.md`