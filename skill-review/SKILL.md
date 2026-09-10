---
name: skill-review
description: Statically reviews a Claude Agent Skill's SKILL.md and bundled resources against best-practice conventions — frontmatter compliance, progressive disclosure and file structure, description/triggering strength, writing style (explained reasoning vs. rigid MUST/NEVER directives), overfitting, and safety. Produces both a machine-readable JSON scorecard and a human-readable markdown report, with a concrete suggested rewrite for every flagged issue. Use this whenever the user asks to review, audit, lint, validate, critique, grade, or get feedback on a skill or a SKILL.md file — before publishing a new skill, as a pre-check in a skill-evaluation pipeline, or when comparing two skill versions. Trigger even on casual phrasing like "check this skill", "is this SKILL.md any good", or "what's wrong with my skill" without the user saying "validate" explicitly.
metadata:
  version: "1.5.0"
  maintained_by: "Claude Code Skill Evaluation project"
---

# Purpose

A static reviewer for Claude Agent Skills. It reads a `SKILL.md` and its
bundled resources and judges them against known best practices — it never
executes the skill being reviewed. This keeps "this skill is malformed or
poorly written" cleanly separate from "this skill performs badly in
practice" (that second question needs actual runs; see the `skill-creator`
skill for that if it's available).

The review runs in two layers: a **deterministic pass**
(`scripts/structural_check.py` computes hard facts and compliance errors)
and a **qualitative pass** (you read the skill yourself against
`references/rubric.md` and turn judgment calls into scored findings). Some
things about a skill are objectively checkable — does the frontmatter
parse, is the name kebab-case, is the description under 1024 characters.
Others need judgment — is the description "pushy" enough, does the writing
explain *why* instead of barking directives, is the skill overfit to one
narrow example. Both layers are required for a full review; see Workflow.

# When to Use

- The user asks to review, audit, lint, validate, critique, grade, or get
  feedback on a skill or a `SKILL.md` file — including casual phrasing like
  "check this skill", "is this SKILL.md any good", or "what's wrong with my
  skill," without them saying "validate" explicitly.
- As a pre-check before publishing a new skill.
- As a gate in a skill-evaluation pipeline.
- When comparing two versions of the same skill (see Decision Guidelines
  for how the JSON output supports diffing).

# When NOT to Use

- The user wants to know whether a skill performs well in actual use
  (triggering accuracy in practice, task success rate) rather than whether
  it's well-formed and well-written. That's a runtime question — point to
  the `skill-creator` skill if available, rather than trying to answer it
  from a static read.

# Workflow

