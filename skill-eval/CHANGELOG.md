# Changelog

All notable changes to the `skill-eval` skill are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
versioning follows [SemVer](https://semver.org/).

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
