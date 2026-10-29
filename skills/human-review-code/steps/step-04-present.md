---
---

# Step 4: Present

## RULES

- YOU MUST ALWAYS SPEAK OUTPUT in your Agent communication style with the config `{communication_language}`
- Do NOT auto-fix anything. Present findings and let the user decide next steps.

## INSTRUCTIONS

1. Group remaining findings by category.

2. Present to the user in this order (include a section only if findings exist in that category):

   - **Intent Gaps**: "These findings suggest the captured intent is incomplete. Consider clarifying intent before proceeding."
     - List each with title + detail.

   - **Bad Spec**: "These findings suggest the spec should be amended. Consider regenerating or amending the spec with this context:"
     - List each with title + detail + suggested spec amendment.

   - **Performance Issues**: "These are performance, N+1, or efficiency issues:" (NEW section — not present in bmad-code-review)
     - Sub-group by category: `n_plus_1`, `inefficient_loop`, `missing_bulk`, `oversized_component`, `unnecessary_api`, `inefficient_transform`, `complexity`
     - List each with title + detail + suggestion + location (if available).
     - These are technically `patch` but get their own prominent section for visibility.

   - **Patch**: "These are fixable code issues:"
     - List each with title + detail + location (if available).

   - **Defer**: "Pre-existing issues surfaced by this review (not caused by current changes):"
     - List each with title + detail.

3. Summary line: **X** intent_gap, **Y** bad_spec, **Z** performance, **W** patch, **V** defer findings. **R** findings rejected as noise.

4. If clean review (zero findings across all layers after triage): state that N findings were raised but all were classified as noise, or that no findings were raised at all (as applicable).

5. Offer the user next steps (recommendations, not automated actions):
   - If `performance` findings exist: "Performance issues often require algorithmic changes — consider using `useMemo`/`useCallback`, batching DB queries, or reducing API call counts."
   - If `patch` findings exist: "These can be addressed in a follow-up implementation pass or manually."
   - If `intent_gap` or `bad_spec` findings exist: "Consider running the planning workflow to clarify intent or amend the spec before continuing."
   - If only `defer` findings remain: "No action needed for this change. Deferred items are noted for future attention."

Workflow complete.
