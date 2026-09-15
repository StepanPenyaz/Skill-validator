---
name: skill-eval
description: Runs a Claude Agent Skill against real tasks and reports what it actually cost to do so — model used, token count, wall-clock time, and a short qualitative judgment of how the run went. Use this whenever the user asks to evaluate a skill's runtime cost, compare how a skill performs across models, measure a skill's token/time cost, or wants to know whether a new version of a skill is worth its cost relative to the old one. Not for asking whether a SKILL.md is well-written — that's skill-review.
metadata:
  version: "0.6.0"
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

`skill-eval` runs `skill-review` against the target skill before doing
anything else — both its deterministic gate mode and, if that passes, its
qualitative full review mode too — and refuses to proceed if either comes
back blocked. There is no point measuring the runtime cost of a skill that
would fail to parse or ship, and a hard compliance error isn't the only
way a skill can be broken: some blocking problems (a safety-relevant
pattern that's an actual problem in context, not just a regex candidate)
only surface once a model actually reads the skill. See Workflow.

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

1. **Run the gate check — two stages, cheapest first.** Before doing
   anything else, run `skill-review` against the target skill directory,
   in this order, stopping at the first stage that fails:

   1a. **Deterministic stage.** Run `skill-review`'s gate mode:

       ```bash
       python3 ../skill-review/scripts/structural_check.py <target-skill-directory>
       ```

       No model call. If `compliance_errors` is non-empty (any
       Blocker-severity finding — malformed frontmatter, a hardcoded
       secret, etc.) → **stop immediately**. Report the gate failure to
       the user, quoting the `compliance_errors` entries verbatim, and do
       not proceed to stage 1b or to running the target skill at all. If
       empty → continue to stage 1b. `structural_warnings`
       (Warning/Info-severity findings) are **not** blocking — see
       Decision Guidelines for what to do with them instead of silently
       dropping them.

   1b. **Qualitative stage.** Run `skill-review`'s full review mode
       (`skill-review/SKILL.md` Workflow steps 1-5 — this one does need a
       model, since it's the pass that judges things a regex can't, like
       whether a safety-relevant pattern is an actual problem in context)
       against the same target skill directory. If the resulting
       `overall_verdict` is `blocked` (any `category_scores` entry is
       `blocker`) → **stop immediately**. Report which category was
       blocked and why, and do not proceed to running the target skill.
       If not blocked → continue to step 2.

   Run 1a before 1b, not the other way around or both at once: 1a is
   free (no model call) and catches most breakage, so there's no reason
   to spend a model call on 1b for a skill that was already going to fail
   1a.

> Steps 2-4 are stubs — filled in by later work:
> 2. Determine the model list for this run (`references/models_config.yaml`'s
>    `default_models`, plus any models the user asked to add for this run
>    only — see Decision Guidelines). Run the target skill against a fixed
>    task-fixture set from `tests/fixtures/tasks/<skill-name>.yaml` (format
>    and authoring methodology: `references/task-authoring.md`), once per
>    model in that list, capturing model/time per run for real and token
>    count as a labeled estimate — see `references/token-capture.md` for
>    why it's an estimate, not a measurement, and how it's computed.
> 3. Write a short qualitative judgment per run.
> 4. Render the results as one table: Model Used | Number of Tokens | Time
>    Spent | Claude's Judgment.

# Rules

- **Never proceed past a failed gate check, at either stage.** If Workflow
  step 1a's `compliance_errors` is non-empty, or step 1b's
  `overall_verdict` is `blocked`, stop there — report the failure and do
  not run the target skill. This is not optional or a judgment call: a
  skill with a Blocker-level finding, deterministic or qualitative,
  shouldn't be run to measure its cost or behavior, regardless of how the
  user phrased the request.
- **Never skip straight to 1b, and never run it before 1a.** 1a is free
  and catches most breakage; running the model-requiring qualitative stage
  first (or instead) wastes a model call on a skill that was already
  going to fail the deterministic check.
- Never collapse a run's judgment into a numeric score — report concrete,
  verifiable observations instead.

# Decision Guidelines

- **`structural_warnings` from stage 1a are not blocking — proceed, but
  don't drop them.** A skill can have Warning/Info-severity findings (an
  orphaned resource file, a missing `metadata.version`, a dangerous-
  shell-pattern candidate) and still be safe to run. Continue past 1a, but
  carry the warning count forward and surface it alongside the final
  report — e.g. a short "Gate check: N structural warning(s), not
  blocking" note near the results table — so the user can see the target
  skill wasn't perfectly clean even though evaluation proceeded, instead
  of that information silently disappearing after stage 1a.
- **A non-`blocked` verdict from stage 1b gets the same treatment.** If
  full review mode comes back `needs_work` or `pass_with_suggestions`
  (not `blocked`), proceed — but surface `overall_verdict` and the
  category scores alongside the final report too, the same way stage 1a's
  warnings are. A skill can be worth evaluating for cost/behavior while
  still having writing-quality issues; don't let that context disappear
  once stage 1b passes.
- **Extending the model list for a comparison.** Step 2's model list
  starts from `references/models_config.yaml`'s `default_models` (just
  `sonnet` out of the box). Two ways to add more, both valid, use the one
  that fits the request:
  - Persistent: edit `default_models` in that file — affects every future
    run, not just this one. Do this when the user wants a standing change
    ("always compare against haiku from now on").
  - One-off: if the user asks at invocation time for extra models for
    *this* run only (e.g. "also test this on haiku and opus"), add them
    to the list used for this run without editing the file.
  Either way, step 2 spawns one `Agent`-tool subagent per model in the
  resulting list, each given the same task prompt and the same target
  skill — the model list is the only thing that varies between rows of
  the final table.
- More to come as later Workflow steps are filled in.

# References

- `../skill-review/references/schema.md` — the `overall_verdict`/
  `category_scores` shape Workflow step 1b's full review mode produces;
  needed to know what "blocked" actually means there.
- `references/models_config.yaml` — the editable `default_models` list;
  see Decision Guidelines for how to extend it, persistently or per-run.
- `references/task-authoring.md` — the `tests/fixtures/tasks/<skill-name>.yaml`
  format and how to write one. See Workflow step 2.
- `references/token-capture.md` — why the "Number of Tokens" column is a
  labeled estimate, not a measurement, in this environment, and how the
  estimate is computed. See Workflow step 2.
- `../SURVEY.md` — survey of existing eval/cost-tracking tools and why
  `skill-eval` is mostly custom-built rather than adopting one wholesale.
