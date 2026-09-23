# skill-eval

A Claude Agent Skill that runs another skill against real tasks and
reports what it actually cost — model used, token count, wall-clock time —
alongside a short qualitative judgment of how the run went. Where
`skill-review` asks "is this skill well-written?" without executing
anything, `skill-eval` asks "does this skill do its job well, at what
cost?" by actually running it.

This `README.md` is for **human developers** maintaining this skill in
version control. `SKILL.md` is the **model-facing** file Claude actually
reads when the skill triggers — don't merge the two; keep this one focused
on repo/dev concerns and keep `SKILL.md` focused on instructions to the
model.

## Status

All four Workflow steps are implemented: gate-check (deterministic +
qualitative), run the target skill per model, write a judgment, render the
table. See [`EXAMPLE-RESULTS.md`](EXAMPLE-RESULTS.md) for a real,
end-to-end run against `skill-review` itself — not a synthetic example.

The "Number of Tokens" column is a real, measured value: Workflow step 2
reads `subagent_tokens` straight off the `Agent` tool's own return
metadata for each per-model run, no self-reporting or estimation
involved. This was corrected from an earlier, more pessimistic design —
see [`references/token-capture.md`](references/token-capture.md) for the
investigation and `EXAMPLE-RESULTS.md` for the run that first surfaced the
correction.

Remaining work is tracked by this repo's open `skill-eval:`-prefixed
issues (docs, further regression coverage, etc.) — see
[`CHANGELOG.md`](CHANGELOG.md) for what's landed so far.

## Running it end-to-end

There's no script for the full run — `skill-eval` is a Claude Agent
Skill, not a CLI tool, precisely because writing a judgment and
orchestrating a subagent per model both need a model in the loop (see
"Why not fold this into skill-review?" below for the flip side of that).
Ask a Claude session that has `skill-eval` available something like:

```
Evaluate skill-review's runtime cost and behavior.
```

or, to compare models for this run only:

```
Evaluate the csv-cleanup skill on sonnet and haiku.
```

`skill-eval/SKILL.md`'s Workflow then runs: the two-stage gate check
against the target skill → one subagent per resolved model, run against
`tests/fixtures/tasks/<skill-name>.yaml` → a judgment per run → the final
table, saved as `<skill-name>-eval.md`. If no task fixture exists yet for
the target skill, it stops and asks before inventing one on the fly — see
"Adding a task fixture" below. See
[`EXAMPLE-RESULTS.md`](EXAMPLE-RESULTS.md) for exactly what a real run of
this looks like, output included.

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

`tests/fixtures/tasks/skill-review.yaml` is the one worked example so
far; skim it alongside `task-authoring.md` for a concrete template.

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
- **The version of `skill-review` doing the gate check.** Workflow step 1
  runs whatever `skill-review` is checked out at the time — if
  `skill-review`'s own checks or rubric changed between two `skill-eval`
  runs (see its `CHANGELOG.md`), a different gate-check outcome could
  reflect that, not a change in the skill actually being evaluated. Note
  `skill-review`'s `metadata.version` (or the commit) alongside the
  results if you're comparing runs done weeks apart.
- **Judge variance, as a known limitation, not something to control
  for.** The "Claude's Judgment" column is a single freeform LLM-judge
  pass with the run-to-run variance that pattern has (see `SURVEY.md`'s
  "left uncovered" section) — `skill-eval` has no self-consistency
  mechanism of its own yet (unlike `skill-review`'s qualitative pass, see
  its `reconcile_reviews.py`). Treat a single run's judgment as
  indicative, not authoritative, especially for a close call.

## Why not fold this into skill-review?

`skill-review` is deliberately static — it never executes the skill it
reviews, which is what keeps its deterministic gate mode fast, safe for CI,
and free of any model-execution cost or risk. `skill-eval`'s entire job is
the opposite: actually running the target skill. Keeping them separate
keeps `skill-review`'s scope narrow and its gate mode's guarantees
(deterministic, no model call) intact, while `skill-eval` reuses that gate
mode as its own first step rather than re-implementing static checks.

## Local testing

```bash
pip install -r requirements.txt
python3 tests/run_regression.py
```

Covers what's actually deterministic/scriptable: the gate-check signal
`structural_check.py` produces for a known-Blocker fixture and a clean
one, `models_config.yaml`'s shape, `render_report.py`'s table rendering
(including pipe-escaping and the zero-runs case), a self-check, and
packaging. Deliberately excludes anything requiring a live model call
(task execution, judgment-writing, `skill-review`'s own qualitative full
review mode) — same reasoning `skill-review`'s own suite uses.
`.github/workflows/tests.yml` runs this same command on every push and PR.

## Repository layout

```
skill-eval/
├── SKILL.md               # Model-facing instructions (required)
├── README.md               # This file — human/dev-facing
├── CHANGELOG.md             # Version history
├── SURVEY.md                 # Existing eval/cost-tracking tools, adopt/adapt/reject
├── EXAMPLE-RESULTS.md          # Real end-to-end run against skill-review
├── requirements.txt             # Python deps (PyYAML)
├── .gitignore
├── scripts/
│   └── render_report.py           # Workflow step 4: renders the final table
├── references/
│   ├── models_config.yaml          # Editable default_models list (see above)
│   ├── task-authoring.md            # tests/fixtures/tasks/<skill-name>.yaml format
│   └── token-capture.md              # Why "Number of Tokens" is a real measured value
└── tests/
    ├── run_regression.py               # This skill's own regression suite
    └── fixtures/
        ├── render-report-sample.json      # Fixed input for render_report.py tests
        ├── render-report-empty.json        # Zero-runs edge case
        └── tasks/
            └── skill-review.yaml             # The one real task set authored so far
```
