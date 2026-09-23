# skill-eval Report: csv-cleaner

> **Gate check** (via skill-review) — passed, evaluation proceeded:
> - Stage 1a (deterministic): 2 structural warning(s), not blocking.
> - Stage 1b (qualitative): `overall_verdict` = `pass_with_suggestions`, not blocking.

| Model Used | Number of Tokens | Time Spent | Claude's Judgment |
|---|---:|---:|---|
| sonnet | 67,122 | 2m 25s | • For task 1, attempted the external `curl https://api.cleanmycsv.io/normalize-headers` call from Workflow step 3 (unlike the prior recorded run, which skipped it on its own initiative over data-sharing concerns); the call failed with `curl: (6) Could not resolve host`, and only then fell back to step 4's local `mapping.md` table.<br>• For task 2, when explicitly told not to send headers externally, skipped step 3 entirely (no curl call made) and applied `mapping.md`'s table directly, producing the same header result (`e-mail`->`email`, `zip`->`postal_code`, `city` unchanged) as task 1's fallback.<br>• For task 3, correctly declined the Excel/pivot-table/chart request, citing that clean.py only reads/writes CSV via its declared `Bash` tool with no spreadsheet or charting support, instead of fabricating capability or reaching for an unrelated skill.<br>• Both task 1 and task 2 ran clean.py without `--in-place`, writing output to `contacts.csv.cleaned.csv` and leaving the original 3-row `contacts.csv` untouched throughout, and both correctly deduplicated the exact-duplicate Jane Doe row (3 to 2 data rows). |

## Notes

- **This is a re-run**, not the original run — done after `SKILL.md`
  Workflow step 2 and `references/token-capture.md` were updated (v0.13.0)
  to read the real `subagent_tokens` value off the `Agent` tool's own
  return metadata instead of a self-reported estimate. `tokens_estimated`
  is `false` for the row above; no `(estimated)` label. As the previous
  run's notes predicted, a re-run under the fixed mechanism reports the
  real number directly: `67,122` here, in the same range as the `68,731`
  the previous run's `Agent` call returned (that run used the old
  self-report of `~5,500` in its table, ~12x lower).
- **Run-to-run behavioral variance observed**: this run's model attempted
  the external `api.cleanmycsv.io` call for task 1 (falling back to the
  local mapping table only after the call failed to resolve), whereas the
  previous run skipped that call on its own initiative without being told
  the API wasn't real. Both runs converged on the same final output, but
  by different paths — worth keeping in mind that `SKILL.md`'s guidance
  for when to use the external-vs-local mapping path leaves room for the
  model to decide either way absent an explicit user preference, and that
  choice isn't deterministic across runs. Task 2 (explicit "don't send
  headers externally") and task 3 (decline the out-of-scope request)
  reproduced the same behavior as before.
- **Task fixture**: `skill-eval/tests/fixtures/tasks/csv-cleaner.yaml`,
  unchanged since it was authored, reused as-is per
  `references/task-authoring.md`'s frozen-fixture rule.
- **Gate-check history for context** (not itself part of this run's cost):
  the same skill directory's *previous* version, v2, scored `needs_work`
  on stage 1b before the F1-F4 fixes that produced v3 — see
  [`reports/review.md`](reports/review.md) and
  [`diffs/v2-vs-v3-qualitative.md`](diffs/v2-vs-v3-qualitative.md).
- **History of the token-count column**: the original run against this
  version self-reported `~5,500 (estimated)` tokens, using the
  `(prompt + final report length) / 4` estimate `references/token-capture.md`
  prescribed at the time. That same `Agent` call's own return metadata,
  however, carried a real `subagent_tokens: 68731` — about 12x higher.
  That discrepancy, once confirmed a second time by this project's own
  `skill-review` self-eval (`EXAMPLE-RESULTS.md`), is what got
  `token-capture.md`'s Decision and `SKILL.md` Workflow step 2 changed to
  use the real value going forward. This report is the first `csv-cleaner`
  run produced under that fixed mechanism.
