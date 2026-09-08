# Skill Validator

A repo of Claude Agent Skills, packaged and validated with shared tooling.

## Layout

```
.
├── scripts/
│   └── package_skill.py   # Shared packager for every skill below
├── skill-review/          # Statically reviews other skills for compliance/quality
└── <future-skill>/
```

Each skill is a top-level directory containing its own `SKILL.md`. Dev-only
content (tests, fixtures, caches) lives under that skill's `tests/`
directory and must never ship in the packaged bundle.

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
