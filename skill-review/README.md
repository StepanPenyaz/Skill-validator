# skill-review

A Claude Agent Skill that statically reviews other skills (`SKILL.md` +
bundled resources) against best-practice conventions and produces a scored,
actionable report.

This `README.md` is for **human developers** maintaining this skill in
version control. `SKILL.md` is the **model-facing** file Claude actually
reads when the skill triggers — don't merge the two; keep this one focused
on repo/dev concerns (setup, testing, release process) and keep `SKILL.md`
focused on instructions to the model.

## What it does

Given a path to a skill directory, produces:
- `<skill-name>-review.json` — machine-readable scorecard (category scores,
  severity-tagged findings, suggested rewrites). Schema in
  `references/schema.md`.
- `<skill-name>-review.md` — human-readable summary generated from the JSON.

Review covers four categories: compliance (hard frontmatter/packaging
rules), structure & progressive disclosure, description & triggering
quality, and writing style & content quality (see `references/rubric.md`
for the full rubric).

## Repository layout

```
skill-review/
├── SKILL.md                      # Model-facing instructions (required)
├── README.md                     # This file — human/dev-facing
├── CHANGELOG.md                  # Version history
├── requirements.txt              # Python deps for scripts/
├── .gitignore
├── scripts/
│   └── structural_check.py       # Deterministic compliance/structure checker
├── references/
│   ├── rubric.md                 # Qualitative scoring rubric
│   └── schema.md                 # JSON output schema for the review report
└── tests/
    └── fixtures/
        ├── good-skill/           # Minimal skill that should pass cleanly
        │   └── SKILL.md
        └── bad-skill/            # Minimal skill with known issues, for regression testing
            └── SKILL.md
```

`tests/` is dev-only: `structural_check.py` and `../scripts/package_skill.py`
both exclude it, so fixture skills (each with their own `SKILL.md`) never
count against or ship in the packaged `skill-review` bundle. Any new skill
added to this repo should follow the same convention.

## Local testing

```bash
pip install -r requirements.txt

# Should report zero compliance errors and zero structural warnings:
python3 scripts/structural_check.py tests/fixtures/good-skill

# Should report specific known issues (see tests/fixtures/bad-skill/SKILL.md
# comments for what each one is testing):
python3 scripts/structural_check.py tests/fixtures/bad-skill

# Should report zero compliance errors for skill-review itself, even though
# the fixtures above each carry their own SKILL.md under tests/:
python3 scripts/structural_check.py .
```

`structural_check.py` only prints JSON — it has no side effects and never
modifies the skill under review. Use it as a quick sanity check before
running the full qualitative review (which requires Claude to read the
skill and consult `references/rubric.md`).

## Versioning

Version lives in two places that must stay in sync:
- `SKILL.md` frontmatter → `metadata.version`
- `CHANGELOG.md` → top entry

Bump on any change to `SKILL.md` instructions, the rubric, the JSON schema,
or `structural_check.py`'s check logic — anything that could change what a
prior review run would have reported. Follow semver: patch for wording/typo
fixes that don't change verdicts, minor for new checks or rubric criteria
(backward compatible — old reports remain valid, just less thorough),
major for schema-breaking changes to the JSON output.

## Packaging for distribution

This repo hosts more than one skill, so packaging is a shared, repo-level
tool rather than something each skill vendors its own copy of:

```bash
python3 ../scripts/package_skill.py . [output-dir]
```

It zips the skill into `<output-dir>/skill-review.skill` (default
`../dist/`), excluding `tests/` and other dev-only content, and refuses to
write the bundle if anything other than exactly one `SKILL.md` survives
that exclusion — the same rule `structural_check.py` enforces, so a clean
`structural_check.py .` run should always be packageable. Any new skill
added to this repo should package with the same script rather than adding
a per-skill copy.

## Using this in the Claude Code Skill Evaluation pipeline

This skill is the static/diagnostic layer of the broader evaluation plan —
it runs before any runtime execution benchmark, and its JSON output is
designed to be diffed across skill versions (see `overall_verdict` and
`category_scores` in `references/schema.md`) as a leading indicator ahead
of full A/B runtime comparisons.
