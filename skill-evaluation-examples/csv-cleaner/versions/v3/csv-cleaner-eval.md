# skill-eval Report: csv-cleaner

> **Gate check** (via skill-review) — passed, evaluation proceeded:
> - Stage 1a (deterministic): 2 structural warning(s), not blocking.
> - Stage 1b (qualitative): `overall_verdict` = `pass_with_suggestions`, not blocking.

| Model Used | Number of Tokens | Time Spent | Claude's Judgment |
|---|---:|---:|---|
| sonnet | ~5,500 (estimated) | 4m 15s | • Correctly ran clean.py without --in-place (wrote contacts.csv.cleaned.csv, left the original 3-row file untouched) and deduplicated the exact-duplicate Jane Doe row, going from 3 to 2 data rows.<br>• For task 1, on its own initiative skipped the external api.cleanmycsv.io call (step 3) since the user hadn't been told/asked about header names leaving the machine, and instead applied step 4's local mapping.md table by hand -- correctly rewriting 'e-mail' to 'email' and 'zip' to 'postal_code' while leaving 'city' untouched (not in the table), exactly the actionable behavior v3's fix to F3 was meant to produce.<br>• For task 2, reproduced the identical canonical mapping ('e-mail'->'email', 'zip'->'postal_code') when explicitly told to use only the local table -- step 4's instruction is followed deterministically rather than improvised differently run to run.<br>• For task 3 (Excel file with a pivot table and a chart), correctly declined rather than fabricating capability, citing that clean.py only reads/writes CSV via Python's csv module with no spreadsheet or charting support, instead of over-triggering into an out-of-scope task. |

## Notes

- **Task fixture**: `skill-eval/tests/fixtures/tasks/csv-cleaner.yaml` (new
  — no prior fixture existed for csv-cleaner). Frozen as of this run; reuse
  it unchanged for any future version comparison against v3, per
  `references/task-authoring.md`.
- **Gate-check history for context** (not itself part of this run's cost):
  the same skill directory's *previous* version, v2, scored
  `needs_work` on stage 1b before the F1-F4 fixes that produced v3 — see
  [`../v3/reports/review.md`](reports/review.md) and
  [`../v3/diffs/v2-vs-v3-qualitative.md`](diffs/v2-vs-v3-qualitative.md).
- **Token estimate vs. this session's own measured usage**: the subagent
  self-reported `~5,500` tokens using the `(prompt + final report length)
  / 4` estimate `references/token-capture.md` prescribes. This session's
  `Agent` tool call, however, also returned a real measured
  `subagent_tokens: 68731` in its own usage metadata for the same call —
  about **12x** the self-report. `token-capture.md` documents that no
  mechanism was found, at the time it was written, for the orchestrating
  session to retrieve a spawned subagent's real usage — that may no longer
  hold in this environment/tool version, since a real number was visible
  here without any extra instrumentation. Worth a follow-up look at
  `references/token-capture.md`'s investigation before trusting the
  estimated column at face value; flagged rather than silently used to
  replace the prescribed estimate, since changing the token-source
  mechanism is a `skill-eval` design decision, not something to make
  unilaterally mid-run.
