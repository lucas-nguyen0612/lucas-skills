---
name: spec-quality-gate
description: Validate a bmad-loop story spec (_bmad-output/implementation-artifacts/spec-<story-key>.md) against the quality bars that predict whether an unattended dev/review session can drive it without escalating, hanging, blowing its token budget, or silently drifting -- Boundaries & Constraints, I/O & Edge-Case Matrix, verifiable Tasks & Acceptance (incl. named cross-cutting concerns), Code Map & Dependency freshness, Verification-vs-[verify]-commands alignment (incl. new-phase hang safety), and story sizing against the token budget. Use before approving/freezing a spec for bmad-loop, after bmad-create-story, or whenever the user asks to "check", "validate", or "review" a story spec's readiness. Read-only -- reports findings, does not edit the spec.
---

# Spec Quality Gate

## Why this exists

`bmad-loop` drives unattended sessions off the frozen spec alone -- there is no
one to ask mid-run. Real incidents in this repo's `.harness/ledger/` and
`_bmad-output/planning-artifacts/harness-engineering-plan.md` show what an
underspecified spec costs, and which of those gaps are already closed at the
system level vs. still resting entirely on the spec author:

- `1-1-invite-a-person`: a parity requirement ("UI must match the Studio
  mock") lived only in prose (Implementation Notes), never became a checkable
  acceptance item, so no gate caught the drift -- fixed post-hoc by a human
  (commits `2f5711e`, `12abdd7`). **Still open** -- no mechanical Studio-mock
  parity gate exists in `.harness/scripts/verify` today, so this remains a
  spec-only defense.
- `1-4-inactivate-a-member`: the spec implied a React Doctor score check, but
  it wasn't reachable from the loop at the time, so the score silently
  regressed to 56 before a human caught it. **Now closed** -- `doctor` is a
  standing phase in `.harness/scripts/verify`, and `i18n-check.mjs` (the
  matching i18n-completeness gap from the same story) now runs as part of the
  `lint` phase. Kept here as the worked example for check 4/6, not as a live
  gap.
- `1-5-preset-a-member-code-during-invitation` (run `20260716-214305-eaf6`):
  the story spent **~3.27M weighted tokens** against a 2M `max_tokens_per_story`
  budget, with no mid-loop enforcement -- the overrun was only visible after
  the fact, in the ledger. **Still open**, and specifically a sizing problem:
  nothing checks a story's likely token footprint before it's handed to the
  loop.
- Same run: a **new verify phase hung** (React Doctor blocking on TTY stdin --
  the second time this exact shape occurred, after Playwright's html-reporter
  in an earlier run) under the engine's non-interactive spawn context. The
  orchestrator's outer kill destroyed the phase's evidence, and a retry
  session burned ~1.1M tokens guessing from an unlabeled "timed out". The
  "phase authoring contract" in `docs/development-guide/verify-gate.md` exists
  because of this -- but nothing checks a *new* spec-introduced verify phase
  against that contract before it's frozen.

The throughline: spec problems, not code problems. The spec *implied* a
requirement, a safe size, or a safe new check, without making it *checkable*
or *proven-safe* before the loop ran unattended against it. This skill exists
to catch that class of gap before the spec is approved, not after.

## Inputs

Accepts a story key (e.g. `1-4-inactivate-a-member`) or a direct path to a
spec file. If neither is given:

1. Resolve `implementation_artifacts` via
   `uv run --python 3.11 _bmad/scripts/resolve_config.py --project-root {project-root}`.
2. List spec files under that path whose `status:` frontmatter is not `done`
   (i.e. not yet frozen/shipped) and ask the user which one to check. If
   exactly one exists, use it without asking.

## Procedure

### 1. Load context

- Read the target spec file in full.
- Read `{project-root}/.bmad-loop/policy.toml` and extract `[verify]
  commands` and `[limits] max_tokens_per_story` (needed for checks 6 and 7).
  Missing file/section is itself a finding, not a skip condition.
- Read `{implementation_artifacts}/sprint-status.yaml` (needed for check 5's
  dependency ordering).
- Read `docs/development-guide/verify-gate.md`'s "phase authoring contract"
  section (needed for check 6's new-phase safety sub-check).
- List `{project-root}/.harness/ledger/*.yaml` and skim `wall_clock_hours` /
  `tokens.weighted_total` (when present) for 2-3 stories of comparable scope
  (similar task count or same epic) as a sizing baseline for check 7.

### 2. Check -- Boundaries & Constraints

- The section must exist and be non-empty.
- It must contain concrete negative/out-of-scope statements -- what must
  **not** happen, be built, or be assumed -- not just a restatement of the
  positive requirements. Scan for explicit negation ("must not", "never",
  "does not", "out of scope", "not responsible for") or Vietnamese
  equivalents ("không được", "không hỗ trợ").
- FAIL if the section is missing, or every sentence in it is positive-only
  (e.g. restates what to build rather than what to avoid).

### 3. Check -- I/O & Edge-Case Matrix

- The section must exist as a table or explicit list of
  `input/edge case -> expected output` pairs.
- Judge coverage against what's plausible for *this* story's domain --
  common categories worth checking for when relevant: empty/null input,
  invalid input, unauthorized/permission-denied, boundary values,
  duplicate/concurrent action, external/network failure. Do not demand a
  category that plainly doesn't apply (e.g. "concurrent edit" for a
  read-only display story) -- but flag an obviously relevant one that's
  missing (e.g. a mutation/write story with no duplicate-submission or
  concurrent-edit row).
- Each row's expected output must be concrete (a specific error, state, or
  UI behavior) -- "handle gracefully" or "show appropriate message" FAILs
  that row.

