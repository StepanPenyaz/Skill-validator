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

This alternative was never needed in the end — see the correction below —
but the finding stands for its own sake: do not install Node.js/the
`claude` CLI to unblock this. Revisit this path only if some other reason
to want the CLI-subprocess harness (`claude plugin eval`'s isolated-
session-with-skill-loaded approach) comes up.

## Correction: real per-subagent usage *is* available, just not the way this spike looked for it

The investigation above is still accurate about what it checked: no
separate introspection tool, keyed on a `session_id`, can retrieve a
spawned `Agent`-tool subagent's usage after the fact, because a subagent
never exposes a `session_id` for such a tool to query.

But that's not the only path. Three independent real Workflow step-2 runs
now agree that **the `Agent` tool's own return value, for a subagent
spawned directly from a top-level conversation turn** (not through a
`Workflow` script's `agent()` wrapper — that path is unconfirmed either
way), carries real usage metadata alongside the subagent's final report —
no follow-up call, no self-reporting, no estimation:

- `../EXAMPLE-RESULTS.md` (`skill-review` self-eval, v0.10.0): `Agent`
  call returned `subagent_tokens: 89012, tool_uses: 13,
  duration_ms: 123032`.
- `../../skill-evaluation-examples/csv-cleaner/versions/v3/csv-cleaner-eval.md`:
  `Agent` call returned `subagent_tokens: 68731` for the same call whose
  subagent separately self-reported `~5,500` under the old estimate
  instruction — about 12x apart, the self-report undercounting exactly as
  predicted below.

Both real values are also consistent with the undercount direction this
document predicted for the self-report estimate: the estimate only sees
visible prompt + final-answer text, not tool definitions, intermediate
tool-call/tool-result content, or reasoning tokens, so it was always going
to read low relative to the real figure.

## Decision: use the real `subagent_tokens` value from the `Agent` tool's own result

Given 2-for-2 independent confirmations (three runs, two separate target
skills) that this metadata is actually present on the call, `skill-eval`
no longer instructs the subagent to self-report an estimate. Workflow step
2 instead reads `subagent_tokens` straight off the `Agent` tool's return
value for that call and reports it as a real number —
`tokens_estimated: false` in `render_report.py`'s input shape, no `~` /
`(estimated)` label on the rendered column.

If a future run's `Agent` call somehow doesn't carry `subagent_tokens` in
its result (e.g. because the call went through a `Workflow` script's
`agent()` wrapper instead of a direct top-level `Agent` call, which is
still unconfirmed — see above), that is a stop-and-report condition for
step 2, not a silent fallback to the old estimate: report the gap to the
user rather than guessing again, since quietly reintroducing the estimate
is exactly how this stayed unfixed through two prior confirmations already
on record.
