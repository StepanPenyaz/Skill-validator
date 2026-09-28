# skill-eval

A Claude Agent Skill that statically reviews another skill's `SKILL.md` +
bundled resources against best-practice conventions **and** runs it against
real tasks to report what it actually cost — model used, token count,
wall-clock time — alongside a short qualitative judgment of how the run
went. It answers "is this skill well-written?" and "does this skill do its
job well, at what cost?" in one pipeline (see `SKILL.md`'s Purpose for why
these two used to be separate skills and aren't anymore).

This `README.md` is for **human developers** maintaining this skill in
version control. `SKILL.md` is the **model-facing** file Claude actually
reads when the skill triggers — don't merge the two; keep this one focused
on repo/dev concerns and keep `SKILL.md` focused on instructions to the
model.

## Status

`skill-eval` absorbed the former `skill-review` skill's static-review layer
(deterministic gate mode + qualitative full review mode, including
self-consistency and version-diffing) as of the merge documented in
`CHANGELOG.md`; `CHANGELOG-skill-review-history.md` keeps that skill's own
version history as a historical record. All Workflow steps are implemented:
static review (gate mode + full review mode), run the target skill per
model, write a judgment, render the table. See
[`EXAMPLE-RESULTS.md`](EXAMPLE-RESULTS.md) for a real, end-to-end run of the
pre-merge pipeline against `skill-review` itself — not a synthetic example
(kept as historical record; see the note at its top).

The "Number of Tokens" column is a real, measured value: Workflow step 2
reads `subagent_tokens` straight off the `Agent` tool's own return
metadata for each per-model run, no self-reporting or estimation
involved — see [`references/token-capture.md`](references/token-capture.md).

## Two entry points in the static-review layer: gate mode and full review mode

Pick based on what's actually being asked for; neither is a lesser version
of the other — see `SKILL.md`'s Decision Guidelines for the full
"full pipeline vs. gate-mode-only vs. static-review-only" decision.

1. **Gate mode** (deterministic) — `scripts/structural_check.py` /
   `scripts/generate_static_report.py`, plus `scripts/diff_reviews.py` when
   given two skill directories. No model call: hard facts and compliance
   errors only — no judgment, no false positives from misreading intent,
   same input always produces the same output, safe to run unattended, and
   usable completely standalone (independent of the rest of this skill's
   pipeline). This is the **Linter** layer.
2. **Full review mode** (qualitative) — `SKILL.md` Workflow step 1b: Claude
   runs gate mode first, then reads the skill itself against
   `references/rubric.md` and turns judgment calls (is the description
   pushy enough, does the writing explain *why* instead of barking
   MUST/NEVER, is the skill overfit to one example) into scored findings
   with concrete rewrites. This is the **Static Quality** layer. Requires a
   Claude session — there's no script for this half.

|  | Gate mode | Full review mode |
|---|---|---|
| Needs a model call? | No | Yes |
| Deterministic? | Yes — same input, same output | No — judgment varies run to run (see "Self-consistency" below) |
| Catches | Malformed frontmatter, hardcoded secrets, orphaned files, dangerous-looking patterns (as *candidates*, not verdicts) | Everything gate mode catches, **plus** writing quality, triggering strength, and whether a gate-mode candidate is an actual problem in context |
| Reach for it when | Wiring this into CI/a script; "just run the linter"; a quick pre-publish check | A human asks to review, audit, grade, or get feedback; a rewrite or rubric score is needed |

Self-consistency and `scripts/diff_reviews.py` are optional extensions
layered on top of these two entry points, not third and fourth modes of
their own — self-consistency runs full review mode N times;
`diff_reviews.py`'s two flavors diff either two gate mode runs or two full
review mode runs, and the diff itself is always deterministic (no new
model call), even for the full-review-mode flavor.

## What the static-review layer validates

**Metadata** — `name` present, kebab-case, ≤64 chars, matches the folder;
`description` present, ≤1024 chars, ≥8 words, has an explicit "when to use
this" trigger cue; `SKILL.md` filename is exactly `SKILL.md` (case-
sensitive); `metadata.version` is set.

**Structure** — SKILL.md body line count; `scripts/`/`references/`/`assets/`
presence and per-directory file counts; coverage against the recommended
section outline in `references/preferred-structure.md`; exactly one
`SKILL.md` would ship (packaging rule); bundled resource files are actually
pointed to from the body (not orphaned); large reference files (>300 lines)
have a table of contents; no hardcoded user-specific/absolute paths.

