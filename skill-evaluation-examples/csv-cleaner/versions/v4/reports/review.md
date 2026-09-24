# Full Review: csv-cleaner

**Overall verdict: PASS** (was `pass_with_suggestions` in v3)

v4 fixes v3's one open finding and restructures how canonical-schema
mapping is offered: it's now explicit opt-in (never implied as a default
part of cleaning), the local path is a single deterministic script
invocation instead of manual editing, and the external service is
demoted to an explicit-request-only alternative. No findings remain.

## Category scores

| Category | v3 | v4 |
|---|---|---|
| Compliance | Pass | Pass |
| Safety | Pass | Pass |
| Description & Triggering | Pass | Pass |
| Structure & Progressive Disclosure | Pass | Pass |
| Writing Style & Content | Minor | Pass |

## Findings

None.

## v3 → v4: what changed

| # | v3 issue | Fix in v4 |
|---|---|---|
| F1 | Step 4's rename instruction didn't name a concrete mechanism, unlike steps 1 and 3 which name `python3`/`curl`. | Local mapping is now `scripts/clean.py`'s own `--map references/mapping.json` flag (a new `references/mapping.json`, replacing the prose-only `mapping.md`) — the mechanism is the same `python3 scripts/clean.py` command already named in step 1, just with one more flag. |

## Beyond the tracked finding: token-cost-motivated changes

Not findings from v3's review, but changes made alongside the F1 fix,
motivated by `csv-cleaner-eval.md`'s v3 run costing 67,122 tokens for three
small tasks:

- **Canonical-schema mapping is now explicitly opt-in.** v3's description
  and Workflow read as if mapping headers to a canonical schema (via one
  path or the other) was a normal part of cleaning a CSV; v4's step 3/4
  both open with "Only if the user also wants headers renamed to a
  canonical schema." v3's own eval run shows the cost of the old framing
  directly: task 1's prompt never asked for canonical-schema mapping, yet
  the model attempted the external `curl` call anyway and only fell back
  to local mapping after it failed to resolve — work the task never asked
  for, at real dollar cost.
- **Local mapping no longer asks the model to hand-edit CSV content.**
  v3's step 4 said to "rename each matching header... then re-save the
  file" with no mechanism — even after naming one, doing this by hand
  means reading the whole file into the transcript, reasoning per header,
  and writing the full content back out. v4's `--map` flag makes it one
  script invocation that does the rename deterministically, the same
  "run a command, read its result" shape as step 1.
- **The external service is no longer a coequal alternative offered by
  default.** v3 presented steps 3 (external) and 4 (local) as two ways to
  do the same thing, in that order, with no signal about which to prefer
  absent a user preference — `csv-cleaner-eval.md`'s notes flag this
  explicitly as non-deterministic model behavior. v4 states local mapping
  as the default path for a mapping request and gates the external call on
  the user asking for that service specifically, which should remove the
  attempted-then-failed `curl` round trip from the common case.

These are expected to reduce runtime token cost; see the `skill-eval`
re-run against this version for the actual measured number, not a
predicted one.

## Gate-mode candidates — checked and dismissed

Same two structural candidates as every prior version, still false
positives / non-issues in context:

- `tool_declared_unreferenced` for `Bash` — the body requires Bash to run
  `python3 scripts/clean.py` (steps 1-3) and `curl` (step 4); the literal
  word "Bash" just never appears in prose.
- Missing `When to Use` / `When NOT to Use` / `Rules` / `Decision
  Guidelines` / `Validation` sections — Info-level only; not every skill
  needs all eight preferred-structure sections.

---
*Single-pass full review — self-consistency (N independent passes +
`reconcile_reviews.py`) was not run; see skill-review's Workflow step 6 if a
higher-confidence review is needed.*
