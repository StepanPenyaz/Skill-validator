---
name: skill-review
description: Statically reviews a Claude Agent Skill's SKILL.md and bundled resources against best-practice conventions — frontmatter compliance, progressive disclosure and file structure, description/triggering strength, writing style (explained reasoning vs. rigid MUST/NEVER directives), overfitting, and safety. Produces both a machine-readable JSON scorecard and a human-readable markdown report, with a concrete suggested rewrite for every flagged issue. Use this whenever the user asks to review, audit, lint, validate, critique, grade, or get feedback on a skill or a SKILL.md file — before publishing a new skill, as a pre-check in a skill-evaluation pipeline, or when comparing two skill versions. Trigger even on casual phrasing like "check this skill", "is this SKILL.md any good", or "what's wrong with my skill" without the user saying "validate" explicitly.
metadata:
  version: "1.2.0"
  maintained_by: "Claude Code Skill Evaluation project"
---

# Skill Review

A static reviewer for Claude Agent Skills. It never executes the skill being
reviewed — it only reads the `SKILL.md` and bundled resources and judges
them against known best practices. This makes it fast and deterministic
where possible, and clearly separates "this skill is malformed / poorly
written" from "this skill performs badly in practice" (that second question
needs actual runs — see the `skill-creator` skill for that if it's
available).

## Why two layers

Some things about a skill are objectively checkable (does the frontmatter
parse, is the name kebab-case, is the description under 1024 characters).
Other things need judgment (is the description "pushy" enough, does the
writing explain *why* instead of barking MUST/NEVER, is the skill overfit
to one narrow example). This skill runs both:

1. **Deterministic pass** — `scripts/structural_check.py` computes hard
   facts and compliance errors.
2. **Qualitative pass** — you read the skill yourself against
   `references/rubric.md` and turn judgment calls into scored findings.

Never skip straight to writing the report from the script output alone —
the script cannot judge writing quality, and several of its checks (e.g.
orphaned resource files) are only *candidate* signals that need your
confirmation against the actual text before they're reported as real
findings.

## Step 1: Locate what to review

Figure out what the user wants reviewed:
- A path to a skill directory or `SKILL.md` file on disk → use that.
- A skill installed in this session (visible under `/mnt/skills/...` or
  similar) → use that path directly (read-only; don't try to edit it).
- Pasted SKILL.md content with no file → write it to a temp directory
  first (e.g. `/tmp/skill-under-review/SKILL.md`) so the script can run
  against it. Ask the user for any bundled resources they want included,
  or proceed with SKILL.md alone and note the limitation in the report.

If genuinely ambiguous (e.g. multiple skills exist and the user didn't say
which), ask. Otherwise proceed — don't stall on minor ambiguity.

## Step 2: Run the deterministic check

```bash
python3 scripts/structural_check.py <path-to-skill-directory>
```

This prints one JSON object: parsed frontmatter, `compliance_errors` (hard
failures — missing/invalid frontmatter, bad naming, multiple SKILL.md
files, disallowed keys), `structural_warnings`, and `metrics` (line counts,
description word count, resource file inventory, orphaned-file candidates,
large-reference-without-TOC list, hardcoded-path candidates, imperative
marker counts).

If `fatal_error` is present (e.g. path doesn't exist, PyYAML missing —
install with `pip install pyyaml --break-system-packages` if needed), fix
the environment issue and rerun before continuing.

Any `compliance_errors` are automatic **Blocker** findings — the skill will
fail to parse or upload. List these first in the report regardless of what
else you find.

## Step 3: Read the skill yourself

Open the actual `SKILL.md` body (and any `references/` files it points to)
and score it against `references/rubric.md`, covering:

1. Description & triggering quality
2. Structure & progressive disclosure
3. Writing style & content quality
4. Safety

For every candidate the script flagged as a *signal* rather than a hard
fact (orphaned resource files, portability path matches, large-reference
TOC gaps, high imperative-marker counts), verify it against the real text
before treating it as a finding — false positives are worse than silence
here, since they erode trust in the whole report. For example, a script
referenced only via `python -m scripts.foo` is still properly pointed-to
even though "foo.py" doesn't appear verbatim in the body.

Also walk `metrics.must_never_lines` — every MUST/NEVER line the script
found, with its line number and text — against rubric.md's "Hard
directives that need enforcement, not just prose" guidance under Safety.
Most will need no finding; flag only the ones protecting against real harm.

## Step 4: Write concrete rewrites, not just diagnoses

For every Minor/Major/Blocker finding, include the current problematic
text (or a description of the structural problem) and a specific rewritten
version — not just "this is vague, make it more specific." If a finding is
purely mechanical (move a file, delete an unused key), describe the exact
mechanical fix instead of prose rewrite.

Keep rewrites proportionate: don't rewrite parts of the skill that are
already fine just to demonstrate thoroughness.

## Step 5: Produce both output files

Follow `references/schema.md` exactly for the JSON structure. Compute
`overall_verdict` from the category scores (`blocked` if any category is
`blocker`, `needs_work` if any is `major`, `pass_with_suggestions` if only
`minor` findings remain, else `pass`).

Write:
- `<skill-name>-review.json` — full structured output per the schema.
- `<skill-name>-review.md` — human-readable: lead with `overall_verdict`
  and the one-paragraph summary, then a findings table (severity |
  category | issue | suggested fix), grouped by severity with Blockers
  first. Keep it scannable — this should be readable in under a minute for
  a skill with a handful of findings.

Save both to `/mnt/user-data/outputs/` and present them with `present_files`
when that convention exists in the current environment. Outside a sandbox
with that convention (e.g. a local Claude Code session), save both files
next to the skill directory being reviewed and tell the user the paths
directly.

If the user just wants a quick verdict in chat rather than files, it's fine
to summarize inline instead — use judgment based on how the request was
phrased ("give me a quick take" vs. "review this skill").

## Notes for use in an evaluation pipeline

If this skill is being run as part of a larger Claude Code Skill
evaluation (comparing skill versions, gating publication, etc.), the JSON
output is designed to be diffed across versions: compare `category_scores`
and finding counts between an old and new `SKILL.md` to get a quick signal
on whether a revision improved structural/writing quality — independent of
and prior to any runtime benchmark of actual task performance.
