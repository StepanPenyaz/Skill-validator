# Changelog

All notable changes to the `skill-eval` skill are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
versioning follows [SemVer](https://semver.org/).

## [1.2.0] — 2026-09-28

### Added
- **Single-skill reports now embed the static review, not just a pass/
  fail note.** `scripts/render_report.py`'s single-skill shape gains
  `gate_check.stage_1a.findings` (rendered via
  `scripts/generate_static_report.py`'s own `render_markdown_report`,
  imported rather than reimplemented, as a `## Static Check Report`
  subsection — its `heading_level` parameter is new, letting a caller
  embed it under a bigger report's own heading) and
  `gate_check.stage_1b.category_scores`/`.review_file` (rendered as a
  `## Qualitative Review Summary` table pointing at the full
  `<skill-name>-review.md` rather than duplicating its rewrites inline).
  Both are additive and optional — a JSON payload without them (like the
  existing sample fixtures) renders exactly as before.
- **Comparative reports, for a two-version invocation.**
  `scripts/render_report.py` gains a `"report_type": "comparative"` input
  shape: `old_skill_name`/`new_skill_name`, `structural_diff`/
  `qualitative_diff` (`scripts/diff_reviews.py`'s own output, rendered via
  its `render_markdown` — also given a new `heading_level` parameter for
  the same embedding reason), and `runs[]` with per-model `old`/`new`
  cost/judgment objects rendered as one wide table (old vs. new side by
  side, with a computed token/time delta per row) instead of two separate
  tables a reader would have to line up by hand. `SKILL.md`'s Workflow now
  states the mode decision up front (single skill vs. two versions) and
  documents both step-4 shapes; the two-version case runs steps 1-3 twice
  (once per version, same model list and task fixture) and step 4 renders
  the comparative shape instead of two independent reports.
- Three new fixtures/regression checks: `render-report-full-single-sample.json`
  (embedded static findings + qualitative summary), `render-report-comparative-sample.json`
  (built from real `diff_reviews.py` output against the existing
  `diff-old-skill`/`diff-new-skill` and `version-diff` fixtures, not
  hand-typed), and `render-report-missing-tokens-sample.json` extended to
  also exercise the comparative table's per-side `null`-tokens handling.

### Fixed
- `tests/run_regression.py`'s `run()` helper decoded a subprocess's stdout
  using the platform's default locale codec (cp1252 on Windows) instead of
  the UTF-8 every script here actually writes (each reconfigures its own
  `sys.stdout` to UTF-8, for the em dashes/arrows/bullets they print) —
  silent mojibake (`→` became `â†’`) rather than a decode error, so it went
  unnoticed until a new comparative-report test asserted on an arrow
  character directly. Fixed by passing `encoding="utf-8"` explicitly to
  `subprocess.run`.

## [1.1.0] — 2026-09-28

### Changed (breaking: run behavior)
- **The pipeline no longer stops on a Blocker/`blocked` static-review
  result.** Previously, `compliance_errors` from stage 1a or an
  `overall_verdict` of `blocked` from stage 1b would halt the Workflow
  before the target skill ever ran — no report was produced at all. Now
  both stages always run, the target skill always gets executed in step 2
  regardless of what they found, and the final report always gets
  rendered — with the Blocker/`blocked` result carried forward and shown
  as a prominent warning (`render_report.py`'s `gate_check` handling: a
  distinct callout block listing the actual `compliance_errors` entries
  and/or blocked categories, not folded into the routine "passed,
  evaluation proceeded" note). Motivation: a report with real statistics
  is always more useful than no report at all, and a Blocker is exactly
  the kind of thing a reader needs surfaced clearly, not hidden behind a
  refusal to run.
- **A missing task fixture no longer pauses the run to ask.** Workflow
  step 2 now authors `tests/fixtures/tasks/<skill-name>.yaml` itself,
  following `references/task-authoring.md`'s methodology exactly (same
  sourcing priority: description/"When to Use", `CHANGELOG.md`-driven
  change coverage, a "When NOT to Use" boundary case), saves it, and
  continues the run with it. This is not the same as the old "never
  invent tasks on the fly" rule, which was about *unsaved, improvised*
  prompts defeating the point of a frozen fixture — an auto-authored
  fixture is saved to disk and frozen from that point on exactly like a
  hand-authored one; only the "who wrote it, and whether the run pauses to
  ask first" part changed. The final report notes when a run's fixture was
  auto-generated (`task_fixture_auto_generated: true` in
  `render_report.py`'s input shape) so a later reader knows to go look at
  what it actually asked before relying on it for a comparison.
- **A per-model token-capture failure no longer aborts the whole run.**
  If `subagent_tokens` is absent from the `Agent` tool's result for one
  model's call (see `references/token-capture.md`), that model's `tokens`
  is now recorded as `null` and the remaining models still get evaluated;
  `render_report.py`'s `format_tokens` renders an explicit "capture
  failed" note for that row instead of a plain dash (which could misread
  as "no run happened") or a silent fallback to the discredited
  self-reported estimate.

### Added
- `scripts/render_report.py`: `gate_check.stage_1a.compliance_errors` and
  `gate_check.stage_1b.blocked_categories` in the input shape, rendered as
  a prominent warning block when either is non-empty/`blocked`;
  `task_fixture_auto_generated` in the input shape, rendered as a note
  when `true`. Two new fixtures (`render-report-blocked-sample.json`,
  `render-report-missing-tokens-sample.json`) and 3 new regression checks
  covering both, plus the existing sample's unchanged rendering (backward
  compatible — no `compliance_errors`/`blocked_categories`/
  `task_fixture_auto_generated` keys renders exactly as before).

## [1.0.0] — 2026-09-28

### Changed (merge, breaking)
- **Merged `skill-review` into `skill-eval`.** `skill-review` no longer
  exists as a separately-triggerable skill; its static-review layer (gate
  mode + full review mode, self-consistency, version-diffing) is now this
  skill's Workflow step 1, and its scripts/references/fixtures live under
  `skill-eval/` directly:
  - `scripts/{structural_check,generate_static_report,reconcile_reviews,diff_reviews}.py`
    moved from `skill-review/scripts/` — unchanged, self-contained,
    path-relative-to-`__file__` logic, so no code changes were needed.
  - `references/{rubric.md,schema.md,preferred-structure.md,severity_config.yaml}`
    moved from `skill-review/references/`.
  - `tests/fixtures/{bad-skill,good-skill,clean-skill-with-tricky-patterns,
    consistency-runs,diff-old-skill,diff-new-skill,version-diff}` moved from
    `skill-review/tests/fixtures/`; `tests/run_regression.py` now runs both
    skills' former regression suites as one (18 checks).
  - `skill-review/README.md`'s repo/dev-facing content (two entry points
    table, what it validates, self-consistency, retuning severity, diffing
    across versions) folded into this `README.md`. `skill-review/CHANGELOG.md`
    kept as `CHANGELOG-skill-review-history.md`, frozen, not maintained
    going forward.
  - `SKILL.md` rewritten: frontmatter `description`/"When to Use" now also
    covers `skill-review`'s former triggering phrases ("review this skill",
    "is this SKILL.md any good", "what's wrong with my skill"); Workflow
    step 1's two stages now run locally (`scripts/structural_check.py`,
    then an inlined full-review-mode pass against `references/rubric.md`)
    instead of pointing at a separate skill's `SKILL.md`.
  - **`scripts/structural_check.py`/`generate_static_report.py` still work
    standalone**, independent of the rest of this skill's pipeline — a
    quick pre-check (`python3 skill-eval/scripts/structural_check.py <dir>`)
    doesn't require going through the full Workflow. This was an explicit
    design goal for the merge, not an incidental side effect.
  - Root `README.md`, `.github/workflows/tests.yml`, and
    `scripts/package_skill.py`'s comments updated for the single-skill
    layout (one CI job instead of two).
  - **What did not change in this release:** the static-review stages still
    hard-stop the Workflow on a Blocker/`blocked` verdict, and Workflow
    step 2 still stops and asks the user when no task fixture exists yet.
    Both are being revisited in a follow-up release (removing blocking
    behavior so a run always produces a report) — this release is the
    structural merge only.

