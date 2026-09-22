# Full Review: csv-cleaner

**Overall verdict: PASS**

All five findings from the v1 review (F1-F5) are resolved. The skill now
discloses its external call, defaults to a non-destructive write, has a
triggering description, and no longer bundles an orphaned reference file.
No findings remain.

## Category scores

| Category | Score |
|---|---|
| Compliance | Pass |
| Safety | Pass |
| Description & Triggering | Pass |
| Structure & Progressive Disclosure | Pass |
| Writing Style & Content | Pass |

## What changed since v1

| # | v1 issue | Fix applied in v2 |
|---|---|---|
| F1 | Undisclosed external call to `api.cleanmycsv.io` (Blocker) | Host is now named in `frontmatter.description`; Workflow step 3 states exactly what is sent (header names only, never row data) and why; a new `references/external-calls.json` registers the call with `key`/`value`/`description`, linked from the SKILL.md References section. |
| F2 | 4-word description, no when-cue (Major) | Rewritten to 68 words: states what the skill does, that it writes to a new file by default, names the external service, and gives an explicit "Use this whenever..." trigger cue. |
| F3 | `MUST overwrite` + `NEVER backup` on an irreversible operation (Major) | `scripts/clean.py` now writes to `<path>.cleaned.csv` by default; the original is only overwritten in place if the user explicitly asks (`--in-place` flag). |
| F4 | `references/legacy_notes.md` never referenced anywhere (Minor) | Deleted — it documented an abandoned v0.x approach with no bearing on the current implementation. |
| F5 | Two directives crammed onto one line (Minor) | Split into two separate Workflow steps (now steps 1-2), each with its own clear instruction. |

## Remaining gate-mode candidate — checked and dismissed

`structural_check.py` still flags `tool_declared_unreferenced` for `Bash`:
the literal word "Bash" never appears in the SKILL.md body. Reading the
actual Workflow confirms this is a false positive — step 1 runs
`python3 scripts/clean.py` and step 3 runs `curl`, both of which require a
shell. The check only does a literal-string search for the tool name and
can't infer that from the commands used, so this candidate is dismissed
rather than turned into a finding.

---
*Single-pass full review — self-consistency (N independent passes +
`reconcile_reviews.py`) was not run; see skill-review's Workflow step 6 if a
higher-confidence review is needed.*
