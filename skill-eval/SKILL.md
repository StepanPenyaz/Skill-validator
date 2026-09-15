---
name: skill-eval
description: Runs a Claude Agent Skill against real tasks and reports what it actually cost to do so — model used, token count, wall-clock time, and a short qualitative judgment of how the run went. Use this whenever the user asks to evaluate a skill's runtime cost, compare how a skill performs across models, measure a skill's token/time cost, or wants to know whether a new version of a skill is worth its cost relative to the old one. Not for asking whether a SKILL.md is well-written — that's skill-review.
metadata:
  version: "0.11.0"
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

2. **Run the target skill, once per model.** Do this after step 1 passes,
   never before.

   - **Determine the model list**: `references/models_config.yaml`'s
     `default_models`, plus any models the user asked to add for this run
     only — see Decision Guidelines.
   - **Load the task fixture**: `tests/fixtures/tasks/<skill-name>.yaml`
     (format: `references/task-authoring.md`). If it doesn't exist yet for
     this target skill, that's a stop condition too — see Decision
     Guidelines, don't invent tasks on the fly instead.
   - **For each model in the list, spawn one `Agent`-tool subagent**
     (`model` parameter set to that model) covering *all* tasks from the
     fixture in a single conversation — not one subagent per task. This
     is what makes "one row per model" in the final table meaningful: the
     row reflects the cost of evaluating the whole task set on that
     model, not just one task, and step 3 reads one coherent transcript
     per model instead of stitching several together.
   - **The subagent's prompt must give it everything it needs to actually
     act as the target skill**, since a target skill sitting in this repo
     isn't necessarily auto-loaded/triggered for a fresh subagent the way
     an installed skill would be. Tell it explicitly: read
     `<target-skill-directory>/SKILL.md` (and any bundled `scripts/`/
     `references/` it points to) and follow its instructions to complete
     each task below, in order, using its own tools as needed — then list
     the task prompts from the fixture, each labeled with its `id`.
   - **The subagent's prompt must also ask it to self-report its token
     usage**, since nothing in this environment can retrieve that after
     the fact (see `references/token-capture.md`). Instruct it: as the
     last line of your final report, on its own line, write `Approx.
     tokens used: ~N (estimated)`, where `N` is (everything you were
     given in this prompt, in characters, plus your full final report, in
     characters) ÷ 4 — a standard characters-per-token rule of thumb.
   - **Capture wall-clock time yourself**, around the `Agent` call — start
     a timestamp immediately before spawning it, stop immediately after
     it returns. Don't rely on the subagent to report its own elapsed
     time; it has no reliable way to know that either.
   - **Parse the token estimate back out of the subagent's final report**
     (the `Approx. tokens used: ~N` line) rather than asking for it as
     structured output — the subagent's own final report *is* what step 3
     reads as the run's transcript, so keep it as one coherent piece of
     text for that step to work with, not a report plus a separate
     side-channel value.
   - Continue to step 3 once every model in the list has a captured
     `{model, tokens (estimated), time_seconds, transcript}`.

3. **Write a judgment for each run.** For each model's run from step 2,
   read that run's transcript/output and write 2-4 short bullet points —
   concrete, verifiable observations, not a score. Cover things like: what
   it got right, what it missed, anything notable about how it used tools
   or followed the task. No pass/fail verdict, no numeric rating, no
   overall summary sentence trying to compress the bullets into one
   judgment — the bullets *are* the judgment.

   Worked example — a hypothetical run of a CSV-cleanup skill against a
   file with a missing header row:
   - Correctly detected the missing header and inferred column names from
     the first data row instead of erroring out.
   - Used the `Bash` tool to run the provided `validate.sh` script before
     writing output, as the skill's instructions require.
   - Left two fully-blank rows in the output instead of stripping them,
     even though the skill's `SKILL.md` says to remove blank rows.

   Each bullet there names a specific, checkable thing about *this* run —
   contrast with vague filler like "handled the task well" or "followed
   instructions," which could describe any run and tells the reader
   nothing they could verify against the transcript.

4. **Render the report.** By this point steps 1-3 have already collected
   everything needed — the gate-check result, and each run's model,
   token count, elapsed time, and judgment bullets. Rendering that into
   the final table is purely mechanical, so it's a script, not another
   judgment call:

   - Assemble the collected data into the JSON shape
     `scripts/render_report.py`'s module docstring documents (`skill_name`,
     `gate_check.stage_1a.structural_warnings_count`,
     `gate_check.stage_1b.overall_verdict`, and `runs[]` with
     `model`/`tokens`/`tokens_estimated`/`time_seconds`/`judgment`), write
     it to a temp file, and run:

     ```bash
     python3 scripts/render_report.py <input.json> --out <skill-name>-eval.md
     ```

   - The rendered report leads with the gate-check result — both stages,
     even though both necessarily passed to get this far — so the report
     is self-contained and doesn't require re-running gate mode to know
     it happened (see Decision Guidelines on why that context shouldn't
     silently disappear). Then one Markdown table, one row per model:
     `Model Used | Number of Tokens | Time Spent | Claude's Judgment`,
     judgment bullets rendered as a `<br>`-separated list within the
     cell.
   - Save the file as `<skill-name>-eval.md` — mirroring `skill-review`'s
     `<skill-name>-review.md` convention exactly, including where it's
     saved: to `/mnt/user-data/outputs/` when that convention exists in
     the current environment, otherwise next to the target skill
     directory with the path given to the user directly.

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
- **Never invent tasks on the fly.** If `tests/fixtures/tasks/<skill-name>.yaml`
  doesn't exist yet for the target skill, stop and tell the user a task
  fixture needs to be authored first (`references/task-authoring.md`)
  rather than improvising prompts — an improvised task set defeats the
  whole point of a fixed fixture (see "why a fixed fixture" in that file):
  it wouldn't be the same task set on a rerun or a version comparison.
- **One subagent per model, covering every task — never one subagent per
  task.** Splitting by task would produce several transcripts per model
  instead of one, breaking step 3's "read that run's transcript" (singular)
  and making "one row per model" in the final table misleading rather than
  a real per-model cost.
- **Never collapse a run's judgment into a numeric score.** Report
  concrete, verifiable observations instead — see step 3.
- **Every judgment bullet must reference something specific and
  verifiable from that particular run** — "used the `Bash` tool correctly
  to run the install script" or "missed the edge case where the input CSV
  has no header row," not generic filler like "handled the task well"
  that could equally describe any run and gives the reader nothing to
  check against the transcript. If a bullet would read the same for a
  different run on a different skill, rewrite it or drop it.

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
  resulting list, each given the same task set and the same target skill
  — the model list is the only thing that varies between rows of the
  final table.
- **No task fixture for this skill yet.** If
  `tests/fixtures/tasks/<skill-name>.yaml` doesn't exist, don't guess at
  tasks — tell the user, and offer to write one following
  `references/task-authoring.md` (a manual/assisted step, per that file)
  before continuing. Only proceed with the run once a real fixture exists.

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
- `scripts/render_report.py` — run in Workflow step 4 to render the final
  Markdown report; purely mechanical, no model call, same role
  `skill-review/scripts/generate_static_report.py` plays there.
- `../SURVEY.md` — survey of existing eval/cost-tracking tools and why
  `skill-eval` is mostly custom-built rather than adopting one wholesale.