**Permissions & Tool Usage** — cross-checks `allowed-tools` frontmatter
against tool/MCP references in the body, flagging tools declared-but-unused
(over-provisioning) and tools used-but-undeclared (under-provisioning, can
fail at runtime).

**Security** — hardcoded secret/credential patterns (API keys, AWS keys,
JWT-shaped tokens, private key blocks, connection strings — reported as
hard Blockers); dangerous shell patterns (`rm -rf`, `curl | bash`, disabled
TLS verification, etc.); phrasing that resembles prompt-injection/
instruction-override language; phrasing that resembles a prohibited
high-risk action (entering credentials, permanent deletion, bypassing a
captcha); external hosts contacted but never named in the description;
every MUST/NEVER directive line, so the qualitative pass can judge whether
each one protects against real harm and deserves a companion enforcement
hook (a skill can't configure its own hooks — see `references/rubric.md`).

Every check above maps to a `check_id` in
[`references/severity_config.yaml`](references/severity_config.yaml) —
see **Retuning severity** below.

**Cost-conditional scanning** — the dangerous-shell-pattern, prompt-
injection, and undeclared-host scans only matter if the skill being checked
can actually act on what they'd find (run a shell command, fetch a URL), so
they're skipped by default for a skill whose `allowed-tools` and SKILL.md
body declare/reference no shell-executing or network-capable tool. The skip
is never silent: `metrics.security_scan` always records whether it happened
and why, and the Markdown report calls it out with a blockquote note.
Hardcoded-secret and prohibited-action-phrase scanning are never skipped —
those matter regardless of the skill's own tool access. Pass
`--force-security-scan` to either script to run the full scan anyway.

## Self-consistency (qualitative layer)

The Static Quality pass is a single LLM read of the skill, which has
run-to-run variance — the same skill reviewed twice can land on different
severities, or catch a different borderline finding. For a routine review,
one pass is enough. For a higher-confidence review, `SKILL.md`'s Decision
Guidelines has Claude produce N independent qualitative passes
(`<skill-name>-review-run<N>.json`, N=3 by default) and reconcile them with
`scripts/reconcile_reviews.py`:

```bash
python3 scripts/reconcile_reviews.py <skill-name>-review-run1.json \
  <skill-name>-review-run2.json <skill-name>-review-run3.json
```

This is purely mechanical (like the Linter — no model call): it groups
findings across runs by `(category, location)`, reports each one's
agreement count and a consensus severity (ties broken toward the more
severe value), and recomputes `overall_verdict` from the reconciled
`category_scores` using the same derivation rule as a single run. A finding
that only 1 of 3 runs caught is kept, but marked unconfirmed rather than
presented with the same confidence as one all three runs agreed on — see
`tests/fixtures/consistency-runs/` for a worked example. See
[`references/schema.md`](references/schema.md)'s "Self-consistency" section
for the reconciler's output shape.

## Running the full pipeline end-to-end

There's no script for the full run (static review + per-model execution) —
that half of `skill-eval` needs a Claude session in the loop, since writing
a judgment and orchestrating a subagent per model both require a model. Ask
a Claude session that has `skill-eval` available something like:

```
Evaluate skill-eval's own runtime cost and behavior.
```

or, to compare models for this run only:

```
Evaluate the csv-cleanup skill on sonnet and haiku.
```

or, for the static-review layer alone (no execution, no cost table):

```
Review this skill: <path-to-a-skill>
```

`SKILL.md`'s Workflow then runs: static review (gate mode, then full review
mode unless the user only wanted gate mode) → one subagent per resolved
model, run against `tests/fixtures/tasks/<skill-name>.yaml` → a judgment
per run → the final table, saved as `<skill-name>-eval.md`. If no task
fixture exists yet for the target skill, it stops and asks before
inventing one on the fly — see "Adding a task fixture" below. See
[`EXAMPLE-RESULTS.md`](EXAMPLE-RESULTS.md) for what a real run of the full
pipeline looked like, output included (from before the merge, when the
static-review layer was invoked as a separate `skill-review` skill — the
underlying mechanics are unchanged).

## Models configuration

`references/models_config.yaml`'s `default_models` list (just `sonnet` out
of the box) is what step 2 tests against by default. Two ways to add more
models to a comparison:

- **Persistent**: edit `default_models` in that file — affects every
  future run, not just one.