### 4. Check -- Tasks & Acceptance

- Every acceptance item must be independently checkable: by an automated
  command, or by a specific observable state ("field X shows value Y",
  "response is 403"). Vague criteria ("works correctly", "good UX") FAIL.
- **Named cross-cutting-concern checklist.** Don't rely on generic scanning
  alone -- check explicitly, by name, whether this story's Design/
  Implementation Notes touch any of these known project blind spots, and if
  so whether each has a matching Tasks & Acceptance item:
  - **Studio mock parity** -- any story building/changing admin/account/pos
    UI that references a Studio mock (`apps/*/app/studio/**`) must have an
    explicit acceptance item that the shipped route matches it. No
    mechanical gate exists for this (see "Why this exists") -- the spec is
    the only defense.
  - **Tenant RLS / isolation** -- any story touching `iam.*` tables, a
    `service_role` path, or cross-tenant data must have an explicit
    positive+negative acceptance pair (tenant A sees its own data, tenant B
    is invisible), not just a general "RLS enforced" statement.
  - **Protected-files boundary** -- any story whose Code Map touches a file
    listed in `.harness/protected-files.json` (e.g. `.bmad-loop/policy.toml`,
    `.claude/settings.json`, `.harness/disposition-authority.json`) must
    have an explicit acceptance item naming the approval-label flow, since a
    plain commit will be blocked by the pre-commit hook mid-loop.
  - **i18n** -- covered automatically by `i18n-check.mjs` in the `lint`
    phase, so this is a lower-priority check now; still flag a story that
    hardcodes a locale string as an anti-pattern if you see one, but do not
    fail the spec solely for omitting an explicit i18n acceptance item.
- Beyond the named list above, still cross-check the **whole spec** (Intent,
  Design Notes, Implementation Notes) for other requirement-shaped
  statements referencing specific artifacts or behavior that are **not**
  promoted into a Tasks & Acceptance item. This is the general form of the
  check that would have caught the `1-1` mock-parity gap -- report every
  orphaned requirement by name and by the line it was found at.

### 5. Check -- Code Map & Dependency freshness

- **Code Map.** For each file/path listed in the spec's Code Map, confirm it
  either exists in the current tree, or is unambiguously marked as new (e.g.
  prefixed with "create", "new file"). A path that reads as existing but
  isn't (or vice versa) sends the dev session exploring or editing the wrong
  place -- FAIL and name the stale path.
