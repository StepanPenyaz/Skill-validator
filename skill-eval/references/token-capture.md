# Token, time and cost capture

`skill-eval` reports tokens, time and cost for each model run. All three must be measured values.

## Where the numbers come from

- **Tokens:** the `Agent` tool's own result for the run's subagent carries `subagent_tokens`, a single total (input and output together). The orchestrator copies it.
- **Time:** the elapsed time of that same `Agent` call (`duration_ms`, or a timestamp taken before and after the call).
- **Cost:** `tokens / 1,000,000 × blended_usd_per_million` from `models_config.yaml`. The blended rate is the midpoint of the model's input and output price, because the total is not split. The cost is therefore computed from a measured token count, and is approximate to that extent.

## Why not ask the subagent for its own count

A subagent can only see its visible prompt and answer. It cannot see tool definitions, tool results or reasoning tokens. In a past run a subagent reported about 5,500 tokens for a call whose harness-reported total was 68,731, about 12 times lower. So the subagent's own number is never used.

## When a number is missing

If the `Agent` result carries no `subagent_tokens` or no duration (for example when the run went through a `Workflow` script's `agent()` wrapper), write `unavailable` in `run_on_<model>_report.md`. Do not estimate. The cost is `unavailable` too. Continue with the next model.
