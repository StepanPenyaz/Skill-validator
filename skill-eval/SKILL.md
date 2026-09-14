---
name: skill-eval
description: Runs a Claude Agent Skill against real tasks and reports what it actually cost to do so — model used, token count, wall-clock time, and a short qualitative judgment of how the run went. Use this whenever the user asks to evaluate a skill's runtime cost, compare how a skill performs across models, measure a skill's token/time cost, or wants to know whether a new version of a skill is worth its cost relative to the old one. Not for asking whether a SKILL.md is well-written — that's skill-review.
metadata:
  version: "0.3.0"
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

1. **Run the gate check.** Before doing anything else, run `skill-review`'s
   gate mode against the target skill directory:

   ```bash
   python3 ../skill-review/scripts/structural_check.py <target-skill-directory>
   ```

   This is deterministic and makes no model call. Then:
   - If `compliance_errors` is non-empty (any Blocker-severity finding —
     malformed frontmatter, a hardcoded secret, etc.) → **stop
     immediately**. Report the gate failure to the user, quoting the
     `compliance_errors` entries verbatim, and do not proceed to running
     the target skill at all.
   - If `compliance_errors` is empty → continue to step 2.
     `structural_warnings` (Warning/Info-severity findings) are **not**
     blocking — see Decision Guidelines for what to do with them instead
     of silently dropping them.

> Steps 2-4 are stubs — filled in by later work:
> 2. Run the target skill against a fixed task-fixture set, once per model
>    in the configured model list, capturing model/time per run for real
>    and token count as a labeled estimate — see
>    `references/token-capture.md` for why it's an estimate, not a
>    measurement, and how it's computed.
> 3. Write a short qualitative judgment per run.
> 4. Render the results as one table: Model Used | Number of Tokens | Time
>    Spent | Claude's Judgment.

# Rules

- **Never proceed past a failed gate check.** If Workflow step 1's
  `compliance_errors` is non-empty, stop there — report the failure and do
  not run the target skill. This is not optional or a judgment call: a
  skill with a Blocker-severity finding shouldn't be run to measure its
  cost or behavior, regardless of how the user phrased the request.
- Never collapse a run's judgment into a numeric score — report concrete,
  verifiable observations instead.

# Decision Guidelines

- **`structural_warnings` from the gate check are not blocking — proceed,
  but don't drop them.** A skill can have Warning/Info-severity findings
  (an orphaned resource file, a missing `metadata.version`, a dangerous-
  shell-pattern candidate) and still be safe to run. Continue to step 2,
  but carry the warning count forward and surface it alongside the final
  report — e.g. a short "Gate check: N structural warning(s), not
  blocking" note near the results table — so the user can see the target
  skill wasn't perfectly clean even though evaluation proceeded, instead
  of that information silently disappearing after step 1.
- More to come as later Workflow steps are filled in.

# References

- `references/token-capture.md` — why the "Number of Tokens" column is a
  labeled estimate, not a measurement, in this environment, and how the
  estimate is computed. See Workflow step 2.
- `../SURVEY.md` — survey of existing eval/cost-tracking tools and why
  `skill-eval` is mostly custom-built rather than adopting one wholesale.
- More to come as `references/` files are added (task-fixture format,
  models configuration, etc.).
