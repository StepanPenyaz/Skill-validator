# skill-eval

Evaluates a Claude Agent Skill and writes two reports: a short `final_report.md` and a `detailed_final_report.md`. See [`SKILL.md`](SKILL.md) for the exact steps Claude follows.

## The flow

1. **Structure check (gate).** Does `SKILL.md` follow `references/preferred-structure.md`? Same report as `/skill-static-review`. Blocking (Blocker) findings stop the evaluation: later steps do not run, and the short report lists only those findings.
2. **Rubric review.** Do the sections mean what they should? Any security risks? Runs in a Claude subagent, using the model and token limit in `config.yaml`.
3. **Evaluation data.** If `evals/inputs/` and `evals/verified-outputs/` exist, they are used. If not, a subagent generates them and `evals/GENERATED.md` marks them, so both reports say the data needs review.
4. **Run the skill.** `scripts/run_skill.py` starts one `claude -p` process per model, repeat and input, in a clean temporary project that has the skill but not `evals/`. The repeats (`runs_per_model`) show whether a model behaves the same each time. Tokens, real cost, time, turns and tool calls come from `claude -p`; every transcript is kept.
5. **Comparison and similarity.** `scripts/compute_similarity.py` scores each output against the verified output (0 to 100%), per run and case, and rates stability. Two independent judge subagents write notes and a verdict for each model's median run.
6. **Reports.** `scripts/build_final_report.py` writes both reports, ending in a model recommendation.

## What the skill under review needs

```
<skill>/
└── SKILL.md
```

`evals/inputs/` and `evals/verified-outputs/` are optional. Without them they are generated (see `references/eval-data-authoring.md`). Verified examples written or checked by a person give better results.

## Where results go

```
<skill>/
├── step_reports/       01_structure, 02_rubric, 04_comparison_<model>_a/_b, 05_similarity
├── static_report/      latest structure check report
├── evals/<skill>_<version>_outputs/
│   ├── <model>/run_<r>/   outputs, <input>.json run records, <input>.jsonl transcripts
│   └── run_on_<model>_report.md
├── final_report.md            Summary, Skill name, Skill description, Model recommendation
└── detailed_final_report.md   all sections, including run stability and behaviour
```

These folders and reports are left out when a skill is packaged.

## The reports

`final_report.md` has four sections: Summary, Skill name, Skill description and Model recommendation. A fifth section, Blocking structure findings, appears only when the structure check found Blockers and then contains only those findings. The summary notes when the eval data was generated.

`detailed_final_report.md` adds the run results, the output comparison notes, the full structure check and rubric review, and section 9, run stability and behaviour.

## Similarity, stability and the model recommendation

Similarity scores a produced output against its verified output. It is not a score for the skill. What counts as similar depends on the kind of skill, so it is defined per profile (`references/profiles.md`). The default `document` profile, for structured text, mixes fact recall, word overlap and structure. To change the weights or required sections, edit the profile in `config.yaml`.

A case with no output (a failed or cut-off run) scores 0 and makes its run incomplete.

Stability is measured on repeats of the same input, not between different inputs: a model is `unstable` when one input gets very different similarity from run to run. A model with too few complete runs is `insufficient`, which points at infrastructure (timeouts, budget), not at the model. If two or more models are unstable, the report flags a possible problem in the skill; one unstable model is a limit of that model.

The recommendation (section 4 of the short report) follows a fixed rule: drop models with too few complete runs, unstable results, or a `Major gaps` verdict from both judges (a verdict the judges disagree on is `Disputed`, kept and flagged); take the models within the run-to-run noise of the best similarity (never less than `recommendation.tolerance_points`); recommend the cheapest of them.

Settings: all of them are in `config.yaml`.

## Running the pieces

```
python skill-eval/scripts/run_skill.py <skill> [--models opus,sonnet] [--runs 3] [--jobs 3]
python skill-eval/scripts/compute_similarity.py <skill>
python skill-eval/scripts/build_final_report.py <skill> [--baseline <older skill>]
```

`run_skill.py` needs the `claude` CLI, logged in. Runs that already succeeded are skipped on a second start (use `--force` to run them again). Set `CLAUDE_BIN` or `--claude-bin` to use another command, as the tests do.

## Static review on its own

```
/skill-static-review <path-to-skill>
```

No Claude session is needed; the command only runs `scripts/generate_static_report.py`. You can run it at any time, alone or as step 1. Each run replaces `static_report/static_report.md`.

To change how serious a check is, edit `static_checks` in `config.yaml`.

## Comparing two versions

Ask for a comparison of V1 and V2.

- If V1 already has a `detailed_final_report.md`, only V2 is evaluated and the two reports are compared.
- If it has none, both versions are evaluated, each in its own clean subagent, and then compared.

## Files

| Path | Purpose |
|---|---|
| `SKILL.md` | Instructions for Claude |
| `references/preferred-structure.md` | Structure `SKILL.md` is checked against |
| `references/rubric.md` | Rubric for step 2 |
| `config.yaml` | All settings: models, repeats, runner and stability limits, recommendation tolerance, rubric review model, similarity profiles, severity of static checks |
| `references/profiles.md` | Profiles: what depends on the kind of skill, and how to add one |
| `scripts/profiles/` | Profile modules (`document`) |
| `references/eval-data-authoring.md` | How to write or generate `evals/` data |
| `references/token-capture.md` | Where tokens, time and cost come from |
| `scripts/structural_check.py` | Static checks |
| `scripts/generate_static_report.py` | Static report in Markdown; `--fail-on-blocker` is the gate |
| `scripts/run_skill.py` | The model runs (`claude -p`) |
| `scripts/compute_similarity.py` | Similarity, stability and flags |
| `scripts/build_final_report.py` | Builds both reports, including the model recommendation |
| `tests/` | Unit tests: `python -m unittest discover skill-eval/tests` |

Needs Python 3 and PyYAML (`pip install -r requirements.txt`).
