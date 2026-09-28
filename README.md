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
└── skill-eval/             # Statically reviews a skill AND runs it against real tasks, reporting cost
```

Each skill is a top-level directory containing its own `SKILL.md`. Dev-only
content (tests, fixtures, caches) lives under that skill's `tests/`
directory and must never ship in the packaged bundle.

## skill-eval

The one skill currently in this repo. It statically reviews a Claude Agent
Skill's `SKILL.md` + bundled resources against best-practice conventions
(metadata, structure, permissions/tool usage, security) **and** runs it
against real tasks, reporting what it actually cost — model used, token
count, wall-clock time — alongside a short qualitative judgment of how the
run went. It answers "is this skill well-written?" and "does this skill do
its job well, at what cost?" in one pipeline; running the target skill
happens only after the static review passes (see `skill-eval/SKILL.md`'s
Purpose).

The static-review half has two officially supported entry points — pick
based on what you need, they're not a "lite" version and a "full" version
of the same thing:

- **Gate mode** — deterministic, no model call, safe for CI, and usable
  completely standalone:

  ```bash
  python3 skill-eval/scripts/structural_check.py <path-to-a-skill>          # raw JSON
  python3 skill-eval/scripts/generate_static_report.py <path-to-a-skill>    # human-readable Markdown
  ```

- **Full review mode** — the complete rubric-based review, requires a
  Claude session (there's no script for this half): ask Claude to "review
  this skill" / "audit this SKILL.md" / similar, pointing at the skill's
  path. Follows `skill-eval/SKILL.md`'s Workflow step 1.

To also run the target skill and get a cost/behavior report, ask something
like:

```
Evaluate skill-eval's own runtime cost and behavior.
```

— asked in a Claude session with `skill-eval` available, pointing at a
target skill's directory (and, optionally, which models to compare). Giving
two skill directories (an old/new version pair) produces a comparative
report instead of two separate ones.

See [`skill-eval/README.md`](skill-eval/README.md) for the full picture —
the table comparing gate mode and full review mode, what each check
validates, how to retune a check's severity via
`skill-eval/references/severity_config.yaml` without touching code, how to
add a task fixture for a new target skill, what has to stay constant for
two runs' numbers to be comparable, and a survey of existing eval/
cost-tracking tools (`skill-eval/SURVEY.md`) explaining why this is mostly
custom-built rather than adopting one of them wholesale. See
[`skill-eval/EXAMPLE-RESULTS.md`](skill-eval/EXAMPLE-RESULTS.md) for a real
run's output.

Its own regression suite (`skill-eval/tests/run_regression.py`) covers
what's actually deterministic/scriptable — both the static-review checks
and the report-rendering logic — and runs on every push and PR via
`.github/workflows/tests.yml`.

`skill-eval` absorbed a former separate `skill-review` skill; see
`skill-eval/CHANGELOG.md`'s merge entry and
`skill-eval/CHANGELOG-skill-review-history.md` for that history.

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
  `skill-eval/scripts/structural_check.py`), keep the same exclude list
  in sync — that script must stay self-contained (it also runs when the
  skill is distributed standalone, without the rest of this repo), so it
  can't import `scripts/package_skill.py` directly.
- If the new skill has its own test fixtures, give it a
  `<skill-name>/tests/run_regression.py` (see `skill-eval/tests/
  run_regression.py` for the pattern: plain assertions over subprocess
  calls to the skill's own CLI scripts, no framework needed) and add a step
  for it in `.github/workflows/tests.yml`, alongside skill-eval's.
