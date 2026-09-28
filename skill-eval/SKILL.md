---
name: skill-eval
description: Statically reviews a Claude Agent Skill's SKILL.md and bundled resources against best-practice conventions (frontmatter compliance, structure, writing style, safety), then runs it against real tasks and reports what it actually cost to do so — model used, token count, wall-clock time — alongside a short qualitative judgment of how the run went. Use this whenever the user asks to review, audit, lint, validate, critique, grade, or get feedback on a skill or SKILL.md file ("check this skill", "is this SKILL.md any good", "what's wrong with my skill"), or to evaluate, benchmark, or measure a skill's runtime cost/behavior ("how much does this skill cost to run", "how does this skill perform on Haiku vs Sonnet"). Also use it to compare two versions of the same skill — the report covers both the structural/quality diff and the cost/behavior diff in that one case. Trigger even on casual phrasing, without the user saying "validate" or "evaluate" explicitly.
metadata:
  version: "1.2.0"
  maintained_by: "Claude Code Skill Evaluation project"
---

# Purpose

`skill-eval` answers two related questions about a Claude Agent Skill, in
one pipeline:

1. **Is it well-written?** A static read of `SKILL.md` and its bundled
   resources against known best practices — frontmatter compliance,
   progressive disclosure, description/triggering strength, writing style,
   overfitting, safety. No execution.
2. **Does it do its job well, at what cost?** Actually running the skill
   against real tasks and reporting what happened: which model, how many
   tokens, how long it took, and a short judgment of the result.

These two questions used to live in separate skills (`skill-review` and
`skill-eval`); they're now one skill because the second question was
always downstream of the first — there's no point measuring the runtime
cost of a skill that's badly written or unsafe, and the static layer's own
JSON output is what step 2 needs anyway to know whether it's safe to
proceed. See CHANGELOG.md's merge entry for the history.

The static layer keeps its own two officially supported entry points —
named explicitly so a CI pipeline, or a person deciding what to run,
doesn't have to reverse-engineer which one they need:

- **Gate mode** — the deterministic layer only: `scripts/structural_check.py`
  / `scripts/generate_static_report.py`, plus `scripts/diff_reviews.py` when
  given two skill directories. No model call; same input always produces
  the same output; safe to run standalone or unattended in CI, independent
  of the rest of this skill's pipeline — a person can run
  `python3 skill-eval/scripts/structural_check.py <dir>` directly for a
  quick pre-check before ever asking for a full evaluation. Gate mode is a
  **complete, correct answer** to "give me a fast structural/security
  check," not a partial or lesser version of a review.
- **Full review mode** — gate mode's output, plus the qualitative pass: read
  the skill yourself against `references/rubric.md` and turn judgment calls
  into scored findings with concrete rewrites. Some things about a skill
  need judgment, not a regex — is the description "pushy" enough, does the
  writing explain *why* instead of barking directives, is the skill overfit
  to one narrow example, is a gate-mode candidate (a MUST/NEVER line, a
  `curl | bash` pattern) an actual problem in context.

Running the target skill against real tasks (the cost/behavior layer) does
not produce a single numeric quality score either. A run's outcome is
reported as a short freeform judgment (concrete observations, not a
pass/fail verdict or a rating) sitting next to the run's cost in the same
table row — the comparison is made by reading the row, not by a computed
ratio.

`skill-eval` runs its own static review against the target skill before
doing anything else — both gate mode and full review mode. Neither stage
stops the pipeline, even on a Blocker or a `blocked` verdict: the full run
(cost/behavior layer included) always happens and a report is always
produced, with whatever the static review found carried forward and
surfaced prominently rather than silently dropped or used as a reason to
withhold the report. A hard compliance error isn't the only way a skill
can be broken — some problems (a safety-relevant pattern that's an actual
problem in context, not just a regex candidate) only surface once a model
actually reads the skill — but either way, the answer is "run it and say
so clearly," not "refuse to run it." See Workflow.

# When to Use

- The user asks to review, audit, lint, validate, critique, grade, or get
  feedback on a skill or a `SKILL.md` file — including casual phrasing like
  "check this skill", "is this SKILL.md any good", or "what's wrong with my
  skill," without them saying "validate" explicitly. This is full review
  mode by default (see Workflow step 1 and Decision Guidelines).
- The user asks to evaluate, benchmark, or measure a skill's runtime cost
  or behavior — e.g. "how much does this skill cost to run", "evaluate
  this skill", "how does this skill perform on Haiku vs Sonnet".
