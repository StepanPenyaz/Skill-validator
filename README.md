# Skill Validator

[![Tests](https://github.com/StepanPenyaz/Skill-validator/actions/workflows/tests.yml/badge.svg)](https://github.com/StepanPenyaz/Skill-validator/actions/workflows/tests.yml)

A repo of Claude Agent Skills, packaged and validated with shared tooling.

## Layout

```
.
├── .github/workflows/
│   └── tests.yml           # Runs each skill's own regression suite on push/PR
├── scripts/
│   └── package_skill.py    # Shared packager for every skill below
├── skill-review/           # Statically reviews other skills for compliance/quality
└── skill-eval/              # Runs another skill against real tasks and reports its cost
```

Each skill is a top-level directory containing its own `SKILL.md`. Dev-only
content (tests, fixtures, caches) lives under that skill's `tests/`
directory and must never ship in the packaged bundle.

## skill-review

The one skill currently in this repo. It statically reviews *other* Claude
Agent Skills — `SKILL.md` plus bundled resources — against best-practice
conventions (metadata, structure, permissions/tool usage, security) and
produces a scored, actionable report, without ever executing the skill
being reviewed.

It has two officially supported entry points — pick based on what you
need, they're not a "lite" version and a "full" version of the same thing:

- **Gate mode** — deterministic, no model call, safe for CI:

  ```bash
  python3 skill-review/scripts/structural_check.py <path-to-a-skill>          # raw JSON
  python3 skill-review/scripts/generate_static_report.py <path-to-a-skill>    # human-readable Markdown
  ```

- **Full review mode** — the complete rubric-based review, requires a
  Claude session (there's no script for this half): ask Claude to "review
  this skill" / "audit this SKILL.md" / similar, pointing at the skill's
  path. Follows `skill-review/SKILL.md`'s Workflow.

See [`skill-review/README.md`](skill-review/README.md) for the full
picture — the table comparing both modes, what each check validates, more
usage examples (including diffing two versions of a skill and self-
consistency across repeated reviews), and how to retune a check's severity
via `skill-review/references/severity_config.yaml` without touching code.

Its own regression suite (`skill-review/tests/run_regression.py`) runs
every fixture under `skill-review/tests/fixtures/` and asserts the result
matches what's documented — this is what `.github/workflows/tests.yml`
runs on every push and PR.

## skill-eval

Runs *another* skill against real tasks and reports what it actually
cost — model used, token count, wall-clock time — alongside a short
qualitative judgment of how the run went. Where `skill-review` asks "is
this skill well-written?" without executing anything, `skill-eval` asks
"does this skill do its job well, at what cost?" by actually running it.
It runs `skill-review` against the target skill first and refuses to
proceed if that comes back blocked.

```
Evaluate skill-review's runtime cost and behavior.
```

— asked in a Claude session with `skill-eval` available, pointing at a
target skill's directory (and, optionally, which models to compare). See
[`skill-eval/EXAMPLE-RESULTS.md`](skill-eval/EXAMPLE-RESULTS.md) for a
real run's output, and [`skill-eval/README.md`](skill-eval/README.md) for
the full picture — how to add a task fixture for a new target skill, what
has to stay constant for two runs' numbers to be comparable, and a survey
of existing eval/cost-tracking tools (`skill-eval/SURVEY.md`) explaining
why this is mostly custom-built rather than adopting one of them
wholesale.

Its own regression suite (`skill-eval/tests/run_regression.py`) covers
what's actually deterministic/scriptable — same convention as
`skill-review`'s — and also runs on every push and PR.

## Adding a new skill

- Put it at `<repo-root>/<skill-name>/`, with `SKILL.md` at its root.
- Put its test fixtures under `<skill-name>/tests/fixtures/`, not loose at
  the skill root — fixture skills (which carry their own `SKILL.md`) are
  otherwise indistinguishable from a packaging violation.
- Package it with the shared tool, not a per-skill copy:

  ```bash
  python3 scripts/package_skill.py <skill-name> [output-dir]
  ```

  This excludes `tests/`, `.git`, `__pycache__`, `dist`, `node_modules`,
  and `.pytest_cache`, then refuses to write the bundle unless exactly one
  `SKILL.md` survives.
- If the new skill needs its own deterministic compliance checker (like
  `skill-review/scripts/structural_check.py`), keep the same exclude list
  in sync — that script must stay self-contained (it also runs when the
  skill is distributed standalone, without the rest of this repo), so it
  can't import `scripts/package_skill.py` directly.
- If the new skill has its own test fixtures, give it a
  `<skill-name>/tests/run_regression.py` (see `skill-review/tests/
  run_regression.py` for the pattern: plain assertions over subprocess
  calls to the skill's own CLI scripts, no framework needed) and add a step
  for it in `.github/workflows/tests.yml`, alongside skill-review's.
