# skill-eval Report: csv-cleaner

> **Gate check** (via skill-review) — passed, evaluation proceeded:
> - Stage 1a (deterministic): 2 structural warning(s), not blocking.
> - Stage 1b (qualitative): `overall_verdict` = `pass`, not blocking.

| Model Used | Number of Tokens | Time Spent | Claude's Judgment |
|---|---:|---:|---|
| sonnet | 65,096 | 13m 57s | • For task 1 (no canonical-mapping request), ran only `python scripts/clean.py contacts.csv` and made no external call at all - unlike the v3 run against this same task, which attempted `curl https://api.cleanmycsv.io/normalize-headers` first and only fell back to local mapping after the call failed to resolve.<br>• For task 2 (explicit local-mapping-only request), used the new `--map references/mapping.json` flag on the same `clean.py` invocation instead of hand-editing the CSV, producing the exact expected header mapping (`e-mail`->`email`, `zip`->`postal_code`, `city` left as-is since it isn't in the table) in one deterministic script call.<br>• For task 3, correctly declined the Excel/pivot-table/chart request, citing that `clean.py` only reads/writes CSV via Python's `csv` module with no spreadsheet or charting support, instead of fabricating capability.<br>• Both task 1 and task 2 ran without `--in-place`, writing to `contacts.csv.cleaned.csv` and leaving the original 3-row `contacts.csv` untouched throughout (verified directly against the file after the run), and both correctly deduplicated the exact-duplicate Jane Doe row (3 to 2 data rows). |

## Notes

- **Token count vs. v3**: 65,096 here vs. 67,122 for v3's run of the same
  task set (`versions/v3/csv-cleaner-eval.md`) — about 3% lower. Both
  numbers are real `subagent_tokens`, not estimates. This is a smaller
  drop than the design change might suggest: v4 was meant to remove a
  whole wasted round trip (v3's task-1 run attempted the external `curl`
  call before falling back to local mapping; this run skipped that
  entirely, matching v3's task 2 and 3 behavior exactly). It's possible
  that failed DNS-resolution round trip itself was cheap in tokens even
  though it changed the model's reasoning path, or that other parts of
  the transcript (tool definitions, thinking) dominate the total enough
  to dilute the saving. This is one run on each side, not an average — see
  the run-to-run variance point below before treating either number as a
  stable baseline.
- **Time went up, not down, despite fewer tokens**: 13m 57s here vs. 2m
  25s for v3's run. `references/token-capture.md` and v3's own notes
  already establish that this environment's wall-clock time and token
  count aren't tightly coupled (model response latency varies run to
  run independent of transcript size), so this isn't read as a
  regression caused by v4's changes — but it's reported as measured,
  not smoothed over, since the whole point of this project is not to
  round an inconvenient number away.
- **Behavioral difference confirmed**: this run's task 1 did *not*
  attempt the external `api.cleanmycsv.io` call, unlike v3's task-1 run
  (which is the specific behavior v4's Workflow rewrite — canonical-
  schema mapping is now opt-in, not implied as part of every clean —
  was meant to produce). Tasks 2 and 3 reproduced the same behavior as
  every prior version.
- **Task fixture**: `skill-eval/tests/fixtures/tasks/csv-cleaner.yaml`,
  unchanged since it was authored, reused as-is per
  `references/task-authoring.md`'s frozen-fixture rule.
- **Gate-check history for context** (not itself part of this run's
  cost): this version's `skill-review` full review scored `pass` (up
  from v3's `pass_with_suggestions`) — see
  [`reports/review.md`](reports/review.md) and
  [`diffs/v3-vs-v4-qualitative.md`](diffs/v3-vs-v4-qualitative.md).
- **Caveat on drawing conclusions from single runs**: as `csv-cleaner-eval.md`
  for v3 already noted, this environment shows real run-to-run
  behavioral and cost variance for the same skill version. A single v4
  run being marginally cheaper in tokens and slower in wall-clock time
  than a single v3 run is a data point, not a trend — a higher-confidence
  before/after comparison would need multiple runs per version (out of
  scope for this pass; `skill-review`'s Workflow step 6 self-consistency
  mechanism doesn't apply here since that's for the qualitative review,
  not `skill-eval`'s runtime runs).