## [0.13.0] — 2026-09-23

### Changed
- `references/token-capture.md`: formalized the correction
  `EXAMPLE-RESULTS.md` (v0.10.0) had already flagged but never turned into
  an actual decision change — a third independent real run (`skill-eval`
  against `csv-cleaner` v3) reproduced the same gap between a self-reported
  estimate and the `Agent` tool's real `subagent_tokens` metadata (~5,500
  vs. 68,731, ~12x), for the same reason: nothing had updated the
  Decision section or Workflow step 2 to stop prescribing the estimate.
  Decision changed to: read `subagent_tokens` off the `Agent` tool's own
  return value for a subagent spawned directly from a top-level turn; a
  missing `subagent_tokens` is now a stop-and-report condition, not a
  silent fallback to the old estimate.
- `SKILL.md` Workflow step 2: subagents are no longer asked to self-report
  a token estimate; step 2 now reads the real `subagent_tokens` value and
  reports `tokens_estimated: false`. Also now explicit that the `Agent`
  call must be made directly from the top-level turn, not through a
  `Workflow` script's `agent()` wrapper (unconfirmed whether that path
  surfaces the same metadata).
- `README.md`: "Number of Tokens" column described as a real measured
  value instead of a caveat about checking which of two mechanisms
  produced a given number.