- **One-off**: ask for extra models at invocation time (e.g. "also test
  this on haiku and opus") without editing the file — affects only that
  run.

Either way, step 2 spawns one `Agent`-tool subagent per model in the
resulting list, each given the same task and the same target skill — the
model is the only thing that varies between rows of the final table.

## Adding a task fixture for a new skill

`skill-eval` won't invent tasks for a target skill it doesn't already
have a fixture for — see `references/task-authoring.md` for the full
format and methodology; the short version:

1. Create `tests/fixtures/tasks/<skill-name>.yaml` with 3-5 `{id, prompt,
   source}` entries.
2. Pull a happy-path prompt from the target skill's own description/"When
   to Use" examples, at least one task that specifically exercises
   whatever a version's `CHANGELOG.md` entry actually changed (if you're
   about to compare two versions), and one "When NOT to Use" boundary
   case.
3. Treat the file as frozen once it's been used in a real comparison —
   see "Reproducibility" below for why.

`tests/fixtures/tasks/skill-review.yaml` and `tests/fixtures/tasks/csv-cleaner.yaml`
are the worked examples so far; skim one alongside `task-authoring.md` for
a concrete template.

## Reproducibility: what must stay constant

Two `skill-eval` runs' numbers are only comparable — most importantly,
comparing an old version of a skill against a new one — if these all
stayed the same between them:

- **The task fixture.** `tests/fixtures/tasks/<skill-name>.yaml` must be
  byte-identical across both runs. If the tasks differ, a cost or
  judgment difference could just be different tasks, not the thing you
  changed — this is the whole reason the fixture is a frozen file
  instead of an ad hoc prompt (see `references/task-authoring.md`).
- **The model list.** Comparing a `sonnet`-only run against a
  `sonnet`+`haiku` run isn't apples-to-apples — use the same
  `references/models_config.yaml` `default_models` (or the same explicit
  per-run override) for both.
- **The version of `skill-eval` doing the static review.** Workflow step 1
  runs whatever version of this skill's own `structural_check.py` and
  `references/rubric.md` are checked out at the time — if those changed
  between two `skill-eval` runs (see `CHANGELOG.md`), a different
  static-review outcome could reflect that, not a change in the skill
  actually being evaluated. Note this skill's `metadata.version` (or the
  commit) alongside the results if you're comparing runs done weeks apart.
- **Judge variance, as a known limitation, not something to control
  for.** The "Claude's Judgment" column is a single freeform LLM-judge
  pass with the run-to-run variance that pattern has (see `SURVEY.md`'s
  "left uncovered" section) — the cost/behavior layer has no
  self-consistency mechanism of its own yet (unlike the static-review
  layer's qualitative pass, see `reconcile_reviews.py` above). Treat a
  single run's judgment as indicative, not authoritative, especially for a
  close call.

## Retuning severity

Every check's severity (`Blocker` / `Warning` / `Info`) is looked up at run
time from [`references/severity_config.yaml`](references/severity_config.yaml)
by a stable `check_id` — it's not hardcoded in `structural_check.py`. To
change what any future validation run reports for a given check (for every
skill, not just one), edit that check's `severity` value in the YAML file
and re-run — no code changes needed:

```yaml
name_not_kebab_case: {what_is_wrong: "Frontmatter 'name' is not kebab-case.", severity: Blocker}
```

`Blocker` findings land in `compliance_errors`; `Warning`/`Info` land in
`structural_warnings`. If the file is missing, malformed, or missing a
`check_id` the code actually uses, both scripts fail fast with a clear
`fatal_error`/`Error:` message rather than silently using the wrong
severity or crashing with a raw traceback.

## Diffing across versions

```bash
# Gate mode diff: two skill directories, no model call.
python3 scripts/diff_reviews.py old_skill/ new_skill/

# Full review mode diff: two already-produced <skill-name>-review.json
# files - category_scores, overall_verdict, and severity changes on a
# finding that persists across versions. The diff itself is still
# deterministic, no new model call - full review mode only needs to have
# already produced both input files.
python3 scripts/diff_reviews.py old-review.json new-review.json
```

Both modes support `--markdown` (a human-readable table instead of JSON),
`--out <path>`, and `--fail-on-new` — exits 1 only if `<new>` introduces a
finding `<old>` didn't have, so a CI gate can block a PR on regressions it
actually introduced without also blocking on every pre-existing finding.
Mixing one directory and one `.json` file is rejected. See
`tests/fixtures/diff-old-skill/` + `diff-new-skill/` for a worked example of
the deterministic mode, and `tests/fixtures/version-diff/` for the
qualitative mode.

## Local testing

```bash
pip install -r requirements.txt
python3 tests/run_regression.py
```

Covers what's actually deterministic/scriptable: `structural_check.py`
against every fixture under `tests/fixtures/` (`good-skill`, `bad-skill`,
`clean-skill-with-tricky-patterns`), `reconcile_reviews.py` against
`consistency-runs`, `diff_reviews.py` against both `diff-old-skill`/
`diff-new-skill` and `version-diff`, `models_config.yaml`'s shape,
`render_report.py`'s table rendering (including pipe-escaping and the
zero-runs case), a self-check, and packaging. Deliberately excludes
anything requiring a live model call (task execution, judgment-writing,
the qualitative full review mode itself).
`.github/workflows/tests.yml` runs this same command on every push and PR.