- **Dependencies vs. build order.** Cross-check the spec's declared
  Dependencies against `{implementation_artifacts}/sprint-status.yaml`'s
  `development_status`. Every prerequisite story/epic named must already be
  `done`. Remember story *numbering* is not build *order* in this project
  (see the BUILD-ORDER NOTE at the top of `sprint-status.yaml`) -- check the
  actual recorded status, never infer readiness from the story key's number.
  FAIL if a named dependency isn't `done`, or if the spec's Code Map assumes
  an artifact (table, exported function, route) that a not-yet-done
  dependency is supposed to produce.

### 6. Check -- Verification vs. `[verify] commands`

- List every check the spec's Verification section names as "how we know
  this is done."
- For each one, confirm it is covered by an automated command in
  `[verify] commands`, OR the spec explicitly marks it as a manual/
  out-of-band check with an owner (e.g. "manual: human confirms visually").
- FAIL any verification the spec implies is machine-checked but that has no
  reachable command in `[verify] commands` and no explicit manual-check
  callout -- this is the class of gap that let the `1-4` React Doctor
  regression through before `doctor` became a standing verify phase.
- **New-phase hang safety.** If the spec's Verification section introduces a
  check/tool that is **not** already one of the existing `[verify] commands`
  (a new lint rule, a new CLI tool, a new script), confirm the spec (or the
  Code Map entry that adds it) accounts for the "phase authoring contract"
  in `docs/development-guide/verify-gate.md`: non-interactive invocation
  (stdin from `/dev/null` + the tool's own CI/non-interactive flag) and its
  own wall-clock bound (the tool's internal budget flag, if any, plus
  `run_with_timeout` as backstop). FAIL silently-assumed-safe new phases --
  this exact gap hung the loop twice (Playwright's html-reporter, React
  Doctor's TTY wait), each time burning ~1M+ tokens on a retry session that
  had nothing to diagnose from an unlabeled "timed out".

### 7. Check -- Story sizing vs. token budget

- Estimate the story's shape: count Tasks & Acceptance items, distinct files
  in the Code Map, and any explicitly new subsystems/packages.
- Compare against the sizing baseline gathered in step 1 (`wall_clock_hours`
  / `tokens.weighted_total` from 2-3 comparably-scoped ledger records) and
  against `[limits] max_tokens_per_story` in `.bmad-loop/policy.toml`.
- FAIL (or flag "borderline") when the story's shape looks materially larger
  than the comparably-scoped baseline stories, or spans multiple unrelated
  subsystems that could split along a natural seam (e.g. a DB migration +
  service layer + two separate app UIs). Recommend a concrete split point
  when flagging -- don't just say "too big." This is the check that would
  have flagged `1-5-preset-a-member-code-during-invitation` (~3.27M weighted
  tokens against a 2M budget) before the loop ran, not after.
- Do not fail a story solely for being the first of its kind (no comparable
  baseline yet) -- note the absence of a baseline instead and rely on the
  other signals (task/file count, subsystem span).

### 8. Report

Produce a per-check (2-7) PASS/FAIL/BORDERLINE with concrete evidence (quote
or line reference) and a one-line fix suggestion per FAIL. End with one
overall verdict:

- **READY** -- hand off to `bmad-dev-story`/`bmad-loop` as-is.
- **NOT READY** -- list the smallest set of edits that would flip each FAIL
  to PASS, ordered by how much escalation/drift risk each one removes.

Do not edit the spec. Offer, but don't do without being asked:

- Writing this report to
  `{implementation_artifacts}/spec-quality-report-<story-key>.md` for
  traceability alongside the ledger.
- Making the edits directly, if the user asks for that in the same turn.

## Out of scope

- Not an editor -- read-only findings only, unless explicitly asked to fix.
- Not a technical/architectural review -- this checks specification
  *verifiability*, not whether the chosen approach is sound (that's
  `bmad-architecture` / `bmad-check-implementation-readiness`).
- Not a replacement for `bmad-create-story:validate` -- that checks general
  story readiness and template completeness; this checks a specific,
  ledger-evidenced set of blind spots (verifiability, named cross-cutting
  concerns, dependency/build-order accuracy, new-verify-phase hang safety,
  token-budget sizing) that this repo's own incidents show slip through
  generic readiness checks. Run both.
