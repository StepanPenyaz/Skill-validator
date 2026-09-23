# Full Review: csv-cleaner

**Overall verdict: PASS WITH SUGGESTIONS** (was `needs_work` in v2)

All four findings from v2's independent full review are resolved: the
description no longer overclaims automatic canonical-schema mapping or
"fixing" encoding, and Workflow steps 3-4 are both now concrete, actionable
instructions instead of a bare file reference.

## Category scores

| Category | v2 | v3 |
|---|---|---|
| Compliance | Pass | Pass |
| Safety | Pass | Pass |
| Description & Triggering | Major | Pass |
| Structure & Progressive Disclosure | Pass | Pass |
| Writing Style & Content | Major | Minor |

## Findings

| ID | Severity | Category | Issue | Suggested fix |
|---|---|---|---|---|
| F1 | Minor | Writing Style & Content | Step 4 (the fix for v2's F3) now gives an explicit rename instruction, but doesn't name a concrete mechanism for it — steps 1 and 3 both name a command (`python3 scripts/clean.py`, `curl`); step 4 just says to "apply the table... rename it... re-save the file." | Name a concrete mechanism, e.g. a short Python/`csv` snippet run through Bash, consistent with step 1's tooling — see `review.json` for full wording. |

Full current-text/suggested-rewrite pairs and rationale are in `review.json`.

## v2 → v3: what changed

| # | v2 issue (from the independent review) | Fix in v3 |
|---|---|---|
| F1 | Description claimed headers are mapped "against a canonical schema... locally via `references/mapping.md`", but `clean.py` never applies that table. | Description now says local mapping means "Claude applies `references/mapping.md`'s table by hand — see Workflow step 4," matching what actually happens. |
| F2 | Description claimed the skill "fixes encoding issues"; `clean.py` actually does lossy `errors="replace"` decoding. | Description now says it "coerces the file to UTF-8, replacing any bytes that can't be decoded with a placeholder character" and explicitly notes source-encoding repair isn't attempted. |
| F3 | Workflow step 4 said to "consult" `mapping.md` with no instruction for what to do with it. | Step 4 now says explicitly: rename each matching header to its canonical name, then re-save the file. |
| F4 | Step 3's `curl -d @headers.json` referenced a file whose shape was never defined. | Step 3 now shows the expected shape: `{"headers": ["email", "full name", "zip"]}`. |

## Gate-mode candidates — checked and dismissed

Same two structural candidates as v1/v2, both still false positives / non-
issues in context:

- `tool_declared_unreferenced` for `Bash` — the body requires Bash to run
  `python3 scripts/clean.py` (step 1) and `curl` (step 3); the literal word
  "Bash" just never appears in prose.
- Missing `When to Use` / `When NOT to Use` / `Rules` / `Decision
  Guidelines` / `Validation` sections — Info-level only; not every skill
  needs all eight preferred-structure sections.

---
*Single-pass full review — self-consistency (N independent passes +
`reconcile_reviews.py`) was not run; see skill-review's Workflow step 6 if a
higher-confidence review is needed.*