1. **Locate what to review.** Figure out what the user wants reviewed:
   - A path to a skill directory or `SKILL.md` file on disk → use that.
   - A skill installed in this session (visible under `/mnt/skills/...` or
     similar) → use that path directly (read-only; don't try to edit it).
   - Pasted SKILL.md content with no file → write it to a temp directory
     first (e.g. `/tmp/skill-under-review/SKILL.md`) so the script can run
     against it. Ask the user for any bundled resources they want
     included, or proceed with SKILL.md alone and note the limitation in
     the report.

2. **Run the deterministic check.**

   ```bash
   python3 scripts/structural_check.py <path-to-skill-directory>
   ```

   This prints one JSON object: parsed frontmatter, `compliance_errors`
   (hard failures — missing/invalid frontmatter, bad naming, wrong
   SKILL.md filename case, multiple SKILL.md files, disallowed keys,
   hardcoded secrets/credentials), `structural_warnings`, and `metrics`
   (line counts, description word count, resource directory inventory and
   per-directory file counts, preferred-structure section coverage,
   orphaned-file candidates, large-reference-without-TOC list,
   hardcoded-path candidates, imperative marker counts, declared-vs-referenced
   tool usage, and security pattern candidates — dangerous shell commands,
   prompt-injection/instruction-override phrasing, prohibited-action
   phrasing, undeclared external hosts).

   If `fatal_error` is present, see Decision Guidelines.

   Every check the script runs also lands in `result["findings"]` — the
   same facts as `compliance_errors`/`structural_warnings`, but structured
   as `{category, severity, issue, suggestion, location}` with a
   Blocker/Warning/Info severity per check (not the rubric's
   Minor/Major/Blocker/Pass scale used later — these are two different
   scales; don't conflate them). Severity is looked up at run time from
   `references/severity_config.yaml`, not hardcoded.

   If the user wants a quick, purely mechanical rendering of just this
   deterministic layer, see Decision Guidelines for
   `generate_static_report.py`.

3. **Read the skill yourself.** Open the actual `SKILL.md` body (and any
   `references/` files it points to) and score it against
   `references/rubric.md`, covering:
   1. Description & triggering quality
   2. Structure & progressive disclosure — `references/preferred-structure.md`
      has a suggested section outline if the skill under review would
      benefit from restructuring; it's a recommendation, not a
      requirement, so don't flag a skill just for using a different shape.
   3. Writing style & content quality
   4. Safety

   For every candidate the script flagged as a *signal* rather than a hard
   fact (orphaned resource files, portability path matches, large-reference
   TOC gaps, high imperative-marker counts), verify it against the real
   text before treating it as a finding — false positives are worse than
   silence here, since they erode trust in the whole report. For example, a
   script referenced only via `python -m scripts.foo` is still properly
   pointed-to even though "foo.py" doesn't appear verbatim in the body.

   Also walk `metrics.must_never_lines` — every hard-directive line the
   script found, with its line number and text — against rubric.md's
   guidance on directives that need enforcement, not just prose. Most will
   need no finding; flag only the ones protecting against real harm.

   Give the same treatment to `dangerous_shell_pattern_candidates`,
   `prompt_injection_phrase_candidates`, `prohibited_action_phrase_candidates`,
   `undeclared_external_hosts`, `tools_declared_but_unreferenced`, and
   `tools_referenced_but_undeclared` — confirm each against the real
   surrounding text before reporting it as a finding (see rubric.md). Any
   `hardcoded_secret_candidates` are already listed in `compliance_errors`
   as Blockers; no separate judgment needed there.

4. **Write concrete rewrites, not just diagnoses.** For every
   Minor/Major/Blocker finding, include the current problematic text (or a
   description of the structural problem) and a specific rewritten version
   — not just "this is vague, make it more specific." If a finding is
   purely mechanical (move a file, delete an unused key), describe the
   exact mechanical fix instead of a prose rewrite.

5. **Produce both output files.** Follow `references/schema.md` exactly
   for the JSON structure. Compute `overall_verdict` per Decision
   Guidelines. Write:
   - `<skill-name>-review.json` — full structured output per the schema.
   - `<skill-name>-review.md` — human-readable: lead with `overall_verdict`
     and the one-paragraph summary, then a findings table (severity |
     category | issue | suggested fix), grouped by severity with Blockers
     first. Keep it scannable — readable in under a minute for a skill
     with a handful of findings.

   See Decision Guidelines for when to save files vs. summarize inline.

# Rules

- **Never skip straight to writing the report from script output alone.**
  The script cannot judge writing quality, and several of its checks (e.g.
  orphaned resource files) are only *candidate* signals that need
  confirmation against the actual text before they're reported as real
  findings. Skipping this step produces false positives that undermine the
  whole report.
- **Compliance errors are automatic Blockers.** Any `compliance_errors` the
  script returns are hard failures — the skill will fail to parse or
  upload. List these first in the report regardless of what else is found.
- **Confirm before reporting.** Every candidate metric (orphaned files,
  hard-directive lines, dangerous-shell patterns, prompt-injection
  phrasing, prohibited-action phrasing, undeclared hosts, tool-usage
  mismatches) must be checked against the real surrounding text before it
  becomes a finding. A raw regex match is not a verdict.
- **Keep rewrites proportionate.** Don't rewrite parts of the skill that
  are already fine just to demonstrate thoroughness.
- **Stay read-only.** This skill never executes or modifies the skill
  being reviewed — it only reads `SKILL.md` and its bundled resources.

# Decision Guidelines

- If it's genuinely ambiguous what to review (e.g. multiple skills exist
  and the user didn't say which) → ask. Otherwise proceed — don't stall on
  minor ambiguity.
- If `fatal_error` is present in the script output (e.g. path doesn't
  exist, PyYAML missing — install with
  `pip install pyyaml --break-system-packages` if needed) → fix the
  environment issue and rerun before continuing.
- If the user wants a quick, purely mechanical rendering of just the
  deterministic layer — no qualitative confirmation, no rewrites — run
  `python3 scripts/generate_static_report.py <path-to-skill-directory>`
  (add `--out <path>` to write to a file instead of stdout) instead of the
  full Workflow. This is **not** a substitute for Workflow steps 3-5; only
  reach for it when the user explicitly wants the fast static-only view.
- If the user just wants a quick verdict in chat rather than files → it's
  fine to summarize inline instead of writing output files. Use judgment
  based on how the request was phrased ("give me a quick take" vs. "review
  this skill").
- Compute `overall_verdict` from the category scores: `blocked` if any
  category is `blocker`, `needs_work` if any is `major`,
  `pass_with_suggestions` if only `minor` findings remain, else `pass`.
- If this review is being run as part of a larger Claude Code Skill
  evaluation (comparing skill versions, gating publication, etc.), the JSON
  output is designed to be diffed across versions: compare
  `category_scores` and finding counts between an old and new `SKILL.md` to
  get a quick signal on whether a revision improved structural/writing
  quality — independent of and prior to any runtime benchmark of actual
  task performance.

# Validation

Before finishing, check:
- Every `compliance_errors` entry is reported first, as a Blocker.
- Every candidate-only metric was checked against the real text and either
  confirmed as a finding or explicitly dismissed — none were reported on
  the strength of the raw regex match alone.
- Every Minor/Major/Blocker finding has a concrete rewrite or a described
  mechanical fix, not just a diagnosis.
- Rewrites are proportionate — unaffected, already-fine parts of the skill
  weren't rewritten just to pad the report.
- The JSON output matches `references/schema.md` exactly, and
  `overall_verdict` is consistent with the category scores.
- Both output files are saved to `/mnt/user-data/outputs/` and presented
  with `present_files` when that convention exists in the current
  environment; outside such a sandbox, both files are saved next to the
  skill directory and the paths are given to the user directly.

# References

- `scripts/structural_check.py` — run in Workflow step 2 to produce the
  deterministic JSON scorecard.
- `scripts/generate_static_report.py` — quick static-only Markdown report;
  see Decision Guidelines for when to use this instead of the full
  Workflow.
- `references/rubric.md` — the qualitative scoring rubric; open it in
  Workflow step 3 to score description/triggering, structure, writing
  style, and safety.
- `references/preferred-structure.md` — the optional 8-section outline
  used when judging structure in Workflow step 3.
- `references/schema.md` — the exact JSON output structure; follow it in
  Workflow step 5.
- `references/severity_config.yaml` — the `check_id -> severity` table
  `structural_check.py` reads at run time; if a validation run's severities
  look off, check this file (not the script) first.