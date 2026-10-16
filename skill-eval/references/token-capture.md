# Token, time and cost capture

`skill-eval` reports tokens, time and cost for each model. All three must be measured values.

## Where the numbers come from

`scripts/run_skill.py` runs every case in its own `claude -p` process with `--output-format stream-json`. The final `result` event of that process carries the numbers, and the script saves them in `<input>.json` next to the output:

- **Tokens:** `usage` gives input, output, cache read and cache creation tokens. `Tokens used` in `run_on_<model>_report.md` is their sum, so the split is also written in the report. Cache reads are cheap but they are tokens the model processed.
- **Cost:** `total_cost_usd` as reported by the process. It is the real figure for that run, not an estimate from a blended price.
- **Time:** `duration_ms` of the process.
- **Turns and tools:** `num_turns`, and the tool calls counted in the transcript (`<input>.jsonl`). The transcript also shows whether the `Skill` tool was used.

`Tokens used`, `Time spent` and `Total cost` in `run_on_<model>_report.md` are means per full run (all inputs), over the model's runs.

## When a number is missing

If the process did not return a result (not logged in, killed by the timeout, crashed), the case is recorded as `failed` with the reason, and its numbers are `unavailable`. A run report value is `unavailable` when any case of a run did not report it. Do not estimate. A model with too few complete runs is reported as `insufficient`.

## Why not ask the model for its own count

A model can only see its visible prompt and answer, not tool definitions, tool results or reasoning tokens. In a past run a subagent reported about 5,500 tokens for a call whose harness-reported total was 68,731, about 12 times lower. Only numbers reported by the harness are used.
