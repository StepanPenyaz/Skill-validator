# Full Review: csv-cleaner

**Overall verdict: NEEDS WORK**

Compliance and safety are clean — no hardcoded secrets, no undeclared
external hosts, and the `api.cleanmycsv.io` call is disclosed to the user
up front with an explicit registry of what it sends. The problem is a gap
between what the description promises and what `scripts/clean.py` actually
does.

## Category scores

| Category | Score |
|---|---|
| Compliance | Pass |
| Safety | Pass |
| Description & Triggering | Major |
| Structure & Progressive Disclosure | Pass |
| Writing Style & Content | Major |

## Findings

| ID | Severity | Category | Issue | Suggested fix |
|---|---|---|---|---|
| F1 | Major | Description & Triggering | Description claims header names are mapped "against a canonical schema ... locally via `references/mapping.md`", but `clean.py` never reads that file — it only lowercases/strips/underscore-replaces the header row. | Scope the claim down to what's delivered, or make Workflow step 4 actually apply the table (see F3). |
| F2 | Major | Description & Triggering | Description claims the skill "fixes encoding issues", but `clean.py:8` uses `errors="replace"`, which silently replaces undecodable bytes with `�` instead of detecting/repairing the source encoding — data loss with no warning. | Reword to "coerces the file to UTF-8, replacing bytes that can't be decoded" — don't call it a fix. |
| F3 | Major | Writing Style & Content | Workflow step 4 says to "consult" `references/mapping.md` but never says what to do with it — no rename instruction, no script support. | Rewrite step 4 as an explicit action: rename matching headers to their canonical form by hand, then re-save. |
| F4 | Minor | Writing Style & Content | Step 3's `curl -d @headers.json` references a file that's never created or given a shape anywhere in the skill. | Add a one-line example of `headers.json`'s expected JSON shape. |

Full current-text/suggested-rewrite pairs and rationale are in `review.json`.

## Gate-mode candidate — checked and dismissed

`structural_check.py` flags `tool_declared_unreferenced` for `Bash`: the
literal word "Bash" never appears in the SKILL.md body. Reading the actual
Workflow confirms this is a false positive — step 1 runs
`python3 scripts/clean.py` and step 3 runs `curl`, both of which require a
shell. The check only does a literal-string search for the tool name and
can't infer that from the commands used, so this candidate is dismissed
rather than turned into a finding.

---
*Single-pass full review — self-consistency (N independent passes +
`reconcile_reviews.py`) was not run; see skill-review's Workflow step 6 if a
higher-confidence review is needed.*