## Repository layout

```
skill-eval/
├── SKILL.md                          # Model-facing instructions (required)
├── README.md                         # This file — human/dev-facing
├── CHANGELOG.md                      # Version history
├── CHANGELOG-skill-review-history.md # skill-review's version history (pre-merge, frozen)
├── SURVEY.md                         # Existing eval/cost-tracking tools, adopt/adapt/reject
├── EXAMPLE-RESULTS.md                # Real end-to-end run against skill-review (pre-merge)
├── requirements.txt                  # Python deps (PyYAML)
├── .gitignore
├── scripts/
│   ├── structural_check.py           # Deterministic compliance/structure/security checker (gate mode)
│   ├── generate_static_report.py     # Renders the checker's findings as a Markdown report
│   ├── reconcile_reviews.py          # Aggregates N independent qualitative review runs
│   ├── diff_reviews.py               # Diffs two skill directories or two review.json files
│   └── render_report.py              # Workflow step 4: renders the final cost/judgment table
├── references/
│   ├── rubric.md                     # Qualitative scoring rubric (full review mode)
│   ├── schema.md                     # JSON output schema for <skill-name>-review.json
│   ├── preferred-structure.md        # Recommended (not required) SKILL.md section outline
│   ├── severity_config.yaml          # Editable check_id -> severity policy (see above)
│   ├── models_config.yaml            # Editable default_models list
│   ├── task-authoring.md             # tests/fixtures/tasks/<skill-name>.yaml format
│   └── token-capture.md              # Why "Number of Tokens" is a real measured value
└── tests/
    ├── run_regression.py             # This skill's own regression suite
    └── fixtures/
        ├── good-skill/                       # Minimal skill that should pass cleanly
        ├── bad-skill/                        # Minimal skill with known issues, for regression testing
        ├── clean-skill-with-tricky-patterns/ # Legitimate skill that resembles bad signals
        ├── consistency-runs/                 # 3 synthetic independent review runs, for reconcile_reviews.py
        ├── diff-old-skill/ + diff-new-skill/ # A before/after pair, for diff_reviews.py's deterministic mode
        ├── version-diff/                     # A before/after pair of review.json files, for diff_reviews.py's qualitative mode
        ├── render-report-sample.json         # Fixed input for render_report.py tests
        ├── render-report-empty.json          # Zero-runs edge case
        └── tasks/                            # Task fixtures for Workflow step 2, one per target skill
```

`clean-skill-with-tricky-patterns` is the mirror image of `bad-skill`: `bad-
skill` proves the checker catches real defects (recall), while this fixture
proves it stays quiet on patterns that merely *look* like defects. See the
intro paragraph of its `SKILL.md` for the full list. If any check ever
starts flagging something in this fixture, that's a false-positive
regression in the checker, not a problem with the fixture.

`tests/` is dev-only: `structural_check.py` and `../scripts/package_skill.py`
both exclude it, so fixture skills (each with their own `SKILL.md`) never
count against or ship in the packaged `skill-eval` bundle.

## Versioning

Version lives in two places that must stay in sync:
- `SKILL.md` frontmatter → `metadata.version`
- `CHANGELOG.md` → top entry

Bump on any change to `SKILL.md` instructions, the rubric, the JSON schema,
`severity_config.yaml`, `structural_check.py`'s check logic, or the
Workflow's execution/reporting steps — anything that could change what a
prior run would have reported. Follow semver: patch for wording/typo fixes
that don't change verdicts, minor for new checks/criteria or additive
report fields, major for breaking changes to a JSON output shape or to how
the skill is invoked.

## Packaging for distribution

This repo hosts more than one skill, so packaging is a shared, repo-level
tool rather than something each skill vendors its own copy of:

```bash
python3 ../scripts/package_skill.py . [output-dir]
```

It zips the skill into `<output-dir>/skill-eval.skill` (default `../dist/`),
excluding `tests/` and other dev-only content, and refuses to write the
bundle if anything other than exactly one `SKILL.md` survives that
exclusion — the same rule `structural_check.py` enforces, so a clean
`structural_check.py .` run should always be packageable.
