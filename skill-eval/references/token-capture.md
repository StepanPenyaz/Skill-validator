# Token and time capture: investigation and decision

Research spike for GitHub issue #23: how does `skill-eval` get a
per-subagent token count and wall-clock time, given it executes the target
skill via this environment's `Agent` tool (one subagent per model tested)?

## Wall-clock time — solved, no investigation needed

Timestamp before and after each `Agent` tool call. No instrumentation, no
open question. `claude plugin eval` (see `../SURVEY.md`) confirms this is
the same approach used by the closest existing comparable tool
(`durationSeconds`).

## Token count — investigated, no real mechanism found

Checked every plausible avenue for the orchestrating session to retrieve a
spawned `Agent`-tool subagent's token usage after the fact:

- `mcp__ccd_session_mgmt__get_session`, `list_sessions`,
  `search_session_transcripts`: return session metadata (title, branch,
  recency) or transcript text — no token/cost field of any kind.
- `mcp__ccd_session_mgmt__list_events`: returns a plaintext rendering of a
  session's turns and tool calls — transcript text only, no structured
  usage metadata.
- `mcp__scheduled-tasks__list_task_runs` / `list_scheduled_tasks`: return
  status, timestamps, and a one-line summary per run — no token counts or
  cost.
- Keyword sweeps via `ToolSearch` for "token", "cost", "usage", "context
  window" surfaced nothing else. The only usage-related thing in this
  environment is the `explain-usage` *skill* ("explain where this
  session's tokens went"), which explains the orchestrating session's own
  usage after the fact — not a tool that can be pointed at an arbitrary
  spawned subagent to retrieve its usage programmatically.

**The blocking issue isn't just "no tool exposes this" — it's structural.**
All of the session-introspection tools above key on a `session_id` that
`list_sessions`/`search_session_transcripts`/a scheduled-task run hand you.
Those are top-level CCD sessions (separate windows/tabs/scheduled runs). An
`Agent`-tool subagent is not one of those — it never receives or exposes a
`session_id` to its caller. So even a tool that *did* carry usage data
would have nothing to query it with for this specific case.

## The one real alternative found, and why it's not being used yet

Anthropic's own `claude` CLI, run non-interactively
(`claude -p "<task>" --model <name> --output-format json`), is documented
to return a JSON envelope including a real `usage` object (input/output/
cache tokens) and `total_cost_usd` per invocation — exact numbers, no
estimation. This is the same underlying mechanism `claude plugin eval`
(see `../SURVEY.md`) already uses, and would resolve this issue outright if
usable.

**It isn't usable in the environment `skill-eval` is being developed in**:
there's no Node.js/npm installed at all (`node`/`npm`: command not found),
and the `claude` CLI is an npm package (`@anthropic-ai/claude-code`) — it
can't run without Node.js first. This was checked directly (not assumed).

Decision made: **do not** install Node.js/the `claude` CLI to unblock this
right now. Revisit this path if/when this project moves to an environment
that already has Node.js, or if installing it is later judged worth doing
— the harness pattern (`claude plugin eval`'s isolated-session-with-
skill-loaded approach) stays a valid future direction; it just isn't
buildable today, here.

## Decision: fallback (B), token count is an estimate

Since neither a real introspection mechanism nor the CLI-subprocess
alternative is available, `skill-eval` uses a labeled estimate instead of
a measurement:

- Each spawned subagent is instructed, as the last step before returning
  its final report, to append an approximate token count computed as
  `(prompt length + final report length) / 4` (a standard characters-per-
  token rule of thumb).
- The orchestrating workflow step reports this number in the "Number of
  Tokens" column **explicitly labeled as an estimate** (e.g. `~1,850
  (estimated)`), never presented as a measured value.
- This estimate is known to systematically **undercount** true usage: it
  can only see the visible prompt and final-answer text, not the system
  prompt, tool definitions, intermediate tool-call/tool-result content, or
  any internal reasoning tokens. Anyone reading `skill-eval`'s output
  should treat the token column as directionally useful for comparing
  models against each other in relative terms, not as an accurate absolute
  cost figure.

This decision should be revisited whenever the CLI-subprocess path becomes
available — it changes an estimated column into a measured one with no
other change to `skill-eval`'s design.
