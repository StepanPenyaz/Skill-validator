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

One thing worth knowing before relying on the "Number of Tokens" column:
that demo found the token-count design in
[`references/token-capture.md`](references/token-capture.md) is more
pessimistic than it needs to be for at least some execution paths — see
that file's note and `EXAMPLE-RESULTS.md` for the details. Treat the
token column as directionally useful, and check which of the two
mechanisms (measured vs. estimated) actually produced a given number,
until that gets fully resolved.

Remaining work is tracked by this repo's open `skill-eval:`-prefixed
issues (docs, further regression coverage, etc.) — see
[`CHANGELOG.md`](CHANGELOG.md) for what's landed so far.

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
│   └── token-capture.md              # Why "Number of Tokens" is (usually) an estimate
└── tests/
    ├── run_regression.py               # This skill's own regression suite
    └── fixtures/
        ├── render-report-sample.json      # Fixed input for render_report.py tests
        ├── render-report-empty.json        # Zero-runs edge case
        └── tasks/
            └── skill-review.yaml             # The one real task set authored so far
```
