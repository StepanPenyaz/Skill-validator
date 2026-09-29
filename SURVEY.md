# Survey: existing tools for evaluating a skill's runtime cost and behavior

Research spike for GitHub issue #26, part of the broader PBI: "find the
existing patterns and tools that already measure whether a skill does its
job well, at a reasonable cost, and the quality-to-cost trade-off, and work
out which of them we can use."

`skill-eval`'s design at the time of this survey: run a target skill
against real tasks, once per model tested, and report one Markdown table —
`Model Used | Number of Tokens | Time Spent | Claude's Judgment` — where
the judgment is a short freeform qualitative note, deliberately **not** a
numeric score.

## Candidates

### claude plugin eval (Anthropic CLI) — adapt

GA as of Claude Code v2.1.269 (docs at `code.claude.com/docs/en/plugin-evals`).
You write cases (a `prompt.md` + `graders/` per case) under a plugin's
`evals/` directory; `claude plugin eval .` starts a fresh, isolated,
non-interactive `claude -p` session with only the target plugin/skill
loaded, runs the prompt to completion (real tool calls happen), and grades
the transcript/files with six grader types — four free/deterministic
(`regex`, `tool_used`, `tool_order`, `file_exists`) and two billable
judge-model graders (`llm` = rubric PASS/FAIL by majority-of-3 vote,
`baseline` = compare against a reference transcript). By default every
case also re-runs with no plugin loaded (the "no-plugin baseline"),
producing WITH/W-OUT/Δ scores. `aggregate-result.json` and the HTML report
carry `costUsd` (list-price estimate) and `durationSeconds` per suite/case,
plus `--model`/`--judge-model` flags — but each invocation targets exactly
one model; there's no built-in multi-model comparison table.

**Rationale**: this is the closest thing that exists to `skill-eval`'s
harness — it already spawns an isolated Claude Code session with a skill
loaded, drives it through a real task with real tool calls, and reports
per-run wall-clock duration and cost, covering 2 of `skill-eval`'s 3
required columns almost for free. It fights our actual design in three
ways: its grading is a numeric pass/fail fraction from majority LLM-judge
votes (we explicitly want freeform qualitative judgment, not a score); its
whole framing is a with/without-plugin Δ to prove a plugin adds value
rather than a cross-model comparison (you'd loop `--model` yourself and
hand-assemble the table); and cost is a dollar estimate, not a raw token
count. **Adapt it**: either drive cases through it and post-process
`aggregate-result.json` for time/cost while using an `llm` grader's judge
explanation text as the freeform note, or borrow its
isolated-session-with-skill-loaded pattern for a purpose-built script.

### LLM-as-judge pattern (generic, freeform form) — adopt

Not a product, a technique: prompt a second model to evaluate a first
model's output. Well-documented failure modes remain — positional bias in
pairwise comparison, self-preference when judge and generator share a
family, reference-dependency on open-ended tasks, and lower reliability
specifically for numeric/absolute scoring than for pairwise or binary
verdicts.

**Rationale**: `skill-eval`'s design already sidesteps the pattern's
worst-documented failure mode by asking for a short freeform paragraph
rather than a 1-5 or 0-1 numeric score — exactly the scoring shape research
says is least reliable for LLM judges. Adopt the pattern in that specific
form (single-answer, non-comparative, non-numeric) for the "Claude's
Judgment" column; do **not** adopt the more common rubric-with-numeric-score
variant that `claude plugin eval`, promptfoo, and DeepEval all default to.

### promptfoo — adapt

Open-source MIT eval framework. Its "Test Agent Skills" guide
(`promptfoo.dev/docs/guides/test-agent-skills`) is directly on-topic: it
runs real end-to-end agent workflows (not prompt-in/text-out) via custom
providers wrapping the Claude Agent SDK, captures native tool calls into
trajectory assertions (`tool-used`, `tool-sequence`), and ships built-in
`cost` and `latency` assertion types with thresholds, plus
OpenTelemetry-based tracing recording `gen_ai.usage.input_tokens`/
`output_tokens` per span. Explicitly demonstrates running the same eval
config across multiple provider SDKs for comparison.

**Rationale**: the best-fitting third-party general-purpose tool — real
agent/tool-call execution, per-call token capture, and multi-provider
comparison are all architecturally close to what `skill-eval` needs. But
it has no native concept of a Claude Agent Skill/`SKILL.md`; you'd write
your own provider that shells out to Claude Code, no different in kind
from the adapter `claude plugin eval` already has built in. Its grading is
assertion/score-oriented, so a single freeform paragraph still means
suppressing its scoring UI and reading the judge's rationale text. Worth
borrowing its `cost`/`latency` assertion design and multi-provider
comparison pattern rather than adopting it as the harness.

### Braintrust — reject

Hosted eval + observability platform. Traces capture every LLM call,
retrieval step, and tool invocation as a span carrying input/output
tokens, latency, and estimated cost.

**Rationale**: an observatory you send traces to — it doesn't run tasks or
spawn agents itself, so it covers none of "run the target skill against
real tasks." You'd still build the exact same custom harness and then
additionally instrument it to emit Braintrust-shaped spans. For cost
capture, it adds nothing available for free from the Claude API's own
`usage` object or Claude Code's own session cost summary, at the price of
a hosted account and vendor lock-in for a project whose design is a
self-contained Markdown table checked into a skill's own repo.

### LangSmith — reject

LangChain's hosted observability and eval platform. Automatically
attributes token usage, latency, and cost to traces; offers online
LLM-as-judge, code-based, and multi-turn evaluators run against production
traces.

