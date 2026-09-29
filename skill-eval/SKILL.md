---
name: skill-eval
description: Evaluates a Claude Agent Skill end to end and writes one final report. It checks the skill's structure, reviews it against a rubric, runs it on several Claude models using evaluation inputs, measures tokens, time and cost, and compares the produced outputs with verified outputs. Use this whenever the user asks to evaluate, benchmark, audit, review, or measure a skill ("evaluate this skill", "how much does this skill cost to run", "how does this skill do on Opus vs Sonnet", "is this SKILL.md any good"). Also use it to compare two versions of the same skill (V1 vs V2). For a quick structure check only, tell the user to run /skill-static-review instead.
metadata:
  version: "1.0.0"
  maintained_by: "Claude Code Skill Evaluation project"
---

# Purpose

`skill-eval` answers four questions about a target skill and puts the answers in one report:

1. Does `SKILL.md` follow `references/preferred-structure.md`? (structure check)
2. Do its sections mean what they should, and is it safe? (rubric review)
3. Does it do its job on real inputs, and what does that cost? (runs on several models)
4. How close is each produced output to the verified output? (output comparison)

It can also compare two versions of one skill.

Every step that needs Claude runs in its own subagent with a clean context. The main session organises the work and copies numbers. It never judges the target skill itself.

# When to Use

- The user wants a full evaluation of a skill, or a cost and behaviour measurement.
- The user wants V1 and V2 of a skill compared.

# When NOT to Use

- The user only wants the structure check. Tell them to run `/skill-static-review <skill_dir>`. It needs no Claude session.
- The user wants the skill written or fixed. This skill only evaluates.

# Workflow

Work in the target skill's own folder, `<skill>/`. Reports go here:

```
<skill>/
├── step_reports/   01_structure.md, 02_rubric.md, 03_runs.md, 04_comparison_<model>.md
├── static_report/  latest output of /skill-static-review
├── evals/
│   ├── inputs/
│   ├── verified-outputs/
│   └── <skill>_<version>_outputs/
│       ├── <skill>_<version>_<model>.md        produced output
│       └── run_on_<model>_report.md            measured numbers
└── final_report.md
```

Save each step's report before you start the next step.

## Step 0: Pick the mode

- **New skill:** one skill directory. Run steps 1 to 5 once.
- **Two versions, V1 already has `final_report.md`:** run steps 1 to 5 for V2. Pass V1's directory to step 5 as `--baseline`.
- **Two versions, V1 has no `final_report.md`:** first run steps 1 to 5 for V1 in its own clean subagent. Then run steps 1 to 5 for V2 in a separate clean subagent. Then do step 5 for V2 with V1 as `--baseline`.

A "clean subagent" for a whole version run means: start a subagent that gets only the path of that version and this skill's instructions, not this conversation.

## Step 1: Structure check

1. Run `/skill-static-review <skill_dir>`. It writes `static_report/static_report.md`.
2. Copy that report into `step_reports/01_structure.md`. Add one line saying whether `evals/inputs/` and `evals/verified-outputs/` exist.
3. If either eval folder is missing, do one of these:
   - Ask the user to add the files. Stop until they do.
   - Or start a generator subagent. Give it only the skill's name, description and `references/eval-data-authoring.md`. It writes `evals/inputs/` and `evals/verified-outputs/`. Tell the user the files were generated.

## Step 2: Rubric review

1. Read `references/rubric-review-session.md` for the model and the token limit.
2. Start one subagent on that model. Give it the skill folder path, `references/rubric.md`, and the token limit. Ask it to answer:
   - Do the sections of `SKILL.md` follow their intended meaning?
   - Are there security risks in the skill?
3. Ask it to confirm every finding against the real text before reporting it.
4. Save its answer as `step_reports/02_rubric.md`.

## Step 3: Run the target skill

Take the model list from `references/models_config.yaml` (`default_models`), plus any models the user asked for. Run the models one after another. For each model:

1. Start a new subagent on that model. Give it the target skill path and the files in `evals/inputs/`. Ask it to follow the skill for each input and write the results to `evals/<skill>_<version>_outputs/<skill>_<version>_<model>.md`.
2. When the subagent returns, record the numbers the harness reports for it: the total tokens (`subagent_tokens`) and the elapsed time. Do not use numbers the subagent reports about itself. Its own count was found to be about 12 times too low (see `references/token-capture.md`).
3. Write `run_on_<model>_report.md` in the outputs folder, exactly in this shape:

   ```
   # Run report: <model>
   - Model name: <model>
   - Tokens used: <number, no unit>
   - Time spent: <for example 5m 12s>
   - Total cost: $<amount>
   ```

   Total cost is `tokens / 1,000,000 × blended_usd_per_million` from `models_config.yaml`. If a value was not reported, write `unavailable`. Never guess.
4. Write a short summary of all runs in `step_reports/03_runs.md`.

## Step 4: Output comparison

For each model, start a fresh subagent. Give it `evals/verified-outputs/` and that model's produced output. Ask it to write `step_reports/04_comparison_<model>.md` containing only table rows, one per verified output:

```
| 01-api-order-cancel.md | <skill>_<version>_<model>.md | <model> | <version> | <what matches, what is missing> |
```

The note must be specific, for example "does not contain the required test cases".

## Step 5: Final report

Run:

```bash
python skill-eval/scripts/build_final_report.py <skill_dir> [--baseline <older_skill_dir>]
```

It writes `<skill_dir>/final_report.md` with numbered sections:

1. Summary (with three charts when two versions are compared: token usage, total cost, time spent)
2. Skill name
3. Skill description
4. Run results
5. Output comparison
6. Skill structure check
7. Skill rubric review

When `--baseline` is used, the tables show V1, V2 and the change.

Tell the user where `final_report.md` is and give the top-line findings.

# Rules

- Use a separate subagent, with a clean context, for the generator, the rubric review, every model run, every output comparison, and any V1 baseline run. This keeps the target skill from being judged with knowledge from the main session.
- Never use the static review's findings to skip later steps. Report them and keep going.
- Cost, tokens and time must be measured values. If one is missing, write `unavailable`.
- Do not produce `.json` reports. All reports are Markdown.
- Do not give the skill a numeric score. Notes must say what is right or wrong.

# Decision Guidelines

- More models than the default: add them for this run only. Do not edit `models_config.yaml` unless the user asks.
- The rubric review runs out of tokens: report which rubric categories were not covered. Do not raise the limit yourself.
- A model run fails: record the failure in its `run_on_<model>_report.md` and continue with the next model.

# References

- `references/preferred-structure.md`: the structure `SKILL.md` is checked against.
- `references/rubric.md`: the rubric for step 2.
- `references/rubric-review-session.md`: model and token limit for step 2.
- `references/models_config.yaml`: run models and prices.
- `references/severity_config.yaml`: severity of each static check.
- `references/eval-data-authoring.md`: how to write `evals/inputs/` and `evals/verified-outputs/`.
- `references/token-capture.md`: why harness-reported tokens are used.
- `scripts/structural_check.py`, `scripts/generate_static_report.py`: the static review.
- `scripts/build_final_report.py`: builds the final report.
