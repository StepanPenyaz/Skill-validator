# skill-eval

Evaluates a Claude Agent Skill and writes one report. See [`SKILL.md`](SKILL.md) for the exact steps Claude follows.

## The flow

1. **Structure check.** Does `SKILL.md` follow `references/preferred-structure.md`? Uses `/skill-static-review`.
2. **Rubric review.** Do the sections mean what they should? Any security risks? Runs in a Claude subagent, using the model and token limit in `references/rubric-review-session.md`.
3. **Run the skill.** Each model in `references/models_config.yaml` runs the skill on `evals/inputs/` in its own subagent. Tokens, time and cost are measured and saved in `run_on_<model>_report.md`.
4. **Output comparison.** Each produced output is compared with `evals/verified-outputs/`.
5. **Final report.** `final_report.md`, with numbered sections. With two versions it shows V1, V2 and the change, and adds charts for tokens, cost and time.

## What the skill under review needs

```
<skill>/
├── SKILL.md
└── evals/
    ├── inputs/
    └── verified-outputs/
```

If `evals/` is missing, `skill-eval` asks you to add it, or has a separate subagent generate it. See `references/eval-data-authoring.md`.

## Where results go

```
<skill>/
├── step_reports/    reports from each step
├── static_report/   latest /skill-static-review report
├── evals/<skill>_<version>_outputs/   produced outputs and run_on_<model>_report.md
└── final_report.md
```

These folders are left out when a skill is packaged.

## Static review on its own

```
/skill-static-review <path-to-skill>
```

No Claude session is needed; the command only runs `scripts/generate_static_report.py`. You can run it at any time, alone or as step 1. Each run replaces `static_report/static_report.md`.

To change how serious a check is, edit `references/severity_config.yaml`.

## Comparing two versions

Ask for a comparison of V1 and V2.

- If V1 already has a `final_report.md`, only V2 is evaluated and the two reports are compared.
- If it has none, both versions are evaluated, each in its own clean subagent, and then compared.

## Files

| Path | Purpose |
|---|---|
| `SKILL.md` | Instructions for Claude |
| `references/preferred-structure.md` | Structure `SKILL.md` is checked against |
| `references/rubric.md` | Rubric for step 2 |
| `references/rubric-review-session.md` | Model and token limit for step 2 |
| `references/models_config.yaml` | Run models and prices |
| `references/severity_config.yaml` | Severity of each static check |
| `references/eval-data-authoring.md` | How to write `evals/` data |
| `references/token-capture.md` | How tokens, time and cost are measured |
| `scripts/structural_check.py` | Static checks |
| `scripts/generate_static_report.py` | Static report in Markdown |
| `scripts/build_final_report.py` | Builds `final_report.md` |

Needs Python 3 and PyYAML (`pip install -r requirements.txt`).