**Rationale**: same structural mismatch as Braintrust — a place instrumented
traces land, not a task runner. Its evaluators assume an ongoing stream of
production traffic, an infrastructure shape `skill-eval` (a one-off,
per-model, per-task benchmark run) doesn't have. Pulls in a LangChain
dependency for a benefit already free from the Claude API's usage object.

### DeepEval — reject

Open-source Python LLM eval framework (pytest-style). Ships 50+ metrics
including agent-trajectory metrics, scored over a trace you instrument
yourself with `@observe` decorators.

**Rationale**: a metrics/scoring library over traces from an agent you've
already built — no concept of a Claude Agent Skill or Claude Code's
session/tool-use transcript, so using it means writing the same custom
harness anyway, then retrofitting `@observe` tracing for no net savings.
Its metrics default to numeric/pass-fail scores, the opposite of our
explicit non-numeric requirement, and its cost tracking is scoped to the
judge's own calls, not the target run's spend.

### Claude API / Agent SDK `usage` object — adopt

Every Messages API response returns a `usage` object
(`input_tokens`/`output_tokens`/`cache_creation_input_tokens`/
`cache_read_input_tokens`); `client.messages.count_tokens()` gives an exact
pre-flight count.

**Rationale**: if `skill-eval`'s harness ever drives the target skill
directly through the Messages/Agent SDK, summing `response.usage` across
every turn gives the "Number of Tokens" column exactly, for free, with zero
dependency.

### Claude Code's own session/cost tracking — adopt

Claude Code accumulates per-session token totals and a list-price dollar
estimate over a session's life, surfaced via `/cost` and (in this
environment) the bundled `explain-usage` skill; `claude plugin eval` reuses
this same accounting for its `costUsd`/`durationSeconds` fields.

**Rationale**: the right token/cost source whenever the harness shape is
"spawn a Claude-Code-driven session with the skill loaded" rather than a
raw API call — it already reflects real system-prompt/tool-schema overhead
a bare API call wouldn't reproduce, and `claude plugin eval` already proves
it out as a data source.

### Wall-clock timing — adopt

Time the run start-to-finish, no instrumentation needed. `claude plugin
eval` already reports this as `durationSeconds`.

**Rationale**: nothing more sophisticated is needed for the "Time Spent"
column; every other candidate surveyed produces it as a side effect of
running the task at all.

## Recommendation

**Adopt outright**, no external product required: the freeform
(non-numeric, non-comparative) LLM-as-judge pattern for the judgment
column; the Claude API's `usage` object or Claude Code's own session
cost/token accounting for the tokens column, depending on harness shape;
plain wall-clock timing for duration.

**Adapt rather than adopt wholesale**: `claude plugin eval` is the closest
existing execution harness (isolated session, skill loaded, real tool
calls, per-run cost+duration already reported) and should be the starting
point if/when the runtime environment can support it — either driving
`skill-eval`'s task set through it and post-processing
`aggregate-result.json`, or copying its isolated-session-with-skill-loaded
pattern into a purpose-built script — in both cases discarding its
with/without-plugin Δ framing and numeric grader for a single freeform
judge call. promptfoo's "Test Agent Skills" guide is worth the same
treatment if the team would rather stay inside an existing eval framework.

**Build custom, unavoidably**: the actual per-model Markdown table
`skill-eval` needs — one row per model, columns = tokens / wall-clock time
/ a short freeform note, explicitly not a score — has no existing
counterpart. `claude plugin eval` renders a WITH/W-OUT/Δ scored HTML+JSON
report; promptfoo renders its own eval-matrix UI/JSON; Braintrust/LangSmith
render hosted dashboards. None produce a plain, committable,
model-comparison table. That aggregation/formatting layer, plus the loop
that runs the chosen harness once per target model, is genuinely new code
regardless of which harness sits underneath it.

**Reject wholesale**: Braintrust, LangSmith, DeepEval — all three require
an already-running, instrumented agent and only add value once traces are
flowing into them; none execute a task or understand a Claude Agent Skill,
so none replace the harness-building work, and their cost/scoring
value-adds duplicate what the Claude API usage object and a freeform judge
call already give for free.

## Left uncovered

Even after adopting/adapting the best candidates, four things stay
uncovered by anything surveyed:

1. No tool renders `skill-eval`'s specific report shape — that renderer is
   unavoidably custom code.
2. No third-party platform (promptfoo, Braintrust, LangSmith, DeepEval) has
   any native understanding of a Claude Agent Skill or `SKILL.md` — every
   one needs a hand-written adapter just to drive the target skill at all,
   so "adopting" any of them only ever saves report/scoring plumbing, never
   harness-building.
3. None of the cost-tracking mechanisms surveyed produce a normalized
   quality-per-dollar efficiency figure for tasks that legitimately take a
   different number of turns per model — they all report what was spent,
   not whether it was a good trade. The actual quality-to-cost judgment the
   parent PBI asks for still has to be made by a human reading
   `skill-eval`'s table, not computed by any surveyed tool. This matches
   our own design decision (no ratio, just the table).
4. Run-to-run instability in a single freeform LLM-judge paragraph
   (documented bias/variance in the LLM-as-judge literature) isn't solved
   by anything surveyed — `claude plugin eval`'s majority-of-3-vote scheme
   only works for discrete pass/fail, not for stabilizing a freeform
   paragraph. `skill-eval` will need its own mitigation (a fixed
   low-variance judge prompt, or simply documenting the variance as a known
   limitation) rather than inheriting one.
