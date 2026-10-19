# Evaluation data: format and authoring

`skill-eval` needs example inputs and verified outputs for the skill under review:

```
evals/
├── inputs/
└── verified-outputs/
```

## Rules

- One input file and one verified output file per case. Give a pair matching names, for example `inputs/01-api-order-cancel.md` and `verified-outputs/01-api-order-cancel.md`.
- A verified output is what a correct run should produce. A person should have read it and agreed it is right. Generated files are only a starting point: `evals/GENERATED.md` marks them, and both reports then say they need review.
- The same inputs are used for every model and for both versions when two versions are compared. Do not reword an input between runs that will be compared.

- A verified output also fixes what "similar" means. The default similarity profile (`document`) counts the numbers and backticked identifiers in it, so write concrete values (limits, codes, field names) in backticks where they are required. For other kinds of skill, see `profiles.md`.

## What to cover

Take cases from these places, in this order:

1. The skill's `description` and "When to Use" section. They contain example requests. Use one close to word for word.
2. What changed, when comparing two versions. Read the skill's `CHANGELOG.md` and add at least one case that uses the change.
3. The "When NOT to Use" section. Add one case where the skill should decline or hand off.

Three to five cases are enough. Keep each case small, so a run stays cheap.

## Generating the files

When `evals/inputs/` or `evals/verified-outputs/` is missing or empty, `skill-eval` generates the files with a subagent in a fresh context and does not wait for the user. Give it only the skill's name and description, and this file. It must not read the skill's body or any earlier reports, so the cases are not shaped by the skill's own implementation. The orchestrator then writes `evals/GENERATED.md` with the list of files created.

## Extra data for the `codebase-plan` profile

A skill that analyses a codebase needs something to analyse. Add `evals/sandbox/`:

```
evals/sandbox/
├── codebase/       a small realistic project (15 to 40 files), every layer the skill's description names
└── agents/*.md     one definition (frontmatter name, description, tools, model) for every subagent SKILL.md names
```

- Keep the project small and consistent: files must exist where the verified plans say they do, and an existing file's content must make the planned change necessary.
- Use at least one case per layer combination (all layers, one layer only, two layers) so that "do not touch a layer the feature does not need" is tested.
- In verified plans name each existing file in backticks with its path relative to `codebase`, introduce each new file with "New file", and use `Phase N: <name>` headings. Backtick an endpoint or symbol only when the input fixes it.
- Tools of the agents: read-only (`Read, Glob, Grep`). Agent definitions are part of the test setup; when the real ones differ, replace the generated ones.

## How an input is given to the model

`scripts/run_skill.py` copies one input into a clean project next to the installed skill and sends the prompt `runner.prompt` of `config.yaml`, with `{input_file}` replaced by the input's file name. The result is read from the reply.
