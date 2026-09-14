# Changelog

All notable changes to the `skill-eval` skill are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
versioning follows [SemVer](https://semver.org/).

## [0.3.0] — 2026-09-20

### Added
- Workflow step 1 (gate check): runs `skill-review`'s gate mode against
  the target skill directory before anything else and stops immediately
  if `compliance_errors` is non-empty, reporting the failure verbatim
  instead of proceeding.
- A Rules entry making the stop condition non-optional, and a Decision
  Guidelines entry covering `structural_warnings`: not blocking, but
  carried forward and surfaced alongside the final report rather than
  silently dropped.

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
