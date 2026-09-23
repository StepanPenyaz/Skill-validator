# csv-cleaner — improvement progress

Running log of the fix-and-rerun cycle for the `csv-cleaner` demo skill, one
`skill-review` finding at a time. Each entry links to the version snapshot
and, once a next version exists, the `diff_reviews.py` output between it and
its predecessor. See [`versions/README.md`](versions/README.md) for the
folder layout and how to diff any two versions yourself.

## v1 — baseline

**Verdict: `blocked`**

| Category | Score |
|---|---|
| Compliance | Pass |
| Safety | **Blocker** |
| Description & Triggering | Major |
| Structure & Progressive Disclosure | Minor |
| Writing Style & Content | Minor |

Findings: F1 undisclosed external call (Blocker), F2 thin description
(Major), F3 unsafe overwrite-without-backup (Major), F4 orphaned
`legacy_notes.md` (Minor), F5 two directives crammed on one line (Minor).

Full detail: [`versions/v1/reports/review.md`](versions/v1/reports/review.md).

## v2 — all five v1 findings fixed

**Verdict: `pass`** (was `blocked`)

| Category | v1 | v2 |
|---|---|---|
| Compliance | Pass | Pass |
| Safety | **Blocker** | Pass |
| Description & Triggering | Major | Pass |
| Structure & Progressive Disclosure | Minor | Pass |
| Writing Style & Content | Minor | Pass |

| # | v1 issue | Fix in v2 |
|---|---|---|
| F1 | Undisclosed call to `api.cleanmycsv.io` (Blocker) | Host named in the description; Workflow step 3 states what is sent and why; registered in the new [`references/external-calls.json`](versions/v2/csv-cleaner/references/external-calls.json) (`key`/`value`/`description`, per [evaluation-checks.md](../../docs/plans/evaluation-checks.md#3-external-call-registry)), linked from SKILL.md's References section. |
| F2 | 4-word description, no when-cue (Major) | Rewritten to 68 words with an explicit trigger cue. |
| F3 | `MUST overwrite` / `NEVER backup` (Major) | `clean.py` now writes to `<path>.cleaned.csv` by default; original is only overwritten with an explicit `--in-place` flag. |
| F4 | Orphaned `references/legacy_notes.md` (Minor) | Deleted — documented an abandoned approach, no bearing on the current implementation. |
| F5 | Two directives on one line (Minor) | Split into two separate Workflow steps. |

One gate-mode candidate remains (`tool_declared_unreferenced` for `Bash`) but
was checked and dismissed as a false positive — see
[`versions/v2/reports/review.md`](versions/v2/reports/review.md) for why.

**Diff vs v1** (via `skill-review/scripts/diff_reviews.py`):

- Deterministic (gate mode): 8 → 2 structural warnings, 7 resolved, 0
  compliance errors either version. Full output:
  [`versions/v2/diffs/v1-vs-v2-deterministic.md`](versions/v2/diffs/v1-vs-v2-deterministic.md).
- Qualitative (full review): `blocked` → `pass`, all 5 findings resolved, 0
  new, 0 severity-changed. Full output:
  [`versions/v2/diffs/v1-vs-v2-qualitative.md`](versions/v2/diffs/v1-vs-v2-qualitative.md).

Full detail: [`versions/v2/reports/review.md`](versions/v2/reports/review.md).

---

*v2 already reaches a clean `pass` — further versions would only be needed
if new requirements or findings come up.*
