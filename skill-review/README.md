# skill-review

A Claude Agent Skill that statically reviews other skills (`SKILL.md` +
bundled resources) against best-practice conventions and produces a scored,
actionable report — before the skill is published, as a pre-check in a
skill-evaluation pipeline, or when comparing two versions of a skill.

This `README.md` is for **human developers** maintaining this skill in
version control. `SKILL.md` is the **model-facing** file Claude actually
reads when the skill triggers — don't merge the two; keep this one focused
on repo/dev concerns (setup, testing, release process) and keep `SKILL.md`
focused on instructions to the model.

## Purpose

Publishing a broken or poorly-written skill is easy to do by accident —
malformed frontmatter, a description that under-triggers, an orphaned
script nobody points to, a hardcoded secret. `skill-review` catches all of
that **without ever executing the skill being reviewed**: it only reads
`SKILL.md` and its bundled resources and judges them against known
conventions. That keeps it fast, deterministic where possible, and clearly
separates "this skill is malformed / poorly written" from "this skill
performs badly in practice" (that second question needs actual runs — see
the `skill-creator` skill for that if it's available).

## Two layers

1. **Linter** (deterministic) — `scripts/structural_check.py` reads a skill
   directory and computes hard facts and compliance errors: no judgment, no
   false positives from misreading intent, same input always produces the
   same output.
2. **Static Quality** (qualitative) — a model reads the skill itself against
   `references/rubric.md` and turns judgment calls (is the description
   pushy enough, does the writing explain *why* instead of barking MUST/
   NEVER, is the skill overfit to one example) into scored findings with
   concrete rewrites. Driven by `SKILL.md` Steps 3-5.

Never skip straight to writing a review from the Linter's output alone —
several of its checks are only *candidate* signals (an orphaned-looking
file, a phrase that resembles prompt injection) that need confirmation
against the real text before they're reported as findings.

## What it validates

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

## Examples of use

```bash
pip install -r requirements.txt
```

**1. Raw JSON from the Linter** — parsed frontmatter, `compliance_errors`,
`structural_warnings`, `metrics`, and a structured `findings` array:

```bash
python3 scripts/structural_check.py tests/fixtures/bad-skill
```

```json
{
  "compliance_errors": [
    "Name 'BadSkill_v2' is not kebab-case (lowercase letters, digits, hyphens only). Rename to lowercase letters, digits, and hyphens only.",
    "Possible hardcoded secret/credential (openai_style_key), value redacted (sk-A…redacted…). Remove the hardcoded credential; ..."
  ],
  "findings": [
    {"category": "Metadata", "severity": "Blocker", "issue": "Name 'BadSkill_v2' is not kebab-case ...", "suggestion": "Rename to lowercase ...", "location": null},
    ...
  ]
}
```

**2. Human-readable Markdown report** — one table per category, one row per
occurrence, with a suggested fix (still purely mechanical — no judgment):

```bash
python3 scripts/generate_static_report.py tests/fixtures/bad-skill
# or write it to a file instead of stdout:
python3 scripts/generate_static_report.py tests/fixtures/bad-skill --out report.md
```

```markdown
# Static Check Report: BadSkill_v2

2 blocker(s), 15 warning(s), 2 info-level suggestion(s).

## Metadata

| What's Wrong | Severity | Suggested Fix |
|---|---|---|
| Name 'BadSkill_v2' is not kebab-case ... | Blocker | Rename to lowercase letters, digits, and hyphens only. |
...

## Security

| What's Wrong | Severity | Suggested Fix |
|---|---|---|
| `SKILL.md:35` — Possible hardcoded secret/credential ... | Blocker | Remove the hardcoded credential; ... |
...
```

**3. Full qualitative review** (`<skill-name>-review.json` + `.md`, with
rubric-based scoring and concrete rewrites) isn't a script — it's Claude
following `SKILL.md` Steps 1-5, using the Linter's output above as its
starting facts.

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

## Repository layout

```
skill-review/
├── SKILL.md                      # Model-facing instructions (required)
├── README.md                     # This file — human/dev-facing
├── CHANGELOG.md                  # Version history
├── requirements.txt              # Python deps for scripts/
├── .gitignore
├── scripts/
│   ├── structural_check.py       # Deterministic compliance/structure/security checker
│   └── generate_static_report.py # Renders the checker's findings as a Markdown report
├── references/
│   ├── rubric.md                 # Qualitative scoring rubric
│   ├── schema.md                 # JSON output schema for the review report
│   ├── preferred-structure.md    # Recommended (not required) SKILL.md section outline
│   └── severity_config.yaml      # Editable check_id -> severity policy (see above)
└── tests/
    └── fixtures/
        ├── good-skill/           # Minimal skill that should pass cleanly
        │   └── SKILL.md
        └── bad-skill/            # Minimal skill with known issues, for regression testing
            ├── SKILL.md
            └── scripts/helper.py
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
modifies the skill under review. Use it (or `generate_static_report.py` for
the human-readable version) as a quick sanity check before running the full
qualitative review, which requires Claude to read the skill and consult
`references/rubric.md`.

## Versioning

Version lives in two places that must stay in sync:
- `SKILL.md` frontmatter → `metadata.version`
- `CHANGELOG.md` → top entry

Bump on any change to `SKILL.md` instructions, the rubric, the JSON schema,
`severity_config.yaml`, or `structural_check.py`'s check logic — anything
that could change what a prior review run would have reported. Follow
semver: patch for wording/typo fixes that don't change verdicts, minor for
new checks, rubric criteria, or severity retuning (backward compatible —
old reports remain valid, just less/more thorough), major for
schema-breaking changes to the JSON output.

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
