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

Building out in the order tracked by this repo's open `skill-eval:`-prefixed
issues. So far:

1. **Done.** Run `skill-review` against the target skill first — its
   deterministic gate mode, then (if that passes) its qualitative full
   review mode too — and stop on any blocking result from either. No
   point measuring the cost of a skill that wouldn't even ship, or that
   has a blocking problem only a model reading it would catch.
2. **In progress.** Run the target skill against a fixed task-fixture set,
   once per model in a configurable model list (see "Models configuration"
   below), capturing model/tokens/time per run.
3. Write a short qualitative judgment per run (not a numeric score).
4. Render one table: `Model Used | Number of Tokens | Time Spent | Claude's
   Judgment`.

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

## Repository layout

```
skill-eval/
├── SKILL.md           # Model-facing instructions (required)
├── README.md           # This file — human/dev-facing
├── CHANGELOG.md         # Version history
├── requirements.txt     # Python deps for scripts/ (once any exist)
├── .gitignore
├── scripts/             # Empty for now
├── references/
│   ├── models_config.yaml  # Editable default_models list (see above)
│   ├── task-authoring.md   # tests/fixtures/tasks/<skill-name>.yaml format
│   └── token-capture.md    # Why "Number of Tokens" is a labeled estimate
└── tests/
    └── fixtures/         # Empty for now — no task set written yet for any skill
```
