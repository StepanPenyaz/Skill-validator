# csv-cleaner — version history

This directory tracks the improvement journey of the `csv-cleaner` demo skill
as a series of numbered snapshots. Each `vN/` folder is a **complete,
self-contained skill directory** (`SKILL.md`, `scripts/`, `references/`) —
exactly what `skill-review` expects as input — plus a `reports/` subfolder
holding that version's full evaluation output:

```
versions/
  v1/
    SKILL.md
    scripts/
    references/
    reports/
      structural-check.json   # gate mode: python skill-review/scripts/structural_check.py <dir>
      static-report.md        # gate mode: python skill-review/scripts/generate_static_report.py
      review.json             # full review mode (references/schema.md single-run shape)
      review.md               # full review mode, human-readable
```

## Switching between versions

There's nothing to install or check out — "switching" is just opening a
different `vN/` folder. To see the skill as it looked at any point in the
improvement process, read `versions/vN/SKILL.md` and `versions/vN/reports/`.

## Comparing two versions

Because each `vN/` is a real skill directory, any pair can be diffed with
skill-review's own tool, no manual comparison needed:

```bash
# Deterministic diff (gate-mode findings, no model call):
python skill-review/scripts/diff_reviews.py \
    skill-evaluation-examples/csv-cleaner/versions/v1 \
    skill-evaluation-examples/csv-cleaner/versions/v2

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

More versions are added here as `csv-cleaner` gets fixed, one issue at a
time, until it reaches a clean `pass`.
