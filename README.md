# Skill Validator

Tools to evaluate Claude Agent Skills.

## Layout

```
.
├── .claude/commands/
│   └── skill-static-review.md   # /skill-static-review command
├── scripts/
│   └── package_skill.py         # Packages a skill into a .skill bundle
└── skill-eval/                  # The evaluation skill
```

## Evaluate a skill

Ask Claude, with `skill-eval` available:

```
Evaluate the skill in <path-to-skill>.
```

`skill-eval` will:

1. Check the skill's structure.
2. Review it against a rubric.
3. Run it on several Claude models and measure tokens, time and cost.
4. Write `final_report.md` in the skill's folder.

To compare two versions, ask for a comparison of V1 and V2. See [`skill-eval/README.md`](skill-eval/README.md) for details.

## Static review only

No Claude session is needed:

```
/skill-static-review <path-to-skill>
```

The report is saved in `<skill>/static_report/`.

## Package a skill

```bash
python3 scripts/package_skill.py <skill-name> [output-dir]
```

Evaluation folders (`evals/`, `step_reports/`, `static_report/`) and `final_report.md` are not included in the bundle.
