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

Scaffolding only right now (see `SKILL.md`'s stubbed `# Workflow` section).
No working behavior yet. Building out in the order tracked by this repo's
open `skill-eval:`-prefixed issues:

1. Run `skill-review`'s gate mode against the target skill first; stop on
   any breaking (Blocker) finding — no point measuring the cost of a skill
   that wouldn't even ship.
2. Run the target skill against a fixed task-fixture set, once per model
   in a configurable model list, capturing model/tokens/time per run.
3. Write a short qualitative judgment per run (not a numeric score).
4. Render one table: `Model Used | Number of Tokens | Time Spent | Claude's
   Judgment`.

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
├── references/          # Empty for now — task-fixture format, models config, etc.
└── tests/
    └── fixtures/         # Empty for now
```