- As a pre-check before publishing a new skill — gate mode alone is usually
  enough for this (see Decision Guidelines); the full pipeline if the user
  also wants runtime cost/behavior data before publishing, not just a
  pass/fail.
- Comparing two versions of the same skill — on structural/writing quality,
  on cost and behavior, or (the default when two versions are given) both
  at once as a single comparative report.
- As a gate in CI or a script — this is gate mode only, not the full
  pipeline (see Decision Guidelines): deterministic, no model call, won't
  false-block on a subjective judgment call.

# When NOT to Use

- The user wants a single quality score or a pass/fail verdict on a
  skill's runtime behavior — `skill-eval` deliberately reports a
  qualitative judgment instead, not a score; point out this limitation
  rather than inventing a number to satisfy the request.
- The user wants to know whether a skill performs well in actual use
  (triggering accuracy in practice, task success rate) from a static read
  alone, without running it — that's what Workflow step 2 is for; don't
  try to answer a runtime question from gate/full-review-mode output alone.

# Workflow

**Determine the mode first: single skill, or two versions to compare.**
Everything below is written for one target skill directory. When the user
instead gives two (an old and a new version of the same skill), the whole
Workflow runs for **both** directories — steps 1-3 happen twice, once per
version, sharing the same model list and the same task fixture (see
Decision Guidelines on why the fixture must be identical for both) — and
step 4 renders one **comparative** report instead of two separate ones:
the structural/qualitative diff between the versions (via
`scripts/diff_reviews.py`) plus a side-by-side cost/judgment table, old vs.
new, per model. This is not a different tool or a separate ask — it's the
same Workflow, doubled, with a different step-4 renderer at the end.

