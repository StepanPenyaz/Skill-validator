# Changelog

All notable changes to the `skill-eval` skill are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
versioning follows [SemVer](https://semver.org/).

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
