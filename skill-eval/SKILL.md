---
name: skill-eval
description: Runs a Claude Agent Skill against real tasks and reports what it actually cost to do so — model used, token count, wall-clock time, and a short qualitative judgment of how the run went. Use this whenever the user asks to evaluate a skill's runtime cost, compare how a skill performs across models, measure a skill's token/time cost, or wants to know whether a new version of a skill is worth its cost relative to the old one. Not for asking whether a SKILL.md is well-written — that's skill-review.
metadata:
  version: "0.1.0"
  maintained_by: "Claude Code Skill Evaluation project"
---

# Purpose

`skill-eval` answers a different question from `skill-review`. `skill-review`
asks "is this skill well-written?" (a static read of `SKILL.md` and its
bundled resources, no execution). `skill-eval` asks "does this skill do its
job well, at what cost?" — it actually runs the target skill against real
tasks and reports what happened: which model, how many tokens, how long it
took, and a short judgment of the result.

It does not produce a single numeric quality score. A run's outcome is
reported as a short freeform judgment (concrete observations, not a
pass/fail verdict or a rating) sitting next to the run's cost in the same
table row — the comparison is made by reading the row, not by a computed
ratio.

`skill-eval` runs `skill-review`'s gate mode against the target skill
before doing anything else, and refuses to proceed if that comes back with
a breaking (Blocker-severity) error — there is no point measuring the
runtime cost of a skill that would fail to parse or ship in the first
place. See Workflow.

# When to Use

- The user asks to evaluate, benchmark, or measure a skill's runtime cost
  or behavior — e.g. "how much does this skill cost to run", "evaluate
  this skill", "how does this skill perform on Haiku vs Sonnet".
- Comparing two versions of the same skill on cost and behavior, not just
  on `skill-review`'s static quality score.
- As part of a decision about whether a change to a skill is worth its
  added (or reduced) cost.

# When NOT to Use

- The user wants to know whether a `SKILL.md` is well-formed, well-written,
  or ready to publish, without running it — that's `skill-review`'s job
  (gate mode or full review mode), not this skill's.
- The user wants a single quality score or a pass/fail verdict on a
  skill's behavior — `skill-eval` deliberately reports a qualitative
  judgment instead, not a score; point out this limitation rather than
  inventing a number to satisfy the request.

# Workflow

> Stub — filled in by later work. Planned steps, in order:
> 1. Run `skill-review`'s gate mode against the target skill directory;
>    stop on any breaking (Blocker) finding.
> 2. Run the target skill against a fixed task-fixture set, once per model
>    in the configured model list, capturing model/tokens/time per run.
> 3. Write a short qualitative judgment per run.
> 4. Render the results as one table: Model Used | Number of Tokens | Time
>    Spent | Claude's Judgment.

# Rules

- Never proceed past a failed gate check (see Workflow step 1 once
  written) — a skill with a Blocker-severity finding shouldn't be run to
  measure its cost or behavior.
- Never collapse a run's judgment into a numeric score — report concrete,
  verifiable observations instead.

# Decision Guidelines

> To be filled in alongside the Workflow steps above.

# References

> To be filled in as `references/` files are added (task-fixture format,
> models configuration, etc.).
