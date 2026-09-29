# Evaluation data: format and authoring

`skill-eval` needs example inputs and verified outputs for the skill under review:

```
evals/
├── inputs/
└── verified-outputs/
```

## Rules

- One input file and one verified output file per case. Give a pair matching names, for example `inputs/01-api-order-cancel.md` and `verified-outputs/01-api-order-cancel.md`.
- A verified output is what a correct run should produce. A person should have read it and agreed it is right. Generated files are only a starting point; tell the user they were generated so they can check them.
- The same inputs are used for every model and for both versions when two versions are compared. Do not reword an input between runs that will be compared.

## What to cover

Take cases from these places, in this order:

1. The skill's `description` and "When to Use" section. They contain example requests. Use one close to word for word.
2. What changed, when comparing two versions. Read the skill's `CHANGELOG.md` and add at least one case that uses the change.
3. The "When NOT to Use" section. Add one case where the skill should decline or hand off.

Three to five cases are enough. Keep each case small, so a run stays cheap.

## Generating the files

When the folders are missing and the user wants them generated, use a subagent in a fresh context. Give it only the skill's name and description, and this file. It must not read the skill's body or any earlier reports, so the cases are not shaped by the skill's own implementation.