### Fixed
- No prior version actually applied `EXAMPLE-RESULTS.md`'s own finding to
  the skill's prescribed behavior; every real run since kept rediscovering
  and re-flagging the same gap instead of it being resolved once.

## [0.12.0] — 2026-09-20

### Added
- `README.md`: three new sections closing the remaining doc gaps —
  "Running it end-to-end" (there's no CLI entrypoint for the full run;
  ask a Claude session with `skill-eval` available, with two worked
  invocation examples), "Adding a task fixture for a new skill" (a short
  pointer version of `references/task-authoring.md`'s methodology), and
  "Reproducibility: what must stay constant" (the task fixture, the
  model list, and which `skill-review` version ran the gate check all
  have to match for two runs to be comparable — plus judge variance as
  an acknowledged, uncontrolled-for limitation).
- Root `README.md`: replaced the `<future-skill>/` placeholder in the
  Layout tree with the real `skill-eval/` entry, and added a `##
  skill-eval` section mirroring the existing `## skill-review` section.

## [0.11.0] — 2026-09-20

### Added
- `tests/run_regression.py` (new file): `skill-eval`'s own regression
  suite, following `skill-review/tests/run_regression.py`'s pattern
  exactly (plain assertions over subprocess calls to real CLI
  entrypoints, no test framework). 7 checks: the gate-check signal
  `structural_check.py` produces for `bad-skill` (compliance_errors
  non-empty) and `clean-skill-with-tricky-patterns` (empty);
  `models_config.yaml`'s shape and default content; `render_report.py`'s
  table rendering against a fixed sample input (`tests/fixtures/
  render-report-sample.json`), including pipe-character escaping and the
  gate-check note; the zero-runs edge case
  (`render-report-empty.json`); a self-check (`skill-eval` itself passes
  `skill-review`'s gate mode); and packaging. Explicitly excludes
  anything requiring a live model call.
- `.github/workflows/tests.yml`: new `skill-eval` job (sibling to the
  `skill-review` job) running this suite on every push and PR.
- Refreshed `README.md`'s "Status" section (was still describing step 2
  as "in progress" after #38 already landed it) and added a "Local
  testing" section; updated the repository layout tree to match what
  actually exists now (`scripts/render_report.py`, `SURVEY.md`,
  `EXAMPLE-RESULTS.md`, the new `tests/` contents).

## [0.10.0] — 2026-09-20

### Added
- `EXAMPLE-RESULTS.md`: the first real, end-to-end run of `skill-eval`'s
  complete Workflow, targeting `skill-review` itself with
  `tests/fixtures/tasks/skill-review.yaml`'s 3 tasks — not a synthetic
  example. Gate check passed both stages (9 structural warnings, all
  confirmed as the scanner's own self-referential false positives;
  `overall_verdict: pass` on the qualitative review). One `sonnet` run
  covering all three tasks: 89,012 tokens, 2m 3s, a 4-bullet judgment
  grounded in specific things the subagent actually did (correctly
  triaged gate-mode-only vs. full-review-mode per task, correctly
  dismissed a known false positive, correctly exercised the 1.6.0
  cost-conditional-scan mechanism, correctly declined an out-of-scope
  boundary question).

### Fixed (discovered while running the demo)
- **`references/token-capture.md`'s conclusion was incomplete.** The
  step-2 subagent, spawned through the top-level `Agent` tool directly,
  returned real usage metadata (`subagent_tokens`, `duration_ms`)
  alongside its final report — no self-reporting or estimation needed.
  The original research spike (#23) checked whether a *separate*
  introspection tool could retrieve a spawned subagent's usage after the
  fact and correctly found no mechanism for that — but didn't check
  whether the `Agent` tool's own result already carries it. Flagged
  prominently in `EXAMPLE-RESULTS.md` rather than silently revising
  Workflow step 2 here — confirming how far this generalizes (a
  Workflow's `agent()` wrapper vs. a direct `Agent` tool call; every
  invocation vs. this one) is its own follow-up.

## [0.9.0] — 2026-09-20

### Added
- Workflow step 2 (run the target skill per model), replacing its stub —
  the last of the four Workflow steps to go from stub to real. For each
  model in the resolved model list, spawns one `Agent`-tool subagent
  covering *all* tasks from `tests/fixtures/tasks/<skill-name>.yaml` in a
  single conversation (not one subagent per task — that's what makes "one
  row per model" in the final table a real per-model cost rather than a
  single arbitrary task's cost). The subagent's prompt explicitly tells it
  to read the target skill's `SKILL.md` and follow it, since a target
  skill sitting in this repo isn't necessarily auto-loaded for a fresh
  subagent, and to self-report an approximate token count
  (`Approx. tokens used: ~N (estimated)`) as the last line of its final
  report, per `references/token-capture.md`'s decision — the orchestrator
  captures wall-clock time itself and parses the token estimate back out
  of that same final report, rather than requesting it as a separate
  side-channel value.
- Two new Rules: never invent tasks on the fly if no fixture exists for
  the target skill; always one subagent per model covering every task,
  never one subagent per task.
- A new Decision Guidelines entry for the missing-task-fixture case:
  don't guess, tell the user, offer to author one per
  `references/task-authoring.md`.

## [0.8.0] — 2026-09-20

### Added
- `scripts/render_report.py` (new file): renders the final Markdown
  report from already-collected run data — purely mechanical, no model
  call, same role `skill-review/scripts/generate_static_report.py` plays
  there. Takes a JSON input (`skill_name`, `gate_check` stage results,
  `runs[]` with `model`/`tokens`/`tokens_estimated`/`time_seconds`/
  `judgment`) and renders one table (`Model Used | Number of Tokens |
  Time Spent | Claude's Judgment`) led by a gate-check note that's always
  shown, even on a pass, so the report is self-contained. Escapes `|`/
  newlines in judgment text so a bullet can't break the table.
- Workflow step 4 (render the report), replacing its stub-list entry:
  assemble the collected data, run `render_report.py`, and save as
  `<skill-name>-eval.md` — mirroring `skill-review`'s
  `<skill-name>-review.md` convention exactly, including the
  `/mnt/user-data/outputs/`-if-present, next-to-the-skill-directory-
  otherwise save location.

## [0.7.0] — 2026-09-20

### Added
- Workflow step 3 (judgment): for each model's run, read its transcript/
  output and write 2-4 short bullet points — concrete, verifiable
  observations, not a score, not an overall summary sentence. Includes a
  worked example (a hypothetical CSV-cleanup run) so the instruction
  isn't left abstract.
- A Rules entry requiring every judgment bullet to name something
  specific and checkable from that particular run, not generic filler
  that could describe any run on any skill.

## [0.6.0] — 2026-09-20

### Added
- `tests/fixtures/tasks/skill-review.yaml`: the first real task set,
  following `references/task-authoring.md`'s format, targeting
  `skill-review` itself — 3 tasks: a happy-path "what's wrong with my
  skill" request against `bad-skill` (substantive findings to judge, not
  a no-op); a task specifically targeting the 1.6.0 cost-conditional
  security-scan gate against `good-skill` (should report
  `metrics.security_scan.skipped: true`, so a future regression in that
  gate shows up as a changed judgment/cost); and a "When NOT to Use"
  boundary case checking `skill-review` correctly declines a runtime
  task-success-rate question rather than over-triggering into a claim it
  can't back up. This is the fixture the end-to-end demo (#27) will run.

## [0.5.0] — 2026-09-20

### Added
- `references/models_config.yaml`: editable `default_models` list (just
  `sonnet` out of the box) for Workflow step 2, following the same
  externalized-policy pattern as `skill-review`'s
  `references/severity_config.yaml`. Documented, in both `SKILL.md`
  (Decision Guidelines) and `README.md`, the two ways to extend it for a
  model comparison: persistently (edit the file) or one-off (ask for
  extra models at invocation time, for that run only).
- `README.md`'s "Status" section now reflects that Workflow step 1 (both
  gate-check stages) is actually done, not still a stub.

## [0.4.0] — 2026-09-20

### Added
- `references/task-authoring.md`: defines the `tests/fixtures/tasks/
  <skill-name>.yaml` format (`id`/`prompt`/`source` per task) and the
  authoring methodology — pull a happy-path prompt from the target
  skill's own description, at least one task targeting whatever a
  version's `CHANGELOG.md` entry actually changed, one "When NOT to Use"
  boundary case, 3-5 tasks as a starting guideline. Authoring is a manual
  step for now, matching how `skill-review`'s `bad-skill` fixture was
  hand-authored. No task set written yet for any specific skill — that's
  the next step, now that the format is settled.

## [0.3.0] — 2026-09-20

### Added
- Workflow step 1 (gate check), two stages, run in order, stopping at the
  first that fails: 1a runs `skill-review`'s deterministic gate mode
  (`structural_check.py`) and stops if `compliance_errors` is non-empty;
  1b — only reached if 1a passes — runs `skill-review`'s qualitative full
  review mode and stops if `overall_verdict` is `blocked`. Both are
  needed: gate mode alone can't catch a blocking issue that only a model
  reading the skill would recognize (e.g. a safety-relevant pattern that's
  an actual problem in context, versus just a regex candidate). 1a runs
  first since it's free (no model call) and catches most breakage, so
  there's no reason to spend a model call on 1b for a skill that was
  already going to fail 1a.
- Rules entries making the stop condition non-optional at either stage,
  and requiring 1a to run before 1b. Decision Guidelines entries covering
  non-blocking-but-not-clean results from both stages
  (`structural_warnings` from 1a; `needs_work`/`pass_with_suggestions`
  from 1b): proceed, but carry them forward and surface them alongside the
  final report rather than silently dropping them.

## [0.2.0] — 2026-09-20

### Added
- `SURVEY.md`: survey of existing eval/cost-tracking tools (`claude plugin
  eval`, promptfoo, Braintrust, LangSmith, DeepEval, the generic
  LLM-as-judge pattern) with adopt/adapt/reject verdicts and a final
  recommendation. Headline finding: Anthropic's own `claude plugin eval`
  is the closest existing thing to this skill's execution harness, worth
  adapting rather than building from nothing — but no surveyed tool
  renders the specific per-model comparison table this skill needs, so
  that layer stays custom regardless.
- `references/token-capture.md`: resolves the "how does skill-eval get a
  token count" question from the scaffold's stubbed Workflow step 2. No
  mechanism in this environment can retrieve a spawned Agent-tool
  subagent's real token usage (investigated directly, not assumed) — an
  `Agent`-tool subagent never exposes a `session_id` for any
  introspection tool to key on. The `claude` CLI subprocess path that
  would give real numbers needs Node.js, not installed in this
  environment; decided not to install it to unblock this now. Token count
  is therefore a labeled estimate (`(prompt + response length) / 4`),
  explicitly presented as approximate and known to undercount — never as
  a measured value.

## [0.1.0] — 2026-09-20

### Added
- Initial scaffold: `SKILL.md` frontmatter, `Purpose`/`When to Use`/`When
  NOT to Use` sections, and a stubbed-out `Workflow` listing the planned
  steps (gate check → run target skill per model → judge → render table).
  No working behavior yet — see the repo's open `skill-eval:` issues for
  the steps that fill this in.
