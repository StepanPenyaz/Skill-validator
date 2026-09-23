# csv-cleaner — version history

This directory tracks the improvement journey of the `csv-cleaner` demo skill
as a series of numbered snapshots. Each `vN/` folder holds a **complete,
self-contained skill directory** at `vN/csv-cleaner/` (`SKILL.md`,
`scripts/`, `references/`) — exactly what `skill-review` expects as input,
named to match its own `frontmatter.name` so gate mode doesn't flag a
folder/name mismatch — plus a `reports/` subfolder with that version's full
evaluation output, and (from v2 on) a `diffs/` subfolder with the
`diff_reviews.py` output against the previous version:

```
versions/
  v1/
    csv-cleaner/
      SKILL.md
      scripts/
      references/
    reports/
      structural-check.json   # gate mode: python skill-review/scripts/structural_check.py <dir>
      static-report.md        # gate mode: python skill-review/scripts/generate_static_report.py
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
diffed with skill-review's own tool, no manual comparison needed:

```bash
# Deterministic diff (gate-mode findings, no model call):
python skill-review/scripts/diff_reviews.py \
    skill-evaluation-examples/csv-cleaner/versions/v1/csv-cleaner \
    skill-evaluation-examples/csv-cleaner/versions/v2/csv-cleaner

# Qualitative diff (full-review verdicts/findings):
python skill-review/scripts/diff_reviews.py \
    skill-evaluation-examples/csv-cleaner/versions/v1/reports/review.json \
    skill-evaluation-examples/csv-cleaner/versions/v2/reports/review.json
```

See [`../PROGRESS.md`](../PROGRESS.md) for the running summary — status and
diff of every version so far, from the current baseline to the final
(passing) version.

## Status

| Version | Verdict | Notes |
|---|---|---|
| [v1](v1/) | `blocked` | Baseline. Undisclosed external call, unsafe overwrite policy, thin description, orphaned reference file. See [v1/reports/review.md](v1/reports/review.md). |
| [v2](v2/) | `needs_work` | All 5 v1 findings fixed. A later independent full review (not anchored to the v1 diff) found the description overclaimed `clean.py`'s actual mapping/encoding behavior and Workflow step 4 was non-actionable — see [v2/reports/review.md](v2/reports/review.md). The original `v1-vs-v2` diffs this review superseded are no longer present. |
| [v3](v3/) | `pass_with_suggestions` | Fixes all 4 findings from v2's independent review (description accuracy, Workflow steps 3-4 made actionable). One new minor finding: step 4's rename instruction doesn't name a concrete mechanism. See [v3/reports/review.md](v3/reports/review.md) and the diff in [v3/diffs/](v3/diffs/). |

More versions are added here if new requirements or findings come up.
