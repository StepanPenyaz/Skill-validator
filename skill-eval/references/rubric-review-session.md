# Rubric Review Session

Settings for the Claude session that runs the rubric review (`skill-eval` step 2).
The orchestrator reads these two values and passes them to the rubric-review subagent.

| Setting | Value |
|---|---|
| model | opus |
| token_limit | 60000 |

- `model`: any name from `models_config.yaml`'s `pricing` table.
- `token_limit`: the most tokens the rubric-review subagent may use. If the review is not finished when the limit is near, the subagent must stop and say which rubric categories it did not cover.