1. **Run the static review — two stages, cheapest first.** Before doing
   anything else, review the target skill directory (each of the two, in
   comparative mode), in this order. A Blocker/`blocked` result at either
   stage is **never a stop condition** for the pipeline as a whole — see
   Rules — it's always carried forward into the final report instead,
   prominently, so the report is always produced and always shows real
   statistics even for a broken skill.

   1a. **Deterministic stage (gate mode).**

       ```bash
       python3 scripts/structural_check.py <target-skill-directory>
       ```

       This prints one JSON object: parsed frontmatter, `compliance_errors`
       (hard failures), `structural_warnings`, and `metrics` (line counts,
       description word count, resource directory inventory, preferred-
       structure section coverage, orphaned-file candidates, hardcoded-path
       candidates, imperative marker counts, declared-vs-referenced tool
       usage, and security pattern candidates). If `compliance_errors` is
       non-empty (any Blocker-severity finding — malformed frontmatter, a
       hardcoded secret, etc.), note it (quote the entries verbatim) and
       **continue to stage 1b anyway** — do not stop the pipeline here.
       `structural_warnings` (Warning/Info-severity findings) are likewise
       **not** blocking — see Decision Guidelines for what to do with both
       instead of silently dropping them.

       `dangerous_shell_pattern_candidates`, `prompt_injection_phrase_candidates`,
       and `undeclared_external_hosts` are skipped by default (empty lists)
       for a skill that declares and references no shell-executing or
       network-capable tool — check `metrics.security_scan.skipped` before
       treating an empty list as "found nothing" rather than "didn't look."
       Re-run with `--force-security-scan` if the tool declarations look
       wrong. `hardcoded_secret_candidates` and
       `prohibited_action_phrase_candidates` are never skipped.

       If the user only wants this deterministic layer (see Decision
       Guidelines), it's fine to stop here and present gate mode's output
       (or `scripts/generate_static_report.py`'s Markdown rendering) as a
       complete answer — not a preview of more to come. That's a scope
       choice the user made, not the same thing as the pipeline stopping
       itself on a Blocker.

   1b. **Qualitative stage (full review mode).** Skipped only when the
       user explicitly asked for gate mode alone. Otherwise: open the
       actual `SKILL.md` body (and any `references/` files it points to)
       and score it against `references/rubric.md`, covering description &
       triggering quality, structure & progressive disclosure, writing
       style & content quality, and safety. For every candidate stage 1a
       flagged as a *signal* rather than a hard fact (orphaned resource
       files, portability path matches, high imperative-marker counts,
       dangerous-shell/prompt-injection/prohibited-action/undeclared-host
       candidates), verify it against the real text before treating it as
       a finding — false positives erode trust in the whole report. For
       every Minor/Major/Blocker finding, write a concrete rewrite (or a
       described mechanical fix), not just a diagnosis. Compute
       `overall_verdict` per Decision Guidelines and produce both output
       files following `references/schema.md` exactly:
       `<skill-name>-review.json` and `<skill-name>-review.md`. If the
       resulting `overall_verdict` is `blocked` (any `category_scores`
       entry is `blocker`), note which category and why, and **continue to
       step 2 anyway** — do not stop the pipeline here either.

   Run 1a before 1b, not the other way around or both at once: 1a is
   free (no model call) and catches most breakage, so there's no reason
   to spend a model call on 1b before knowing what 1a already found.

2. **Run the target skill, once per model.** Do this after step 1 passes,
   never before.

   - **Determine the model list**: `references/models_config.yaml`'s
     `default_models`, plus any models the user asked to add for this run
     only — see Decision Guidelines.
   - **Load the task fixture**: `tests/fixtures/tasks/<skill-name>.yaml`
     (format: `references/task-authoring.md`). If it doesn't exist yet for
     this target skill, **author one now**, following
     `references/task-authoring.md`'s methodology exactly (pull a
     happy-path prompt from the target skill's own description/"When to
     Use", a task exercising whatever its `CHANGELOG.md` most recently
     changed, one "When NOT to Use" boundary case, 3-5 tasks as a starting
     guideline), save it to `tests/fixtures/tasks/<skill-name>.yaml`, and
     continue the run with it — don't stop to ask first. This is not the
     same as improvising ad hoc prompts (see Rules): the fixture is
     authored following the same methodology a human would use, written to
     disk, and treated as frozen from that point on, exactly like a
     manually-authored one — the only difference is who wrote it and that
     the run doesn't pause to wait for approval first. Note in the final
     report that the fixture was auto-generated this run (see Workflow
     step 4) so the reader knows to look at it before relying on a
     rerun/comparison.
   - **For each model in the list, spawn one `Agent`-tool subagent directly
     from this top-level turn** (`model` parameter set to that model)
     covering *all* tasks from the fixture in a single conversation — not
     one subagent per task, and not through a `Workflow` script's
     `agent()` wrapper (see `references/token-capture.md` on why the call
     site matters for step 2's own token capture below). One subagent per
     task set is also what makes "one row per model" in the final table
     meaningful: the row reflects the cost of evaluating the whole task
     set on that model, not just one task, and step 3 reads one coherent
     transcript per model instead of stitching several together.
   - **The subagent's prompt must give it everything it needs to actually
     act as the target skill**, since a target skill sitting in this repo
     isn't necessarily auto-loaded/triggered for a fresh subagent the way
     an installed skill would be. Tell it explicitly: read
     `<target-skill-directory>/SKILL.md` (and any bundled `scripts/`/
     `references/` it points to) and follow its instructions to complete
     each task below, in order, using its own tools as needed — then list
     the task prompts from the fixture, each labeled with its `id`. Do
     *not* ask it to self-report a token estimate — see the next step.
   - **Capture wall-clock time yourself**, around the `Agent` call — start
     a timestamp immediately before spawning it, stop immediately after
     it returns. Don't rely on the subagent to report its own elapsed
     time; it has no reliable way to know that either.
   - **Read the real token count off the `Agent` tool's own return value**
     for that call (`subagent_tokens`) — see `references/token-capture.md`
     for why this is a measured number, not an estimate, as long as the
     call was made the way the first bullet above describes. Report it
     with `tokens_estimated: false`. If `subagent_tokens` is absent from
     the result for some call, that's **never** a silent fallback to a
     self-reported estimate, and never a reason to stop the whole run
     either: record that model's `tokens` as unknown (`null`) and move on
     to the remaining models — `render_report.py` renders an explicit
     "capture failed" note for that row rather than a plain dash, so the
     gap is visible in the final report instead of silently guessed at or
     silently dropped (see `token-capture.md`'s Decision section).
   - Continue to step 3 once every model in the list has a captured
     `{model, tokens (real, or null if capture failed), time_seconds,
     transcript}`.

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
   everything needed — the static-review result(s), and each run's model,
   token count, elapsed time, and judgment bullets. Rendering that into
   the final report is purely mechanical, so it's a script, not another
   judgment call. Two shapes, per the mode determined up front:

   **Single skill:**

   - Assemble the collected data into the JSON shape
     `scripts/render_report.py`'s module docstring documents (`skill_name`,
     `gate_check.stage_1a.structural_warnings_count`, `.compliance_errors`,
     and `.findings` (stage 1a's full findings list, for the embedded
     static-check table — reuses `scripts/generate_static_report.py`'s own
     renderer, not reimplemented), `gate_check.stage_1b.overall_verdict`,
     `.blocked_categories`, `.category_scores`, and `.review_file` (the
     `<skill-name>-review.md` stage 1b already produced, pointed to rather
     than duplicated inline), `task_fixture_auto_generated`, and `runs[]`
     with `model`/`tokens`/`tokens_estimated`/`time_seconds`/`judgment`),
     write it to a temp file, and run:

     ```bash
     python3 scripts/render_report.py <input.json> --out <skill-name>-eval.md
     ```

   - The rendered report leads with the static-review result — always,
     regardless of whether it passed clean, found only non-blocking
     warnings, or found a Blocker/`blocked` verdict — so the report is
     self-contained and doesn't require re-running the static review to
     know what happened (see Decision Guidelines on why that context
     shouldn't silently disappear). A Blocker/`blocked` result renders as
     a prominent warning, not folded quietly into the routine note. Then
     the static-check findings table and the qualitative summary (both
     from stage 1a/1b's output, per above), then one Markdown table, one
     row per model: `Model Used | Number of Tokens | Time Spent | Claude's
     Judgment`, judgment bullets rendered as a `<br>`-separated list
     within the cell. **The model table is always rendered** — the run in
     step 2 always happened regardless of what step 1 found, so there's
     always something to show here.

   **Two skill versions (comparative):**

   - Assemble the collected data into the comparative shape
     `scripts/render_report.py`'s module docstring documents:
     `"report_type": "comparative"`, `old_skill_name`/`new_skill_name`,
     `structural_diff`/`qualitative_diff` (run `scripts/diff_reviews.py`
     on the two skill directories for the former and, if both versions
     produced a `<skill-name>-review.json` in step 1b, on those two files
     for the latter — its own output, passed straight through, not
     re-derived by hand), `task_fixture_auto_generated`, and `runs[]` with
     `model` and per-model `old`/`new` objects, each
     `tokens`/`tokens_estimated`/`time_seconds`/`judgment`. Then run the
     same `scripts/render_report.py <input.json> --out <old>-vs-<new>-eval.md`.
   - The rendered report leads with the structural/qualitative diff
     (`scripts/diff_reviews.py`'s own Markdown rendering, embedded as a
     subsection — not reimplemented here), then one wide table, one row
     per model, old vs. new side by side with a computed delta for tokens
     and time, and separate old/new judgment columns — a reader compares
     the row's two halves directly instead of cross-referencing two
     separate reports by hand.

   - Save the file (`<skill-name>-eval.md` or `<old>-vs-<new>-eval.md`),
     to `/mnt/user-data/outputs/` when that convention exists in the
     current environment, otherwise next to the target skill directory
     (directories, for a comparison) with the path given to the user
     directly.

# Rules

- **Compliance errors are automatic Blockers.** Any `compliance_errors`
  stage 1a returns are hard failures — the skill will fail to parse or
  upload. List these first regardless of what else is found.
- **Confirm before reporting.** Every candidate metric from stage 1a
  (orphaned files, hard-directive lines, dangerous-shell patterns, prompt-
  injection phrasing, prohibited-action phrasing, undeclared hosts,
  tool-usage mismatches) must be checked against the real surrounding text
  in stage 1b before it becomes a finding. A raw regex match is not a
  verdict.
- **Keep rewrites proportionate.** Don't rewrite parts of the skill that
  are already fine just to demonstrate thoroughness.
- **The static-review stages never execute or modify the skill being
  reviewed** — they only read `SKILL.md` and its bundled resources. Only
  step 2 (after both stages pass) actually runs the target skill.
- **Never let a failed static review stop the pipeline, at either stage.**
  Run to completion and always render a report — see Purpose requirement
  that statistics are always shown. A Blocker-level finding, deterministic
  or qualitative, is not a reason to withhold the run or the report; it's
  a reason to make sure the report says so prominently (see Workflow step
  4 and Decision Guidelines). This is not optional or a judgment call in
  the other direction either: never quietly drop a `compliance_errors`
  entry or a `blocked` verdict just because the run proceeded past it.
- **Never skip straight to 1b, and never run it before 1a.** 1a is free
  and catches most breakage; running the model-requiring qualitative stage
  first (or instead) wastes a model call before knowing what 1a already
  found.
- **Never pause to ask before authoring a missing task fixture — but never
  improvise ad hoc prompts instead of authoring one either.** If
  `tests/fixtures/tasks/<skill-name>.yaml` doesn't exist yet for the
  target skill, write one now, following `references/task-authoring.md`'s
  methodology, save it to disk, and continue — don't stop the pipeline to
  ask, and don't substitute unsaved, one-off prompts for it. An
  unsaved/improvised task set defeats the whole point of a fixed fixture
  (see "why a fixed fixture" in that file): it wouldn't be the same task
  set on a rerun or a version comparison. Note in the final report that
  the fixture was auto-generated this run (Workflow step 4).
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

- **Full pipeline vs. gate-mode-only vs. static-review-only — decide this
  first.** Default to the full pipeline (Workflow steps 1-4) when the
  request implies either a writing-quality review or a cost/behavior
  question. Two narrower asks, both legitimate, not a lesser version of
  the full pipeline:
  - **Gate mode only**: the ask is explicitly for a fast, deterministic,
    non-judgmental check — "just run the linter," "quick check before I
    publish," wiring this into CI or a script, or any phrasing that wants
    a stable exit code / machine-checkable result rather than prose
    feedback. Run `python3 scripts/generate_static_report.py
    <target-skill-directory>` (or `structural_check.py` for raw JSON) and
    present that as complete, not a preview of more to come.
  - **Static review only (gate mode + full review mode, no execution)**:
    the ask is about writing quality/compliance only ("review this
    skill," "is this SKILL.md any good," "what's wrong with my skill")
    with no mention of cost, runtime behavior, or "evaluate." Run Workflow
    step 1 (both stages) and stop there — don't run the target skill or
    render the cost table unless the user also wants that.
  Switching to a narrower mode is **not** a downgrade — don't silently
  expand a "just review this" request into a full run-and-cost pipeline,
  and don't silently shrink a "how much does this cost" request down to
  just the static review either.
- **Nothing stage 1a or 1b finds blocks the pipeline — everything they
  find gets surfaced instead, at a severity that matches what it is.**
  Three cases, all non-blocking, all carried forward into the final
  report rather than silently dropped:
  - `structural_warnings` from stage 1a (Warning/Info-severity — an
    orphaned resource file, a missing `metadata.version`, a
    dangerous-shell-pattern candidate): a short "Static review: N
    structural warning(s), not blocking" note near the results table.
  - A non-`blocked` `overall_verdict` from stage 1b (`needs_work` or
    `pass_with_suggestions`): surface `overall_verdict` and the category
    scores alongside the final report the same way.
  - `compliance_errors` from stage 1a, or a `blocked` `overall_verdict`
    from stage 1b: still run the target skill and render the report —
    but this one gets the *prominent* warning treatment (Workflow step 4,
    `render_report.py`'s `gate_check` handling), not folded into the
    routine note, since it's a real Blocker, not just a style nit. A
    skill worth evaluating for cost/behavior isn't the same claim as "this
    skill has no problems" — don't let a Blocker read as if it were a
    routine warning, and don't let it stop the run either.
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
- **No task fixture for this skill yet.** Author one immediately following
  `references/task-authoring.md`'s methodology, save it to
  `tests/fixtures/tasks/<skill-name>.yaml`, and continue the run with it —
  don't stop to ask, and don't improvise unsaved prompts instead (see
  Rules). Mention in the final report that this run's fixture was
  auto-generated (Workflow step 4), so anyone relying on it for a future
  comparison knows to go look at what it actually asked.
- If `fatal_error` is present in a script's output (e.g. path doesn't
  exist, PyYAML missing — install with
  `pip install pyyaml --break-system-packages` if needed) → fix the
  environment issue and rerun before continuing.
- If the user doubts the cost-conditional security-scan skip (stage 1a) —
  e.g. the skill actually shells out or hits the network through a path
  the heuristic doesn't recognize — add `--force-security-scan` to either
  script to run the full scan regardless of declared/referenced tools.
- If the user just wants a quick verdict in chat rather than files → it's
  fine to summarize inline instead of writing output files. Use judgment
  based on how the request was phrased ("give me a quick take" vs. "review
  this skill").
- **Self-consistency (optional, static review only).** A single
  qualitative pass (stage 1b) has run-to-run variance — the same skill
  read twice can land on different severities, or catch a different
  borderline finding. Reach for this when the user explicitly asks for a
  more confident or robust review ("double check this," "how sure are
  you," "run this a few times"), or when the review's output will feed
  something where noise is costly (a CI gate, a version comparison, a
  publish/block decision) — not by default; it costs N times the
  qualitative pass. Repeat stage 1b independently N times (N=3 by
  default, each a genuinely fresh read), save each as
  `<skill-name>-review-run<N>.json`, and reconcile:
  `python3 scripts/reconcile_reviews.py <run1.json> <run2.json> [...] [--threshold N]`.
  It groups findings by `(category, location)`, reports each one's
  agreement count out of N and a consensus severity (ties broken toward
  the more severe value), and recomputes `overall_verdict` from the
  reconciled `category_scores`. Build the final `<skill-name>-review.json`/
  `.md` from the reconciled output, marking each finding's confirmation
  ("3/3 runs" vs. "1/3 runs — unconfirmed, review individually") rather
  than presenting every finding at uniform confidence.
- If `reconcile_reviews.py` reports a `fatal_error` (fewer than 2 run files
  given, a run file missing a required field, or runs that reference
  different `skill_name` values) → fix the input and rerun; a mismatched
  `skill_name` usually means one of the runs was accidentally produced
  against the wrong skill or an earlier version of it.
- Compute `overall_verdict` from the category scores: `blocked` if any
  category is `blocker`, `needs_work` if any is `major`,
  `pass_with_suggestions` if only `minor` findings remain, else `pass`.
- **Diffing two versions' static review.** Don't diff two runs by hand —
  use `scripts/diff_reviews.py <old> <new>` (`--markdown` for a
  human-readable table, `--fail-on-new` to exit 1 only when `<new>`
  introduces a finding `<old>` didn't have, `--out <path>` to write to a
  file). It auto-detects what `<old>`/`<new>` are: two skill directories
  diffs the deterministic layer (stage 1a) — no model call either side;
  two already-produced `<skill-name>-review.json` files diffs the
  qualitative layer (stage 1b) — needs full review mode to have already
  produced both files, but the diff itself is still deterministic.
  Mixing one directory and one `.json` file is rejected. When the user
  gives two skill directories (old and new version) to `skill-eval`
  directly, this diff is part of the comparative report Workflow produces
  for that case (both the static-review diff and a side-by-side cost/
  judgment table per model) — not a separate ask.

# References

- `scripts/structural_check.py` — run in Workflow step 1a to produce the
  deterministic JSON scorecard.
- `scripts/generate_static_report.py` — quick static-only Markdown report;
  see Decision Guidelines for when to use this instead of the full
  pipeline.
- `scripts/reconcile_reviews.py` — deterministic aggregation over N
  independent qualitative review runs; see Decision Guidelines'
  self-consistency entry.
- `scripts/diff_reviews.py` — deterministic diff between two skill
  directories or two `<skill-name>-review.json` files; see Decision
  Guidelines for its two modes and `--fail-on-new`/`--markdown` flags.
- `scripts/render_report.py` — run in Workflow step 4 to render the final
  Markdown report; purely mechanical, no model call.
- `references/rubric.md` — the qualitative scoring rubric; open it in
  Workflow step 1b to score description/triggering, structure, writing
  style, and safety.
- `references/preferred-structure.md` — the optional 8-section outline
  used when judging structure in Workflow step 1b.
- `references/schema.md` — the exact JSON output structure for
  `<skill-name>-review.json`/`.md`; the `overall_verdict`/
  `category_scores` shape needed to know what "blocked" actually means in
  step 1b.
- `references/severity_config.yaml` — the `check_id -> severity` table
  `structural_check.py` reads at run time; if a run's severities look off,
  check this file (not the script) first.
- `references/models_config.yaml` — the editable `default_models` list;
  see Decision Guidelines for how to extend it, persistently or per-run.
- `references/task-authoring.md` — the `tests/fixtures/tasks/<skill-name>.yaml`
  format and how to write one. See Workflow step 2.
- `references/token-capture.md` — why the "Number of Tokens" column is a
  real, measured value (read off the `Agent` tool's own return metadata),
  not an estimate, and what to do if that metadata is ever missing. See
  Workflow step 2.
- `SURVEY.md` — survey of existing eval/cost-tracking tools and why
  `skill-eval` is mostly custom-built rather than adopting one wholesale.
- `CHANGELOG-skill-review-history.md` — the version history of
  `skill-review` from before it was merged into this skill; kept as a
  historical record, not maintained going forward.
