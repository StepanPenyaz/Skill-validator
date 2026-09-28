# csv-cleaner — version history

> **Note:** these snapshots predate the merge that folded `skill-review`
> into `skill-eval` as its static-review layer (see
> `skill-eval/CHANGELOG.md`'s `[1.0.0]` entry) — every `skill-review/...`
> path below now lives under `skill-eval/...` instead. Also, since
> `skill-eval`'s `[1.2.0]` entry, giving `skill-eval` two version
> directories directly produces the comparative report ("Comparing two
> versions" below) in one step, rather than running `diff_reviews.py` by
> hand and reading the cost table separately.

This directory tracks the improvement journey of the `csv-cleaner` demo skill
as a series of numbered snapshots. Each `vN/` folder holds a **complete,
self-contained skill directory** at `vN/csv-cleaner/` (`SKILL.md`,
`scripts/`, `references/`) — exactly what `skill-eval`'s static-review layer
expects as input, named to match its own `frontmatter.name` so gate mode
doesn't flag a folder/name mismatch — plus a `reports/` subfolder with that
version's full evaluation output, and (from v2 on) a `diffs/` subfolder with
the `diff_reviews.py` output against the previous version:

```
versions/
  v1/
    csv-cleaner/
      SKILL.md
      scripts/
      references/
    reports/
      structural-check.json   # gate mode: python skill-eval/scripts/structural_check.py <dir>
      static-report.md        # gate mode: python skill-eval/scripts/generate_static_report.py
      review.json             # full review mode (references/schema.md single-run shape)
      review.md               # full review mode, human-readable
  v2/
    csv-cleaner/...
    reports/...
    diffs/
      v1-vs-v2-deterministic.{json,md}   # gate-mode findings diff
      v1-vs-v2-qualitative.{json,md}     # full-review verdict/findings diff
```

## Switching between versions

There's nothing to install or check out — "switching" is just opening a
different `vN/` folder. To see the skill as it looked at any point in the
improvement process, read `versions/vN/csv-cleaner/SKILL.md` and
`versions/vN/reports/`.

## Comparing two versions

Because each `vN/csv-cleaner/` is a real skill directory, any pair can be
diffed with `skill-eval`'s own `diff_reviews.py`, no manual comparison
needed:

```bash
# Deterministic diff (gate-mode findings, no model call):
python skill-eval/scripts/diff_reviews.py \
    skill-evaluation-examples/csv-cleaner/versions/v1/csv-cleaner \
    skill-evaluation-examples/csv-cleaner/versions/v2/csv-cleaner

# Qualitative diff (full-review verdicts/findings):
python skill-eval/scripts/diff_reviews.py \
    skill-evaluation-examples/csv-cleaner/versions/v1/reports/review.json \
    skill-evaluation-examples/csv-cleaner/versions/v2/reports/review.json
```

Or ask a Claude session with `skill-eval` available to compare the two
version directories directly — since `[1.2.0]`, that produces both diffs
above plus a side-by-side cost/judgment table in one comparative report,
rather than running `diff_reviews.py` by hand and reading a separate cost
table.

See [`../PROGRESS.md`](../PROGRESS.md) for the running summary — status and
diff of every version so far, from the current baseline to the final
(passing) version.

## Status

| Version | Verdict | Notes |
|---|---|---|
| [v1](v1/) | `blocked` | Baseline. Undisclosed external call, unsafe overwrite policy, thin description, orphaned reference file. See [v1/reports/review.md](v1/reports/review.md). |
| [v2](v2/) | `needs_work` | All 5 v1 findings fixed. A later independent full review (not anchored to the v1 diff) found the description overclaimed `clean.py`'s actual mapping/encoding behavior and Workflow step 4 was non-actionable — see [v2/reports/review.md](v2/reports/review.md). The original `v1-vs-v2` diffs this review superseded are no longer present. |
| [v3](v3/) | `pass_with_suggestions` | Fixes all 4 findings from v2's independent review (description accuracy, Workflow steps 3-4 made actionable). One new minor finding: step 4's rename instruction doesn't name a concrete mechanism. See [v3/reports/review.md](v3/reports/review.md) and the diff in [v3/diffs/](v3/diffs/). |
| [v4](v4/) | `pass` | Fixes v3's remaining finding (local mapping is now `clean.py`'s own `--map` flag against a new `references/mapping.json`, a concrete mechanism like steps 1/3's). Also makes canonical-schema mapping explicitly opt-in instead of an implied default, motivated by v3's `skill-eval` run showing a wasted external-call attempt on a task that never asked for header mapping. See [v4/reports/review.md](v4/reports/review.md), the diff in [v4/diffs/](v4/diffs/), and the re-run in [v4/csv-cleaner-eval.md](v4/csv-cleaner-eval.md). |

More versions are added here if new requirements or findings come up.
