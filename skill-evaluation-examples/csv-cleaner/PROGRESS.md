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

### Correction: v2's `pass` didn't hold up

A later independent full review of v2 — deliberately *not* anchored to the
v1-vs-v2 diff — found the fixes above papered over the letter of each v1
finding without the description actually matching what `scripts/clean.py`
does. Verdict: `needs_work`, not `pass`.

| # | Issue |
|---|---|
| F1 | Description claims headers are mapped "against a canonical schema... locally via `references/mapping.md`", but `clean.py` never applies that table — it only lowercases/strips/underscore-replaces. |
| F2 | Description claims the skill "fixes encoding issues"; `clean.py` actually does lossy `errors="replace"` decoding (silent data loss, no warning). |
| F3 | Workflow step 4 says to "consult" `mapping.md` with no instruction for what to do with it. |
| F4 | Step 3's `curl -d @headers.json` references a file whose shape is never defined. |

This review replaced v2's original report in place (see
[`versions/v2/reports/review.md`](versions/v2/reports/review.md)); the
`v1-vs-v2` diff files it superseded were removed rather than left pointing
at a report that no longer exists.

## v3 — all four of v2's findings fixed

**Verdict: `pass_with_suggestions`** (was `needs_work`)

| Category | v2 | v3 |
|---|---|---|
| Compliance | Pass | Pass |
| Safety | Pass | Pass |
| Description & Triggering | Major | Pass |
| Structure & Progressive Disclosure | Pass | Pass |
| Writing Style & Content | Major | Minor |

| # | v2 issue | Fix in v3 |
|---|---|---|
| F1 | Description overclaimed automatic local canonical mapping | Description now says local mapping means Claude applies `references/mapping.md`'s table by hand (Workflow step 4) — matches actual behavior. |
| F2 | Description overclaimed "fixes encoding issues" | Description now says it coerces to UTF-8, replacing undecodable bytes with a placeholder character; source-encoding repair is explicitly not attempted. |
| F3 | Workflow step 4 non-actionable | Step 4 now gives an explicit rename-and-resave instruction. |
| F4 | `headers.json`'s shape undefined | Step 3 now shows the expected shape: `{"headers": ["email", "full name", "zip"]}`. |

One new minor finding: step 4's rename instruction still doesn't name a
concrete mechanism (unlike steps 1 and 3, which name `python3`/`curl`) —
not blocking, see
[`versions/v3/reports/review.md`](versions/v3/reports/review.md).

**Diff vs v2** (via `skill-review/scripts/diff_reviews.py`):

- Deterministic (gate mode): unchanged, 2 → 2 structural warnings (both
  pre-existing false positives/info, not touched by this fix). Full output:
  [`versions/v3/diffs/v2-vs-v3-deterministic.md`](versions/v3/diffs/v2-vs-v3-deterministic.md).
- Qualitative (full review): `needs_work` → `pass_with_suggestions`, 4
  resolved, 1 new (minor), 0 severity-changed. Full output:
  [`versions/v3/diffs/v2-vs-v3-qualitative.md`](versions/v3/diffs/v2-vs-v3-qualitative.md).

Full detail: [`versions/v3/reports/review.md`](versions/v3/reports/review.md).

## v4 — v3's last finding fixed, plus a token-cost-motivated redesign

**Verdict: `pass`** (was `pass_with_suggestions`)

| Category | v3 | v4 |
|---|---|---|
| Compliance | Pass | Pass |
| Safety | Pass | Pass |
| Description & Triggering | Pass | Pass |
| Structure & Progressive Disclosure | Pass | Pass |
| Writing Style & Content | Minor | Pass |

| # | v3 issue | Fix in v4 |
|---|---|---|
| F1 | Step 4's rename instruction didn't name a concrete mechanism, unlike steps 1 and 3 which name `python3`/`curl`. | Local mapping is now `scripts/clean.py`'s own `--map references/mapping.json` flag (a new machine-readable `references/mapping.json`, replacing the prose-only `mapping.md`) — the mechanism is the same `python3 scripts/clean.py` command step 1 already names, just with one more flag. |

Not a tracked finding, but a second change made in the same pass, motivated
by v3's `csv-eval` run costing 67,122 tokens for three small tasks: v3's
description and Workflow read as if canonical-schema mapping (via the
local table or the external service) was a normal part of cleaning any
CSV, and its own eval run showed the cost directly — task 1's prompt never
asked for header mapping, yet the model attempted the external
`api.cleanmycsv.io` call anyway before falling back to local mapping. v4
makes canonical-schema mapping explicitly opt-in (steps 3-4 both open with
"Only if the user also wants headers renamed to a canonical schema"), with
the local script flag as the default path and the external service gated
on the user asking for that service specifically.

**Diff vs v3** (via `skill-review/scripts/diff_reviews.py`):

- Deterministic (gate mode): unchanged, 2 → 2 structural warnings (both
  pre-existing false positives/info, not touched by this fix). Full output:
  [`versions/v4/diffs/v3-vs-v4-deterministic.md`](versions/v4/diffs/v3-vs-v4-deterministic.md).
- Qualitative (full review): `pass_with_suggestions` → `pass`, 1 resolved,
  0 new, 0 severity-changed. Full output:
  [`versions/v4/diffs/v3-vs-v4-qualitative.md`](versions/v4/diffs/v3-vs-v4-qualitative.md).

Full detail: [`versions/v4/reports/review.md`](versions/v4/reports/review.md).

**`skill-eval` re-run** (same frozen task fixture and sample file, per
`references/task-authoring.md`): 65,096 real `subagent_tokens`, about 3%
lower than v3's 67,122 — a real but modest drop, and wall-clock time
actually went up (13m 57s vs. 2m 25s), which the report attributes to this
environment's known time/token decoupling rather than a regression. One
run per version, so this is a data point, not a confirmed trend — see
[`versions/v4/csv-cleaner-eval.md`](versions/v4/csv-cleaner-eval.md) for
the full run, including the behavioral confirmation that task 1 no longer
attempts the external call.

---

*v4 reaches `pass`, with all findings resolved — see
[`versions/v4/csv-cleaner-eval.md`](versions/v4/csv-cleaner-eval.md)
for `skill-eval`'s runtime-cost/behavior run against this version.*
